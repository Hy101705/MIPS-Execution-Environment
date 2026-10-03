# MIPS Execution Environment

A small C interpreter for MIPSEE executable files. It loads instructions and
initial data, executes a subset of MIPS, and optionally traces source lines and
register changes.

## Build and run

Requires a C compiler and Make:

```sh
make
./mipsee examples/hi_addi_1.mipsee
./mipsee -t examples/hi_addi_1.mipsee
```

Or compile directly:

```sh
cc -std=c11 -Wall -Wextra mipsee.c -o mipsee
```

Trace mode reads the matching `.s` file beside the executable. The included
binary examples are ready to run; this project does not include an assembler.

## Subset 1 — Executable loading

Implement `read_mipsee_file(char *path, struct mipsee_file *executable)`.
Load the binary file into the following structure, preserving its layout:

```c
struct mipsee_file {
    uint32_t num_instructions;
    uint32_t entry_point;
    uint32_t *instructions;
    uint32_t *debug_offsets;
    uint16_t memory_size;
    uint8_t *initial_data;
};
```

The executable contains seven consecutive sections:

| Section | Bytes | Representation and purpose |
| --- | --- | --- |
| Magic number | 6 | `4D 49 50 53 45 45`, ASCII `MIPSEE` |
| Instruction count | 4 | Unsigned 32-bit little-endian count |
| Entry point | 4 | Unsigned 32-bit little-endian instruction index |
| Instructions | `4 × num_instructions` | Array of 32-bit little-endian instruction words |
| Debug offsets | `4 × num_instructions` | Array of 32-bit little-endian source-file byte offsets |
| Memory size | 2 | Unsigned 16-bit little-endian data-segment size |
| Initial data | `memory_size` | Raw initial data-segment bytes |

Allocate the instruction, debug-offset, and initial-data arrays on the heap
using `malloc`. A successful load produces no output. The loader must also
work independently of the execution function.

Required errors:

- If opening the executable fails, call `perror(path)` and exit with status 1.
- If its magic number is incorrect, print `Invalid MIPSEE file` to standard
  error and exit with status 1.

Additional malformed-file checks are permitted. This implementation also
rejects truncated fields.

## Subset 2 — Basic execution

Implement `execute_mipsee(struct mipsee_file *executable, int trace_mode,
char *path)`. Start at the entry-point instruction index with all 32
general-purpose registers set to zero. Fetch and decode instructions using bit
operations, extracting register operands and immediates.

Register `$zero` always remains zero. Instructions cannot change its stored
value. Unless a branch changes control flow, advance to the next instruction.

In the encoding tables, `s`, `t`, `d`, and `b` denote five-bit register
fields; `I` and `O` denote sixteen-bit immediate and offset fields; `c`
denotes the syscall code field.

| Instruction | Semantics | Encoding |
| --- | --- | --- |
| `ADDI Rt, Rs, Imm16` | Add a sign-extended immediate | `001000ssssstttttIIIIIIIIIIIIIIII` |
| `SYSCALL` | Dispatch using `$v0` | `000000cccccccccccccccccccc001100` |
| `ADD Rd, Rs, Rt` | Add two registers | `000000ssssstttttddddd00000100000` |
| `ORI Rt, Rs, Imm16` | Bitwise OR with a zero-extended immediate | `001101ssssstttttIIIIIIIIIIIIIIII` |
| `LUI Rt, Imm16` | Place the immediate in bits 31–16 | `00111100000tttttIIIIIIIIIIIIIIII` |

Basic system calls:

| Number in `$v0` | Action |
| --- | --- |
| 1 | Print `$a0` as a signed 32-bit decimal integer |
| 10 | Terminate successfully with status 0 |
| 11 | Print the character in `$a0` |

Required execution errors:

- Unsupported syscall: `MIPSEE error: bad syscall number`.
- Invalid instruction: `MIPSEE error: bad instruction <instruction>`.
- Running beyond the instruction array: `MIPSEE error: execution past the end of instructions`.

Print errors to standard error, append a newline, and exit with status 1.
Format instruction words as `0x` followed by eight hexadecimal digits.

## Subset 3 — Extended instructions and memory

Add the following instructions:

