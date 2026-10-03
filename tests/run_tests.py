#!/usr/bin/env python3
"""Standard-library-only black-box tests. No assembler or reference emulator required."""
import argparse
from collections import Counter
from dataclasses import dataclass
import os
from pathlib import Path
import random
import shlex
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x10010000
MASK = 0xffffffff


def imm(op, rs, rt, value):
    return op << 26 | rs << 21 | rt << 16 | (value & 0xffff)


def reg(fn, rs, rt, rd, op=0):
    return op << 26 | rs << 21 | rt << 16 | rd << 11 | fn


def load(rt, value):
    value &= MASK
    return [imm(15, 0, rt, value >> 16), imm(13, rt, rt, value & 0xffff)]


def signed(value):
    value &= MASK
    return value if value < 0x80000000 else value - 0x100000000


EXIT = load(2, 10) + [12]
PRINT = load(2, 1) + [12]


def executable(code, data=b"", entry=0, offsets=None):
    offsets = [0] * len(code) if offsets is None else offsets
    return (b"MIPSEE" + struct.pack("<II", len(code), entry) +
            struct.pack("<" + "I" * len(code), *code) +
            struct.pack("<" + "I" * len(code), *offsets) +
            struct.pack("<H", len(data)) + data)


@dataclass
class Case:
    group: str
    name: str
    payload: bytes = b""
    stdout: bytes = b""
    stderr: bytes = b""
    status: int = 0
    stdin: bytes = b""
    source: bytes | None = None
    trace: bool = False
    loader: bool = False
    args: tuple | None = None
    stderr_contains: bytes | None = None


