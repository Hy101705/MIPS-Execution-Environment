// MIPS Execution Environment: executable loader and interpreter.
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <inttypes.h>
#include <limits.h>
#include <stdbool.h>
#include <string.h>

struct mipsee_file {
    uint32_t num_instructions;
    uint32_t entry_point;
    uint32_t *instructions;
    uint32_t *debug_offsets;
    uint16_t memory_size;
    uint8_t *initial_data;
};

#define DATA_BASE UINT32_C(0x10010000)
#define FILE_LIMIT 6
#define FD_LIMIT 8
#define FILE_CAPACITY 128

struct virtual_file {
    char *name;
    uint8_t data[FILE_CAPACITY];
    size_t size;
};
struct descriptor {
    bool open;
    unsigned file;
    unsigned mode;
    size_t position;
};
struct machine {
    uint32_t registers[32];
    struct mipsee_file *program;
    struct virtual_file files[FILE_LIMIT];
    struct descriptor descriptors[FD_LIMIT];
};

void read_mipsee_file(char *path, struct mipsee_file *executable);
void execute_mipsee(struct mipsee_file *executable, int trace_mode, char *path);
void print_uint32_in_hexadecimal(FILE *stream, uint32_t value);
void print_int32_in_decimal(FILE *stream, int32_t value);

// ============================================================================
// PROGRAM ENTRY POINT
// ============================================================================

int main(int argc, char *argv[]) {
    char *pathname;
    int trace_mode = 0;
    if (argc == 2) pathname = argv[1];
    else if (argc == 3 && strcmp(argv[1], "-t") == 0) {
        trace_mode = 1;
        pathname = argv[2];
    } else {
        fprintf(stderr, "Usage: mipsee [-t] <executable>\n");
        exit(1);
    }
    struct mipsee_file executable = {0};
    read_mipsee_file(pathname, &executable);
    execute_mipsee(&executable, trace_mode, pathname);
    free(executable.debug_offsets);
    free(executable.instructions);
    free(executable.initial_data);
    return 0;
}

// ============================================================================
// SHARED UTILITIES - errors, allocation and integer formatting
// ============================================================================

static void fail(const char *message) {
    fprintf(stderr, "%s\n", message);
    exit(1);
}

static void *allocate(size_t size) {
    void *p = malloc(size ? size : 1);
    if (!p) fail("MIPSEE error: out of memory");
    return p;
}

void print_uint32_in_hexadecimal(FILE *stream, uint32_t value) {
    fprintf(stream, "0x%08" PRIx32, value);
}

void print_int32_in_decimal(FILE *stream, int32_t value) {
    fprintf(stream, "%" PRIi32, value);
}

// ============================================================================
// SUBSET 1 - executable loading and little-endian file decoding
// ============================================================================

static uint32_t read_little(FILE *file, unsigned bytes) {
    uint32_t value = 0;
    for (unsigned i = 0; i < bytes; i++) {
        int byte = fgetc(file);
        if (byte == EOF) fail("Invalid MIPSEE file");
        value |= (uint32_t)byte << (8 * i);
    }
    return value;
}

void read_mipsee_file(char *path, struct mipsee_file *executable) {
    FILE *file = fopen(path, "rb");
    if (!file) { perror(path); exit(1); }
    const char magic[] = "MIPSEE";
    for (unsigned i = 0; i < 6; i++)
        if (fgetc(file) != magic[i]) fail("Invalid MIPSEE file");
    executable->num_instructions = read_little(file, 4);
    executable->entry_point = read_little(file, 4);
    uint64_t bytes = (uint64_t)executable->num_instructions * sizeof(uint32_t);
    if (bytes > SIZE_MAX) fail("Invalid MIPSEE file");
    executable->instructions = allocate((size_t)bytes);
    executable->debug_offsets = allocate((size_t)bytes);
    for (uint32_t i = 0; i < executable->num_instructions; i++)
        executable->instructions[i] = read_little(file, 4);
    for (uint32_t i = 0; i < executable->num_instructions; i++)
        executable->debug_offsets[i] = read_little(file, 4);
    executable->memory_size = (uint16_t)read_little(file, 2);
    executable->initial_data = allocate(executable->memory_size);
    for (unsigned i = 0; i < executable->memory_size; i++)
        executable->initial_data[i] = (uint8_t)read_little(file, 1);
    fclose(file);
}

