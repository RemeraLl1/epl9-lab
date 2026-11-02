/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Compile the unmodified GNU MN103 reader against these local callbacks.
   This is not binary-compatible with libopcodes or a replacement BFD API. */
#ifndef EPL9_DISASSEMBLE_H
#define EPL9_DISASSEMBLE_H
#include <stdint.h>
typedef uint32_t bfd_vma;
typedef unsigned char bfd_byte;
struct disassemble_info {
    unsigned long mach;
    void *stream;
    int (*fprintf_func)(void *, const char *, ...);
    int (*read_memory_func)(bfd_vma, bfd_byte *, unsigned int, struct disassemble_info *);
    void (*memory_error_func)(int, bfd_vma, struct disassemble_info *);
    void (*print_address_func)(bfd_vma, struct disassemble_info *);
};
static uint32_t bfd_getl16(const bfd_byte *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8);
}
static uint32_t bfd_getb16(const bfd_byte *p) {
    return ((uint32_t)p[0] << 8) | (uint32_t)p[1];
}
static uint32_t bfd_getl32(const bfd_byte *p) {
    return bfd_getl16(p) | (bfd_getl16(p + 2) << 16);
}
static uint32_t bfd_getb32(const bfd_byte *p) {
    return (bfd_getb16(p) << 16) | bfd_getb16(p + 2);
}
int print_insn_mn10300(bfd_vma, struct disassemble_info *);
#endif