| Instruction | Semantics | Encoding |
| --- | --- | --- |
| `CLO Rd, Rs` | Count consecutive one bits from the most significant bit | `000000ssssstttttddddd00001010001` |
| `CLZ Rd, Rs` | Count consecutive zero bits from the most significant bit | `000000ssssstttttddddd00001010000` |
| `ADDU Rd, Rs, Rt` | Add, wrapping to 32 bits without an overflow error | `000000ssssstttttddddd00000100001` |
| `ADDIU Rt, Rs, Imm16` | Add a sign-extended immediate, wrapping to 32 bits | `001001ssssstttttIIIIIIIIIIIIIIII` |
| `MUL Rd, Rs, Rt` | Store the low 32 bits of the product | `011100ssssstttttddddd00000000010` |
| `BEQ Rs, Rt, Offset16` | Branch when registers are equal | `000100ssssstttttOOOOOOOOOOOOOOOO` |
| `BNE Rs, Rt, Offset16` | Branch when registers are unequal | `000101ssssstttttOOOOOOOOOOOOOOOO` |
| `SLT Rd, Rs, Rt` | Set to 1 if signed `Rs < Rt`, otherwise 0 | `000000ssssstttttddddd00000101010` |
| `LB Rt, Offset16(Rb)` | Load and sign-extend a byte | `100000bbbbbtttttOOOOOOOOOOOOOOOO` |
| `LH Rt, Offset16(Rb)` | Load and sign-extend a halfword | `100001bbbbbtttttOOOOOOOOOOOOOOOO` |
| `LW Rt, Offset16(Rb)` | Load a word | `100011bbbbbtttttOOOOOOOOOOOOOOOO` |
| `SB Rt, Offset16(Rb)` | Store the low byte | `101000bbbbbtttttOOOOOOOOOOOOOOOO` |
| `SH Rt, Offset16(Rb)` | Store the low halfword | `101001bbbbbtttttOOOOOOOOOOOOOOOO` |
| `SW Rt, Offset16(Rb)` | Store a word | `101011bbbbbtttttOOOOOOOOOOOOOOOO` |

Leading-bit counts range from 0 to 32. For example, `CLZ` of zero is 32,
and `CLO` of an all-ones word is 32.

A taken branch targets `current_instruction_index + sign_extended_offset`.
The offset is relative to the current instruction, not the next instruction.
An untaken branch advances by one.

Memory accesses address the data segment starting at `0x10010000`, initialized
from `initial_data`. The effective address is the base register plus the
sign-extended offset. Multi-byte values use little-endian byte order.
Only data-segment memory access is required.

Additional system calls:

| Number in `$v0` | Action |
| --- | --- |
| 4 | Print the NUL-terminated string at address `$a0` |
| 12 | Read a character from standard input into `$v0`; return -1 on EOF |

Additional errors:

- Signed overflow in `ADD` or `ADDI`:
  `MIPSEE error: addition would overflow`.
- Misaligned or out-of-range memory access:
  `MIPSEE error: bad address for <size> access: <address>`.

Here, `<size>` is `byte`, `half`, or `word`; `<address>` uses eight
hexadecimal digits prefixed with `0x`. Halfwords require two-byte alignment
and words require four-byte alignment. The complete access must fit in
`[0x10010000, 0x10010000 + memory_size)`.

These errors also go to standard error and terminate with status 1.

## Subset 4 — Tracing and an in-memory filesystem

### Source and register tracing

Enable tracing with:

```sh
./mipsee -t examples/hi_addi_1.mipsee
```

Before execution, open the assembly source whose path is obtained by replacing
the executable's `.mipsee` extension with `.s`.

Immediately before each instruction, seek to its debug offset using `fseek`
and print the source line through the newline or EOF. If the offset is beyond
EOF, print no source line.

Immediately after an instruction changes a register's value, print:

```text
   $v0: 0x00000000 -> 0x0000000b
```

Use the register's conventional name and eight-digit hexadecimal values.
Do not report unchanged values or changes to `$zero`. Normal program output
and trace output share standard output.

### File system calls

Emulate files in memory. Guest open, read, write, and close operations must
not perform real host filesystem operations.

| Syscall | Arguments | Result in `$v0` |
| --- | --- | --- |
| 13 — open | `$a0`: NUL-terminated path address; `$a1`: 0 for reading or 1 for writing | Lowest unused descriptor, or -1 on error |
| 14 — read | `$a0`: descriptor; `$a1`: destination buffer address; `$a2`: maximum byte count | Bytes read, or -1 on error |
| 15 — write | `$a0`: descriptor; `$a1`: source buffer address; `$a2`: maximum byte count | Bytes written, or -1 on error |
| 16 — close | `$a0`: descriptor | 0 on success, or -1 on error |

Opening a missing file for writing creates it. Opening an existing file does
not truncate it. Opening a missing file for reading fails. Reads require a
descriptor opened for reading; writes require one opened for writing.
Closing an invalid descriptor fails.

Maintain file contents and a position for each open descriptor. Allocate the
lowest available descriptor on each successful open and make closed
descriptors available for reuse.

Required limits:

- At most 6 files.
- At most 8 simultaneously open descriptors.
- At most 128 bytes per file.

The specification does not fully define every boundary case. Exact behavior
for unspecified cases must be checked against the reference implementation;
local tests alone do not establish full reference compatibility.

## Implementation constraints

- Implement the emulator in C using standard C library facilities; the standard
  mathematics library and assertions are also permitted.