// ============================================================================
// SUBSET 2 - integer interpretation and invalid-instruction reporting
// ============================================================================

static int32_t signed_word(uint32_t value) {
    if (value <= INT32_MAX) return (int32_t)value;
    return -1 - (int32_t)(UINT32_MAX - value);
}

static int32_t immediate(uint32_t instruction) {
    uint32_t value = instruction & 0xffff;
    return value < 0x8000 ? (int32_t)value : (int32_t)value - 0x10000;
}

static void bad_instruction(uint32_t instruction) {
    fputs("MIPSEE error: bad instruction ", stderr);
    print_uint32_in_hexadecimal(stderr, instruction);
    fputc('\n', stderr);
    exit(1);
}

// ============================================================================
// SUBSET 3 - data-segment access, strings and signed-overflow checks
// ============================================================================

static size_t memory_index(struct machine *m, uint32_t address, unsigned size) {
    uint64_t end = (uint64_t)address + size;
    if (address % size || address < DATA_BASE ||
        end > (uint64_t)DATA_BASE + m->program->memory_size) {
        const char *name = size == 4 ? "word" : size == 2 ? "half" : "byte";
        fprintf(stderr, "MIPSEE error: bad address for %s access: ", name);
        print_uint32_in_hexadecimal(stderr, address);
        fputc('\n', stderr);
        exit(1);
    }
    return address - DATA_BASE;
}

static char *memory_string(struct machine *m, uint32_t address) {
    size_t start = memory_index(m, address, 1);
    size_t i = start;
    while (i < m->program->memory_size && m->program->initial_data[i]) i++;
    if (i == m->program->memory_size)
        (void)memory_index(m, DATA_BASE + (uint32_t)i, 1);
    return (char *)m->program->initial_data + start;
}

static uint32_t checked_add(uint32_t a, uint32_t b) {
    int64_t result = (int64_t)signed_word(a) + signed_word(b);
    if (result < INT32_MIN || result > INT32_MAX)
        fail("MIPSEE error: addition would overflow");
    return (uint32_t)result;
}

// ============================================================================
// SUBSET 4 - in-memory file operations
// ============================================================================

static uint32_t file_open(struct machine *m) {
    uint32_t *r = m->registers;
    if (r[5] > 1) return UINT32_MAX;
    if (r[4] < DATA_BASE || r[4] - DATA_BASE >= m->program->memory_size)
        return UINT32_MAX;
    size_t start = r[4] - DATA_BASE;
    if (!memchr(m->program->initial_data + start, 0, m->program->memory_size - start))
        return UINT32_MAX;
    char *name = (char *)m->program->initial_data + start;
    unsigned fd = 0;
    while (fd < FD_LIMIT && m->descriptors[fd].open) fd++;
    if (fd == FD_LIMIT) return UINT32_MAX;
    unsigned f = 0;
    while (f < FILE_LIMIT && (!m->files[f].name || strcmp(name, m->files[f].name))) f++;
    if (f == FILE_LIMIT) {
        if (r[5] == 0) return UINT32_MAX;
        f = 0;
        while (f < FILE_LIMIT && m->files[f].name) f++;
        if (f == FILE_LIMIT) return UINT32_MAX;
        m->files[f].name = allocate(strlen(name) + 1);
        strcpy(m->files[f].name, name);
    }
    m->descriptors[fd] = (struct descriptor){true, f, r[5], 0};
    return fd;
}