def cases(random_count, seed):
    result = []

    def add(group, name, code, expected=b"", error=None, **kwargs):
        payload = executable(code, kwargs.pop("data", b""),
                             kwargs.pop("entry", 0), kwargs.pop("offsets", None))
        result.append(Case(group, name, payload, expected,
                           (error + "\n").encode() if error else b"",
                           kwargs.pop("status", 1 if error else 0), **kwargs))

    def number(group, name, code, value, **kwargs):
        add(group, name, code + PRINT + EXIT, str(signed(value)).encode(), **kwargs)

    # S1: inspect every loaded field without executing the instructions.
    rng = random.Random(seed)
    for count, size, entry in [(0, 0, 0), (1, 1, 0), (4, 256, 3), (19, 65535, 17)]:
        words = [rng.getrandbits(32) for _ in range(count)]
        offsets = [rng.getrandbits(32) for _ in range(count)]
        data = bytes((i * 37 + 128) & 255 for i in range(size))
        expected = f"{count} {entry} {size}\n"
        expected += "".join(f"{a:08x} {b:08x}\n" for a, b in zip(words, offsets))
        expected += data.hex() + "\n"
        result.append(Case("S1", f"loader-fields-{count}-{size}",
                           executable(words, data, entry, offsets),
                           expected.encode(), loader=True))
    for position in range(6):
        blob = bytearray(executable(EXIT))
        blob[position] ^= 0xff
        result.append(Case("S1", f"bad-magic-byte-{position}", bytes(blob),
                           stderr=b"Invalid MIPSEE file\n", status=1))
    for cut in [0, 1, 5, 6, 9, 13, 14, 17, 25, 33, 38, 39, 40]:
        blob = executable(EXIT, b"abc")
        result.append(Case("POLICY", f"truncated-file-{cut}", blob[:cut],
                           stderr=b"Invalid MIPSEE file\n", status=1))
    result.append(Case("S1", "missing-executable", args=("missing.mipsee",),
                       status=1, stderr_contains=b"missing.mipsee:"))
    for args in [(), ("-x", "program.mipsee"), ("a", "b", "c")]:
        result.append(Case("CLI", f"usage-{len(result)}", args=args,
                           status=1, stderr=b"Usage: mipsee [-t] <executable>\n"))

    # S2: literals, sign extension, all registers, syscall code bits.
    for value in [-32768, -1, 0, 1, 32767]:
        number("S2", f"addi-immediate-{value}", [imm(8, 0, 4, value)], value)
    for value in [0, 1, 0x7fff, 0x8000, 0xffff]:
        number("S2", f"ori-zero-extension-{value}", [imm(13, 0, 4, value)], value)
        number("S2", f"lui-{value}", [imm(15, 0, 4, value)], value << 16)
    for index in range(32):
        number("S2", f"register-{index}",
               load(index, 123456) + [reg(33, index, 0, 4)],
               0 if index == 0 else 123456)
    for a, b in [(2, 3), (-9, 4), (-4, -8), (0x7ffffffe, 1), (-2147483647, -1)]:
        number("S2", f"add-{a}-{b}", load(8, a) + load(9, b) +
               [reg(32, 8, 9, 4)], a + b)
    for value in [0, 65, 255, 0x141, -1]:
        add("S2", f"putchar-{value}", load(4, value) + load(2, 11) + [12] + EXIT,
            bytes([value & 255]))
    for codebits in [0, 1, 0xfffff]:
        add("S2", f"syscall-code-{codebits}", load(4, 7) + load(2, 1) +
            [(codebits << 6) | 12] + EXIT, b"7")
    for syscall in [0, 2, 5, 17, MASK]:
        add("S2", f"bad-syscall-{syscall}", load(2, syscall) + [12],
            error="MIPSEE error: bad syscall number")
    for word in [0xffffffff, 0, 0x08000000, 0x00000860, 0x3c220001, 0x70000042]:
        add("S2", f"bad-instruction-{word:08x}", [word],
            error=f"MIPSEE error: bad instruction 0x{word:08x}")
    for entry in [0, 1, MASK]:
        add("S2", f"empty-or-invalid-entry-{entry}", [], entry=entry,
            error="MIPSEE error: execution past the end of instructions")
    add("S2", "fall-through", [imm(9, 0, 8, 1)],
        error="MIPSEE error: execution past the end of instructions")
    add("S2", "nonzero-entry-skips-invalid", [MASK] + EXIT, entry=1)
    add("S2", "exit-does-not-fetch-next", EXIT + [MASK])

    # S3 arithmetic: edge vectors plus fixed-seed independent numeric oracles.
    for ones in [False, True]:
        for count in range(33):
            bits = 0 if count == 32 else 1 << (31 - count)
            value = (~bits & MASK) if ones else bits
            number("S3", f"{'clo' if ones else 'clz'}-{count}", load(8, value) +
                   [reg(0x51 if ones else 0x50, 8, 0, 4)], count)
    for a, b in [(0, -1), (-1, 0), (-2, -1), (MASK >> 1, 0x80000000),
                 (0x80000000, MASK >> 1), (0, 0), (MASK, MASK)]:
        number("S3", f"slt-{a}-{b}", load(8, a) + load(9, b) +
               [reg(42, 8, 9, 4)], int(signed(a) < signed(b)))
    for name, code in [
        ("positive-add", load(8, 0x7fffffff) + load(9, 1) + [reg(32, 8, 9, 4)]),
        ("negative-add", load(8, 0x80000000) + load(9, -1) + [reg(32, 8, 9, 4)]),
        ("positive-addi", load(8, 0x7fffffff) + [imm(8, 8, 4, 1)]),
        ("negative-addi", load(8, 0x80000000) + [imm(8, 8, 4, -1)]),
        ("zero-destination", load(8, 0x7fffffff) + [imm(8, 8, 0, 1)]),
    ]:
        add("S3", f"overflow-{name}", code, error="MIPSEE error: addition would overflow")
    for n in range(random_count):
        a, b = rng.getrandbits(32), rng.getrandbits(32)
        immediate_value = rng.randrange(-32768, 32768)
        vectors = [
            ("addu", reg(33, 8, 9, 4), a + b),
            ("addiu", imm(9, 8, 4, immediate_value), a + immediate_value),
            ("mul", reg(2, 8, 9, 4, 28), a * b),
            ("slt", reg(42, 8, 9, 4), int(signed(a) < signed(b))),
            ("ori", imm(13, 8, 4, immediate_value), a | (immediate_value & 0xffff)),
        ]
        for name, instruction, expected in vectors:
            number("S3", f"random-{name}-{n}", load(8, a) + load(9, b) +
                   [instruction], expected)
        total = signed(a) + signed(b)
        code = load(8, a) + load(9, b) + [reg(32, 8, 9, 4)]
        if -(1 << 31) <= total < (1 << 31):
            number("S3", f"random-add-{n}", code, total)
        else:
            add("S3", f"random-add-{n}", code, error="MIPSEE error: addition would overflow")
    for op in [4, 5]:
        for equal in [False, True]:
            taken = equal == (op == 4)
            code = load(8, 5) + load(9, 5 if equal else 6) + [imm(op, 8, 9, 2),
                    imm(9, 0, 4, 11)]
            # Taken skips the assignment; untaken leaves a0 equal to eleven.
            number("S3", f"branch-{op}-{equal}", code, 0 if taken else 11)
    number("S3", "backwards-loop", [imm(9, 0, 8, 3), imm(9, 4, 4, 2),
           imm(9, 8, 8, -1), imm(5, 8, 0, -2)], 6)
    for offset in [-32768, -1, 32767]:
        add("S3", f"branch-outside-{offset}", [imm(4, 0, 0, offset)],
            error="MIPSEE error: execution past the end of instructions")

    # Memory: compare against Python byte conversions, not emulator output.
    memory = bytes([0x80, 0xff, 0x00, 0x80, 0x78, 0x56, 0x34, 0x12])
    for op, size in [(32, 1), (33, 2), (35, 4)]:
        for offset in range(0, len(memory) - size + 1, size):
            expected = int.from_bytes(memory[offset:offset + size], "little", signed=True)
            number("S3", f"load-{size}-{offset}", load(8, BASE) +
                   [imm(op, 8, 4, offset)], expected, data=memory)
        for address in [BASE - size, BASE + 8, MASK]:
            add("S3", f"bad-load-{size}-{address}", load(8, address) + [imm(op, 8, 4, 0)],
                data=memory, error=f"MIPSEE error: bad address for { {1:'byte',2:'half',4:'word'}[size]} access: 0x{address:08x}")
        if size > 1:
            add("S3", f"cross-end-{size}", load(8, BASE) + [imm(op, 8, 4, 0)],
                data=bytes(size - 1), error=f"MIPSEE error: bad address for { {2:'half',4:'word'}[size]} access: 0x{BASE:08x}")
            add("S3", f"misalignment-{size}", load(8, BASE + 1) + [imm(op, 8, 4, 0)],
                data=memory, error=f"MIPSEE error: bad address for { {2:'half',4:'word'}[size]} access: 0x{BASE+1:08x}")
    number("S3", "negative-memory-offset", load(8, BASE + 4) +
           [imm(32, 8, 4, -4)], -128, data=memory)
    for op, size in [(40, 1), (41, 2), (43, 4)]:
        # Store a truncated value, then print every byte to check endianness and neighbours.
        code = load(8, BASE) + load(9, 0x89abcdef) + [imm(op, 8, 9, 4)]
        for offset in range(8):
            code += [imm(32, 8, 4, offset)] + load(2, 11) + [12]
        expected = bytearray(b"abcdefgh")
        expected[4:4+size] = (0x89abcdef).to_bytes(4, "little")[:size]
        add("S3", f"store-{size}", code + EXIT, bytes(expected), data=b"abcdefgh")
        for address in [BASE - 4, BASE + 8]:
            add("S3", f"bad-store-{size}-{address}", load(8, address) + [imm(op, 8, 0, 0)],
                data=memory, error=f"MIPSEE error: bad address for { {1:'byte',2:'half',4:'word'}[size]} access: 0x{address:08x}")
    for op in [32, 33, 35]:
        add("S3", f"load-zero-still-checks-{op}", load(8, BASE) + [imm(op, 8, 0, 0)],
            error=f"MIPSEE error: bad address for { {32:'byte',33:'half',35:'word'}[op]} access: 0x{BASE:08x}")
    for text in [b"", b"hello\n", b"\xff\x80", b"A\0ignored"]:
        add("S3", f"print-string-{text.hex()}", load(4, BASE) + load(2, 4) + [12] + EXIT,
            text.split(b"\0")[0], data=text + b"\0")
    for input_byte in [b"", b"A", b"\x00", b"\xff", b"\n"]:
        number("S3", f"read-char-{input_byte.hex()}", load(2, 12) + [12, reg(33, 2, 0, 4)],
               input_byte[0] if input_byte else -1, stdin=input_byte)

    # S4: exact trace bytes, offsets, unchanged values and syscall modifications.
    source = b"load\nunchanged\nzero\nexit\n"
    add("S4", "trace-exact", [imm(9, 0, 8, 1), imm(9, 0, 8, 1),
                            imm(9, 0, 0, 9), imm(9, 0, 2, 10), 12],
        b"load\n   $t0: 0x00000000 -> 0x00000001\nunchanged\nzero\nexit\n   $v0: 0x00000000 -> 0x0000000a\nexit\n",
        source=source, trace=True, offsets=[0, 5, 15, 20, 20])
    add("S4", "trace-past-eof", [imm(9, 0, 2, 10), 12],
        b"   $v0: 0x00000000 -> 0x0000000a\n",
        source=b"", trace=True, offsets=[100, 100])
    add("S4", "trace-no-final-newline", [imm(9, 0, 2, 10), 12],
        b"end   $v0: 0x00000000 -> 0x0000000a\nend",
        source=b"end", trace=True, offsets=[0, 0])
    add("S4", "trace-read-char", [imm(9, 0, 2, 12), 12, imm(9, 0, 2, 10), 12],
        b"   $v0: 0x00000000 -> 0x0000000c\n   $v0: 0x0000000c -> 0x00000041\n   $v0: 0x00000041 -> 0x0000000a\n",
        stdin=b"A", source=b"", trace=True)
    names = ("zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 "
             "s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra").split()
    for index in range(1, 32):
        expected = f"   ${names[index]}: 0x00000000 -> 0x0000002a\n"
        previous = 42 if index == 2 else 0
        expected += f"   $v0: 0x{previous:08x} -> 0x0000000a\n"
        add("S4", f"trace-register-name-{index}",
            [imm(9, 0, index, 42), imm(9, 0, 2, 10), 12],
            expected.encode(), source=b"", trace=True)
    add("S4", "trace-output-interleaving", [imm(9, 0, 4, 65), imm(9, 0, 2, 11),
        12, imm(9, 0, 2, 10), 12],
        b"a\n   $a0: 0x00000000 -> 0x00000041\nb\n   $v0: 0x00000000 -> 0x0000000b\nc\nAd\n   $v0: 0x0000000b -> 0x0000000a\ne\n",
        source=b"a\nb\nc\nd\ne\n", offsets=[0, 2, 4, 6, 8], trace=True)
    add("S4", "trace-backwards-debug-offsets",
        [imm(9, 0, 8, 2), imm(9, 8, 8, -1), imm(5, 8, 0, -1),
         imm(9, 0, 2, 10), 12],
        b"init\n   $t0: 0x00000000 -> 0x00000002\ndec\n   $t0: 0x00000002 -> 0x00000001\nbranch\ndec\n   $t0: 0x00000001 -> 0x00000000\nbranch\nexit\n   $v0: 0x00000000 -> 0x0000000a\nexit\n",
        source=b"init\ndec\nbranch\nexit\n", offsets=[0, 5, 9, 16, 16], trace=True)
    add("POLICY", "trace-missing-source", EXIT, trace=True, status=1,
        stderr_contains=b"program.s:")

    # File programs print each syscall result on its own line.
    def filesystem(name, operations, expected, policy=False):
        data = bytearray(512)
        for n in range(7):
            data[n * 8:n * 8 + 3] = bytes([ord('a') + n, 0, 0])
        data[64:192] = bytes(range(128))
        data[192:198] = b"ABCDEF"
        code = []
        for operation in operations:
            if operation[0] == "bytes":
                _, address, count = operation
                code += load(8, address)
                for index in range(count):
                    code += [imm(32, 8, 4, index)] + load(2, 11) + [12]
                continue
            call, *arguments = operation
            for register, value in zip([4, 5, 6], arguments):
                code += load(register, value)
            code += load(2, call) + [12, reg(33, 2, 0, 4)] + PRINT
            code += load(4, 10) + load(2, 11) + [12]
        add("POLICY" if policy else "S4", name, code + EXIT, expected, data=bytes(data))

    filesystem("open-missing-read", [(13, BASE, 0)], b"-1\n")
    filesystem("create-close-reopen", [(13, BASE, 1), (16, 0), (13, BASE, 0)],
               b"0\n0\n0\n")
    filesystem("close-twice", [(13, BASE, 1), (16, 0), (16, 0)], b"0\n0\n-1\n")
    for fd in [0, 7, 8, MASK]:
        for syscall in [14, 15, 16]:
            filesystem(f"invalid-descriptor-{syscall}-{fd}", [(syscall, fd, BASE+64, 1)], b"-1\n")
    filesystem("read-write-mode", [(13, BASE, 1), (14, 0, BASE+256, 3),
                                 (13, BASE, 0), (15, 1, BASE+64, 3)],
               b"0\n-1\n1\n-1\n")
    filesystem("descriptor-limit-and-reuse",
               [(13, BASE, 1)] * 9 + [(16, 3), (16, 1), (13, BASE, 0), (13, BASE, 0)],
               b"0\n1\n2\n3\n4\n5\n6\n7\n-1\n0\n0\n1\n3\n")
    filesystem("six-files-limit", [(13, BASE+8*n, 1) for n in range(7)] +
               [(16, 0), (13, BASE+48, 1), (13, BASE, 0)],
               b"0\n1\n2\n3\n4\n5\n-1\n0\n-1\n0\n")
    filesystem("read-eof-and-partial", [(13, BASE, 1), (15, 0, BASE+192, 6),
               (13, BASE, 0), (14, 1, BASE+256, 4), ("bytes", BASE+256, 4),
               (14, 1, BASE+260, 4), ("bytes", BASE+260, 2), (14, 1, BASE+256, 1)],
               b"0\n6\n1\n4\nABCD2\nEF0\n")
    filesystem("independent-read-cursors", [(13, BASE, 1), (15, 0, BASE+192, 6),
               (13, BASE, 0), (13, BASE, 0), (14, 1, BASE+256, 2),
               (14, 2, BASE+258, 2), ("bytes", BASE+256, 4)], b"0\n6\n1\n2\n2\n2\nABAB")
    filesystem("reopen-no-truncation", [(13, BASE, 1), (15, 0, BASE+192, 6),
               (16, 0), (13, BASE, 1), (15, 0, BASE+194, 2), (13, BASE, 0),
               (14, 1, BASE+256, 8), ("bytes", BASE+256, 6)],
               b"0\n6\n0\n0\n2\n1\n6\nCDCDEF")
    filesystem("binary-file-roundtrip", [(13, BASE, 1), (15, 0, BASE+64, 128),
               (13, BASE, 0), (14, 1, BASE+256, 128), ("bytes", BASE+256, 128)],
               b"0\n128\n1\n128\n" + bytes(range(128)))
    filesystem("separate-file-contents", [(13, BASE, 1), (13, BASE+8, 1),
               (15, 0, BASE+192, 2), (15, 1, BASE+194, 2), (13, BASE, 0),
               (13, BASE+8, 0), (14, 2, BASE+256, 2), (14, 3, BASE+258, 2),
               ("bytes", BASE+256, 4)], b"0\n1\n2\n2\n2\n3\n2\n2\nABCD")
    filesystem("zero-length-valid-buffer", [(13, BASE, 1), (15, 0, BASE+64, 0),
               (13, BASE, 0), (14, 1, BASE+256, 0)], b"0\n0\n1\n0\n")

    # Explicit local policy regressions; unspecified reference boundaries.
    filesystem("capacity-short-write", [(13, BASE, 1), (15, 0, BASE+64, 127),
               (15, 0, BASE+64, 2), (15, 0, BASE+64, 1)], b"0\n127\n1\n0\n", True)
    filesystem("invalid-buffer-no-cursor-change", [(13, BASE, 1),
               (15, 0, BASE+512, 1), (15, 0, BASE+192, 2), (13, BASE, 0),
               (14, 1, BASE+512, 1), (14, 1, BASE+256, 2), ("bytes", BASE+256, 2)],
               b"0\n-1\n2\n1\n-1\n2\nAB", True)
    for flag in [2, MASK]:
        filesystem(f"invalid-open-mode-{flag}", [(13, BASE, flag)], b"-1\n", True)
    filesystem("negative-byte-count", [(13, BASE, 1), (15, 0, BASE+64, MASK)],
               b"0\n-1\n", True)
    filesystem("invalid-open-pointer", [(13, BASE+512, 1)], b"-1\n", True)
    # Guest-created filenames must never appear on the host, even after close.
    filesystem("host-file-isolation", [(13, BASE, 1), (15, 0, BASE+192, 6),
                                      (16, 0)], b"0\n6\n0\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "mipsee")
    parser.add_argument("--subset", choices=["all", "S1", "S2", "S3", "S4", "POLICY", "CLI"], default="all")
    parser.add_argument("--random-cases", type=int, default=32, help="six arithmetic checks per random vector")
    parser.add_argument("--seed", type=int, default=8675309)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--timeout", type=float, default=3)
    args = parser.parse_args()
    if args.random_cases < 0:
        parser.error("--random-cases must be nonnegative")
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error(f"executable not found: {binary}; run make first")
    suite = [c for c in cases(args.random_cases, args.seed)
             if args.subset == "all" or c.group == args.subset]
    counts, failures = Counter(), []
    with tempfile.TemporaryDirectory(prefix="mipsee-tests-") as directory:
        temporary = Path(directory)
        probe = temporary / "loader_probe"
        if any(c.loader for c in suite):
            command = shlex.split(os.environ.get("CC", "cc"))
            subprocess.run(command + ["-std=c11", "-Wall", "-Wextra",
                           str(ROOT / "tests/loader_probe.c"), "-o", str(probe)], check=True)
        for index, case in enumerate(suite):
            sandbox = temporary / str(index)
            sandbox.mkdir()
            path = sandbox / "program.mipsee"
            path.write_bytes(case.payload)
            if case.source is not None:
                path.with_suffix(".s").write_bytes(case.source)
            command = [str(probe if case.loader else binary)]
            command += list(case.args) if case.args is not None else (
                (["-t"] if case.trace else []) + [str(path)])
            before = {p.name: p.read_bytes() for p in sandbox.iterdir()}
            try:
                completed = subprocess.run(command, input=case.stdin, capture_output=True,
                                           cwd=sandbox, timeout=args.timeout)
                assert completed.returncode == case.status, (
                    f"exit {completed.returncode}, expected {case.status}; stderr={completed.stderr[:300]!r}")
                assert completed.stdout == case.stdout, (
                    f"stdout {completed.stdout[:300]!r}, expected {case.stdout[:300]!r}")
                if case.stderr_contains is None:
                    assert completed.stderr == case.stderr, (
                        f"stderr {completed.stderr[:300]!r}, expected {case.stderr[:300]!r}")
                else:
                    assert case.stderr_contains in completed.stderr, completed.stderr
                after = {p.name: p.read_bytes() for p in sandbox.iterdir()}
                assert before == after, "guest program changed host files"
                counts[case.group] += 1
                if args.verbose:
                    print(f"PASS {case.group} {case.name}")
            except (AssertionError, subprocess.TimeoutExpired, OSError) as error:
                failures.append((case, str(error)))
                print(f"FAIL {case.group} {case.name}: {error}")
    for group, count in sorted(counts.items()):
        print(f"{group}: {count} passed")
    print(f"Total: {sum(counts.values())} passed, {len(failures)} failed; seed={args.seed}")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
