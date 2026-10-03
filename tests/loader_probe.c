// Exercise the public loader independently of the interpreter.
#define main interpreter_main
#include "../mipsee.c"
#undef main

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    struct mipsee_file p = {0};
    read_mipsee_file(argv[1], &p);
    printf("%" PRIu32 " %" PRIu32 " %u\n",
           p.num_instructions, p.entry_point, (unsigned)p.memory_size);
    for (uint32_t i = 0; i < p.num_instructions; i++)
        printf("%08" PRIx32 " %08" PRIx32 "\n", p.instructions[i], p.debug_offsets[i]);
    for (unsigned i = 0; i < p.memory_size; i++) printf("%02x", p.initial_data[i]);
    putchar('\n');
    free(p.instructions);
    free(p.debug_offsets);
    free(p.initial_data);
    return 0;
}