- Do not invoke external programs using `system` or similar functions.
- Do not require third-party libraries or special compiler options.
- Support compilation with `cc *.c -o mipsee`.
- Pseudo-instructions do not need decoding: the executable's assembler has
  already expanded them into real instructions.
- Instructions and syscalls outside the listed set are not required.
- Keep diagnostic development output out of normal execution.
- Test programs should finish with syscall 10.

## Testing by subset

The automated suite requires Python 3.10 or later and uses only its standard
library. The emulator itself remains a standalone C program. From the project
directory, run:

```sh
make test
```

The default suite contains **500 named test cases**:

| Group | Cases | Coverage |
| --- | ---: | --- |
| S1 | 11 | Direct loader checks, all magic bytes, missing executable |
| S2 | 77 | Basic instructions, registers, syscall decoding, output and execution errors |
| S3 | 327 | Leading-bit counts, fixed-seed arithmetic, branches, sign extension, memory and overflow |
| S4 | 62 | Exact trace output, register names, file contents, cursors, descriptor limits and host isolation |
| CLI | 3 | Invalid command-line arguments and exact usage messages |
| POLICY | 20 | Additional malformed files and locally chosen behavior for unspecified edge cases |

Each execution checks the expected exit status, standard output, and standard
error. Missing-file errors check their path prefix because operating-system
error wording varies. Tests use fresh temporary directories, enforce execution
timeouts, and check that guest file operations do not create or modify files
in those directories. Tests generate executable bytes directly and do not
require an assembler.

Loader tests compile a small C probe that inspects every field and all data
bytes, including a maximum-sized data segment. Arithmetic expectations are
computed independently using Python integer arithmetic. Trace and filesystem
tests use explicit expected output; they are not snapshots captured from the
interpreter.

Run a single group:

```sh
make test-s1
make test-s2
make test-s3
make test-s4
make test-policy
```

Display every test name, change the reproducible random seed, or increase the
number of arithmetic vectors:

```sh
python3 tests/run_tests.py --verbose
python3 tests/run_tests.py --subset S3 --seed 42 --random-cases 200
```

There are six arithmetic cases per random vector; the default is 32 vectors.
Failures produce a nonzero exit status, making the runner suitable for CI.
`POLICY` cases describe this implementation's choices, such as short writes
at capacity. They do not establish compatibility with an external reference.

To check a separately compiled executable, including an instrumented build:

```sh
cc -std=c11 -Wall -Wextra -fsanitize=undefined mipsee.c -o /tmp/mipsee-ubsan
python3 tests/run_tests.py --binary /tmp/mipsee-ubsan
```

The loader probe is compiled separately using `CC` from the environment (or
`cc`); `--binary` selects the executable used for execution tests.

### Included example programs

| Group | Checks |
| --- | --- |
| Subset 1 | Loaded fields, byte order, initial data, missing files, invalid magic |
| Subset 2 | Basic instructions, zero register, integer and character output, exit, execution errors |
| Subset 3 | Leading-bit counts, arithmetic, branches, signed comparison, memory, overflow and address errors |
| Subset 4 | Source tracing, changed-register output, file creation, descriptor reuse, read/write/close and limits |

Example commands:

```sh
./mipsee examples/hi_addi_1.mipsee
./mipsee examples/clo_and_clz.mipsee
./mipsee examples/load_store.mipsee
./mipsee examples/fs_1.mipsee
./mipsee -t examples/hi_addi_1.mipsee
./mipsee examples/io_no_e.mipsee < examples/io_no_e.1.txt
```

The optional loader harness can be built separately:

```sh
cc -DTEST_SUBSET_1 -Dmain=mipsee_main mipsee.c test_subset_1.c -o loader_test
./loader_test examples/sample_data.mipsee
```

## Feature summary

- Little-endian executable loading with magic-number validation.
- Arithmetic, logical, branch, leading-bit-count, and memory instructions.
- Signed overflow, alignment, instruction, and memory bounds checks.
- Integer, character, and string output, character input, and program exit.
- Source-line tracing and register-change reporting.
- An in-memory filesystem supporting open, read, write, and close, with six
  files, eight open descriptors, and 128 bytes per file.

Emulated file operations do not read or write host files. Each invocation
starts with an empty emulated filesystem and zeroed registers.

## Files

- `mipsee.c`: loader, interpreter, tracing, and emulated filesystem.
- `Makefile`, `mipsee.mk`: build configuration.
- `examples/`: assembly, executable files, disassemblies, and sample input.
- `test_subset_1.c`: optional executable-loader test harness.
- `tests/run_tests.py`: automated black-box and boundary tests.
- `tests/loader_probe.c`: independent entry point for inspecting loaded fields.

Examples prefixed with `err_`, and the invalid-magic example, intentionally
fail. They exercise error reporting.

The implementation has been checked locally against the included examples
and additional boundary tests. Exact compatibility with an external reference
implementation has not been verified.
