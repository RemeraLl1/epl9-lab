/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Read-only CLI adapter for unmodified GNU binutils MN103 disassembly.
   Arguments: image base start_offset stop_offset [machine=332].
   Output: address TAB raw hex TAB mnemonic TAB operands.
   No recursion, symbol inference, instruction-boundary discovery or execution. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
#include "disassemble.h"

static unsigned char *bytes;
static size_t byte_count;
static uint32_t base;
static int failed;
struct text_buffer { char text[1024]; size_t used; };

static int append(void *opaque, const char *format, ...) {
    struct text_buffer *out = opaque;
    size_t available = sizeof(out->text) - out->used;
    va_list args;
    int count;
    va_start(args, format);
    count = vsnprintf(out->text + out->used, available, format, args);
    va_end(args);
    if (count < 0 || (size_t)count >= available) { failed = 1; return -1; }
    out->used += count;
    return count;
}

static int read_bytes(bfd_vma address, bfd_byte *out, unsigned int length,
                      struct disassemble_info *info) {
    size_t offset;
    (void)info;
    if (address < base) return 1;
    offset = address - base;
    if (offset > byte_count || length > byte_count - offset) return 1;
    memcpy(out, bytes + offset, length);
    return 0;
}

static void memory_error(int status, bfd_vma address, struct disassemble_info *info) {
    (void)status; (void)info;
    failed = 1;
    fprintf(stderr, "Out-of-range instruction read at 0x%08lx\n", (unsigned long)address);
}

static void address_text(bfd_vma address, struct disassemble_info *info) {
    append(info->stream, "0x%08lx", (unsigned long)address);
}

static uint64_t number(const char *text) {
    char *end;
    uint64_t n;
    errno = 0;
#ifdef _WIN32
    n = _strtoui64(text, &end, 0);
#else
    n = strtoull(text, &end, 0);
#endif
    if (errno || end == text || *end || *text == '-') {
        fprintf(stderr, "Invalid number: %s\n", text); exit(2);
    }
    return n;
}

int main(int argc, char **argv) {
    FILE *input;
    long file_size;
    uint64_t mapping, start, stop, mach;
    size_t offset;
    struct disassemble_info info;
    struct text_buffer out;
    if (argc != 5 && argc != 6) {
        fprintf(stderr, "Usage: mn103-reader image base start_offset stop_offset [machine=332]\n");
        return 2;
    }
    mapping = number(argv[2]); start = number(argv[3]); stop = number(argv[4]);
    mach = argc == 6 ? number(argv[5]) : 332;
    if (mapping > UINT32_MAX || start >= stop || (mach != 300 && mach != 330 && mach != 332)) return 2;
    input = fopen(argv[1], "rb");
    if (!input) { perror("open input"); return 2; }
    if (fseek(input, 0, SEEK_END) || (file_size = ftell(input)) <= 0 ||
        file_size > 64 * 1024 * 1024 || fseek(input, 0, SEEK_SET)) { fclose(input); return 2; }
    byte_count = (size_t)file_size;
    if (mapping + byte_count > UINT64_C(0x100000000) || stop > byte_count) { fclose(input); return 2; }
    bytes = malloc(byte_count);
    if (!bytes) { fclose(input); return 2; }
    if (fread(bytes, 1, byte_count, input) != byte_count) { fclose(input); free(bytes); return 2; }
    fclose(input);
    base = (uint32_t)mapping;
    memset(&info, 0, sizeof(info));
    info.mach = (unsigned long)mach;
    info.stream = &out; info.fprintf_func = append; info.read_memory_func = read_bytes;
    info.memory_error_func = memory_error; info.print_address_func = address_text;
    for (offset = (size_t)start; offset < stop;) {
        int length, i;
        memset(&out, 0, sizeof(out));
        length = print_insn_mn10300(base + (uint32_t)offset, &info);
        if (failed || length <= 0 || (size_t)length > byte_count - offset) { free(bytes); return 2; }
        printf("%08lx\t", (unsigned long)(base + (uint32_t)offset));
        for (i = 0; i < length; i++) printf("%02x", bytes[offset + i]);
        printf("\t%s\n", out.text);
        offset += length;
    }
    free(bytes);
    return 0;
}