static uint32_t file_transfer(struct machine *m, bool writing) {
    uint32_t *r = m->registers;
    if (r[4] >= FD_LIMIT || signed_word(r[6]) < 0) return UINT32_MAX;
    struct descriptor *d = &m->descriptors[r[4]];
    if (!d->open || d->mode != (unsigned)writing) return UINT32_MAX;
    struct virtual_file *f = &m->files[d->file];
    size_t available = writing ? FILE_CAPACITY - d->position :
        (d->position < f->size ? f->size - d->position : 0);
    size_t count = r[6] < available ? r[6] : available;
    // Validate the transfer before changing guest memory or file contents.
    if (count && (r[5] < DATA_BASE ||
        (uint64_t)r[5] + count > (uint64_t)DATA_BASE + m->program->memory_size))
        return UINT32_MAX;
    for (size_t i = 0; i < count; i++) {
        size_t index = (size_t)(r[5] - DATA_BASE) + i;
        if (writing) f->data[d->position + i] = m->program->initial_data[index];
        else m->program->initial_data[index] = f->data[d->position + i];
    }
    d->position += count;
    if (writing && d->position > f->size) f->size = d->position;
    return (uint32_t)count;
}

// ============================================================================
// SUBSET 4 - source-line and register tracing
// ============================================================================

static FILE *open_source(char *path) {
    size_t length = strlen(path), stem = length;
    if (length >= 7 && strcmp(path + length - 7, ".mipsee") == 0) stem -= 7;
    char *name = allocate(stem + 3);
    memcpy(name, path, stem);
    strcpy(name + stem, ".s");
    FILE *source = fopen(name, "r");
    if (!source) { perror(name); free(name); exit(1); }
    free(name);
    return source;
}

static void trace_line(FILE *source, uint32_t offset) {
    if (fseek(source, (long)offset, SEEK_SET) != 0) return;
    int ch;
    while ((ch = fgetc(source)) != EOF) {
        putchar(ch);
        if (ch == '\n') break;
    }
}

static void trace_registers(const uint32_t old[32], const uint32_t current[32]) {
    static const char *names[32] = {
        "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
        "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
        "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
        "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"
    };
    for (unsigned i = 1; i < 32; i++) {
        if (old[i] == current[i]) continue;
        printf("   $%s: ", names[i]);
        print_uint32_in_hexadecimal(stdout, old[i]);
        fputs(" -> ", stdout);
        print_uint32_in_hexadecimal(stdout, current[i]);
        putchar('\n');
    }
}

// ============================================================================
// SHARED SYSCALL DISPATCH - Subsets 2, 3 and 4
// ============================================================================

static bool system_call(struct machine *m) {
    uint32_t *r = m->registers;
    switch (r[2]) {
    // Subset 2: integer output, exit and character output.
    case 1: print_int32_in_decimal(stdout, signed_word(r[4])); break;
    // Subset 3: string output.
    case 4: fputs(memory_string(m, r[4]), stdout); break;
    // Subset 2: exit and character output.
    case 10: return true;
    case 11: putchar((unsigned char)r[4]); break;
    // Subset 3: character input.
    case 12: r[2] = (uint32_t)getchar(); break;
    // Subset 4: open, read, write and close guest files.
    case 13: r[2] = file_open(m); break;
    case 14: r[2] = file_transfer(m, false); break;
    case 15: r[2] = file_transfer(m, true); break;
    case 16:
        if (r[4] >= FD_LIMIT || !m->descriptors[r[4]].open) r[2] = UINT32_MAX;
        else { m->descriptors[r[4]].open = false; r[2] = 0; }
        break;
    default: fail("MIPSEE error: bad syscall number");
    }
    return false;
}

// ============================================================================
// SHARED EXECUTION LOOP - Subset 2 core with Subset 3/4 extensions
// ============================================================================

void execute_mipsee(struct mipsee_file *executable, int trace_mode, char *path) {
    // Subset 2: zero registers, entry point and instruction fetch/decode.
    struct machine m = {.program = executable};
    uint32_t *r = m.registers;
    int64_t pc = executable->entry_point;
    FILE *source = trace_mode ? open_source(path) : NULL;
    bool stopped = false;
    while (!stopped) {
        if (pc < 0 || (uint64_t)pc >= executable->num_instructions)
            fail("MIPSEE error: execution past the end of instructions");
        uint32_t ins = executable->instructions[pc];
        unsigned op = ins >> 26, rs = (ins >> 21) & 31;
        unsigned rt = (ins >> 16) & 31, rd = (ins >> 11) & 31;
        unsigned fn = ins & 63, shift = (ins >> 6) & 31;
        int32_t imm = immediate(ins);
        int64_t next = pc + 1;
        uint32_t old[32];
        // Subset 4: print the source line and capture the old register values.
        if (source) {
            trace_line(source, executable->debug_offsets[pc]);
            memcpy(old, r, sizeof old);
        }
        if (op == 0 && fn == 12) {
            // Subset 2 SYSCALL instruction; dispatch includes Subset 3/4 calls.
            stopped = system_call(&m);
        } else if (op == 0 && (ins & 0x7ff) == 0x50) {
            // Subset 3: CLZ.
            uint32_t bits = r[rs];
            unsigned count = 0;
            while (count < 32 && !(bits & UINT32_C(0x80000000))) {
                count++; bits <<= 1;
            }
            r[rd] = count;
        } else if (op == 0 && (ins & 0x7ff) == 0x51) {
            // Subset 3: CLO.
            uint32_t bits = ~r[rs];
            unsigned count = 0;
            while (count < 32 && !(bits & UINT32_C(0x80000000))) {
                count++; bits <<= 1;
            }
            r[rd] = count;
        } else if (op == 0 && shift == 0) {
            // Subset 2: ADD. Subset 3: ADDU, SLT and overflow checking.
            switch (fn) {
            case 32: r[rd] = checked_add(r[rs], r[rt]); break;
            case 33: r[rd] = r[rs] + r[rt]; break;
            case 42: r[rd] = signed_word(r[rs]) < signed_word(r[rt]); break;
            default: bad_instruction(ins);
            }
        } else if (op == 28 && fn == 2 && shift == 0) {
            // Subset 3: MUL.
            r[rd] = (uint32_t)((uint64_t)r[rs] * r[rt]);
        } else if (op == 8) {
            // Subset 2: ADDI, with Subset 3 overflow checking.
            r[rt] = checked_add(r[rs], (uint32_t)imm);
        } else if (op == 9) {
            // Subset 3: ADDIU.
            r[rt] = r[rs] + (uint32_t)imm;
        } else if (op == 13) {
            // Subset 2: ORI.
            r[rt] = r[rs] | (ins & 0xffff);
        } else if (op == 15 && rs == 0) {
            // Subset 2: LUI.
            r[rt] = (ins & 0xffff) << 16;
        } else if (op == 4 || op == 5) {
            // Subset 3: BEQ and BNE.
            if ((r[rs] == r[rt]) == (op == 4)) next = pc + imm;
        } else if (op == 32 || op == 33 || op == 35 ||
                   op == 40 || op == 41 || op == 43) {
            // Subset 3: LB, LH, LW, SB, SH and SW.
            unsigned size = (op & 7) == 0 ? 1 : (op & 7) == 1 ? 2 : 4;
            uint32_t address = r[rs] + (uint32_t)imm;
            size_t index = memory_index(&m, address, size);
            if (op >= 40) {
                for (unsigned i = 0; i < size; i++)
                    executable->initial_data[index + i] = (uint8_t)(r[rt] >> (8 * i));
            } else {
                uint32_t value = 0;
                for (unsigned i = 0; i < size; i++)
                    value |= (uint32_t)executable->initial_data[index + i] << (8 * i);
                if (size == 1 && (value & 0x80)) value |= UINT32_C(0xffffff00);
                if (size == 2 && (value & 0x8000)) value |= UINT32_C(0xffff0000);
                r[rt] = value;
            }
        } else {
            bad_instruction(ins);
        }
        r[0] = 0;
        // Subset 4: report changed register values after execution.
        if (source) trace_registers(old, r);
        pc = next;
    }
    if (source) fclose(source);
    for (unsigned i = 0; i < FILE_LIMIT; i++) free(m.files[i].name);
}
