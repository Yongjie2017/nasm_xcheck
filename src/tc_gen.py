#!/usr/bin/env python3

import os
import re
import json

NASM_HEADER = """
        bits 64
        section .text
        global test_%s

test_%s:
        push rbp
        mov rbp,rsp
"""
NASM_FOOTER = """
near1:
        nop
        pop rbp
        ret
"""

GAS_HEADER = """
        .text
        .globl  test_%s

test_%s:
        pushq   %%rbp
        movq    %%rsp, %%rbp
"""
GAS_FOOTER = """
near1:
        nop
        popq    %rbp
        ret
"""

NASM = 0
GAS = 1

operand_to_nasm_gas_mapping = {
    "bndreg"           : [[ "bnd1"],
                          ["%bnd1"]],
    "fpu0"             : [[ "st0"],
                          ["%st0"]],
    "fpureg"           : [[ "st1"],
                          ["%st1"]],
    "fpureg|to"        : [[ "st7"],
                          ["%st7"]],
    "ignore"           : [None,
                          None],
    "imm"              : [[ "0x10"],
                          ["$0x10"]],
    "imm16"            : [[ "0x55AA"],
                          ["$0x55AA"]],
    "imm16|abs"        : [["[a16 abs 0x55AA]"],
                          ["(a16 abs $0x55AA)"]],
    "imm16|far"        : [["far word 0x55AA"],
                          ["far word $0x55AA"]],
    "imm16:imm16"      : [[ "0xFFFF:0000"],
                          ["$0xFFFF:$0000"]],
    "imm16:imm16|far"  : [["far 0xFFFF:0000"],
                          ["far $0xFFFF:$0000"]],
    "imm16:imm32"      : [[ "0xFFFF:0x55AA55AA"],
                          ["$0xFFFF:$0x55AA55AA"]],
    "imm16:imm32|far"  : [["far 0xFFFF:0x55AA55AA"],
                          ["far $0xFFFF:$0x55AA55AA"]],
    "imm16|near"       : [["word near1"],
                          ["word near1"]],
    "imm32"            : [[ "0x55AA55AA"],
                          ["$0x55AA55AA"]],
    "imm32|abs"        : [["[a32 abs 0x55AA55AA]"],
                          ["(a32 abs $0x55AA55AA)"]],
    "imm32|far"        : [["far word 0x55AA55AA"],
                          ["far word $0x55AA55AA"]],
    "imm32|near"       : [["word near1"],
                          ["word near1"]],
    "imm64"            : [[ "0x55AA55AA55AA55AA"],
                          ["$0x55AA55AA55AA55AA"]],
    "imm64|abs"        : [["[a64 abs 0x55AA55AA55AA55AA]"],
                          ["(a64 abs $0x55AA55AA55AA55AA)"]],
    "imm64|near"       : [["word near1"],
                          ["word near1"]],
    "imm8"             : [[ "0x55"],
                          ["$0x55"]],
    "imm8|abs"         : [["[a8 abs 0x55]"],
                          ["(a8 abs $0x55)"]],
    "imm8|near|short"  : [["short near1"],
                          ["short near1"]],
    "imm8|short"       : [["short near1"],
                          ["short near1"]],
    "imm:imm"          : [[ "0xFFFF:0000"],
                          ["$0xFFFF:$0000"]],
    "imm|near"         : [[ "0x10"],
                          ["$0x10"]],
    "kreg"             : [[ "k1"],
                          ["%k1"]],
    "kreg16"           : [[ "k1"],
                          ["%k1"]],
    "kreg16*"          : [[ "k1", ""],
                          ["%k1", ""]],
    "kreg32"           : [[ "k1"],
                          ["%k1"]],
    "kreg32*"          : [[ "k1", ""],
                          ["%k1", ""]],
    "kreg64"           : [[ "k1"],
                          ["%k1"]],
    "kreg64*"          : [[ "k1", ""],
                          ["%k1", ""]],
    "kreg8"            : [[ "k1"],
                          ["%k1"]],
    "kreg8*"           : [[ "k1", ""],
                          ["%k1", ""]],
    "kreg|mask"        : [[ "k1{k7}"],
                          ["%k1{%k7}"]],
    "kreg|rs2"         : [[ "k1+1"],
                          ["%k1+1"]],
    "krm16"            : [[ "k1", "word [eax]"],
                          ["$k1", "word (%eax)"]],
    "krm32"            : [[ "k1", "dword [eax]"],
                          ["$k1", "dword (%eax)"]],
    "krm64"            : [[ "k1", "qword [rax]"],
                          ["$k1", "qword (%rax)"]],
    "krm8"             : [[ "k1", "byte [eax]"],
                          ["$k1", "byte (%eax)"]],
    "mem"              : [["[rax]"],
                          ["(%rax)"]],
    "mem128"           : [["oword [rax+r14*8]"],
                          ["oword (%rax,%r14,8)"]],
    "mem128|mask"      : [["oword [rax+r14*8]{k1}"],
                          ["oword (%rax,%r14,8){%k1}"]],
    "mem16"            : [["word [ax]", "word [ax+cx*8]", "word [ax+cx*8+0x10]", "word [rax]", "word [rax+rcx*8]"],
                          ["word (%ax)", "word (%ax,%cx,8)", "word $0x10(%ax,%cx,8)", "word (%rax)", "word (%rax,%rcx,8)"]],
    "mem16|far"        : [["far word [eax]", "far word [eax]"],
                          ["far word (%eax)", "far word (%eax)"]],
    "mem16|mask"       : [["word [ax]{k1}", "word [ax+cx*8]{k1}", "word [ax+cx*8+0x10]{k1}"],
                          ["word (%ax){%k1}", "word (%ax,%cx,8){%k1}", "word $0x10(%ax,%cx,8){%k1}"]],
    "mem256"           : [["yword [rax]", "yword [rax+r14*8]"],
                          ["yword (%rax)", "yword (%rax,%r14,8)"]],
    "mem256|mask"      : [["yword [rax+r14*8]{k1}"],
                          ["yword (%rax,%r14,8){%k1}"]],
    "mem32"            : [["dword [eax]", "dword [eax+ecx*8]", "dword [eax+ecx*8+0x10]"],
                          ["dword (%eax)", "dword (%eax,%ecx,8)", "dword $0x10(%eax,%ecx,8)"]],
    "mem32|far"        : [["far dword [eax]", "far dword [eax+ecx*8]", "far dword [eax+ecx*8+0x10]"],
                          ["far dword (%eax)", "far dword (%eax,%ecx,8)", "far dword $0x10(%eax,%ecx,8)"]],
    "mem32|mask"       : [["far dword [eax]{k1}", "far dword [eax+ecx*8]{k1}", "far dword [eax+ecx*8+0x10]{k1}"],
                          ["far dword (%eax){%k1}", "far dword (%eax,%ecx,8){%k1}", "far dword $0x10(%eax,%ecx,8){%k1}"]],
    "mem512"           : [["zword [rax]", "zword [rax+r14*8]", "zword [rax+r14*8+0x10]"],
                          ["zword (%rax)", "zword (%rax,%r14,8)", "zword $0x10(%rax,%r14,8)"]],
    "mem512|mask"      : [["zword [rax]{k1}", "zword [rax+r14*8]{k1}", "zword [rax+r14*8+0x10]{k1}"],
                          ["zword (%rax){%k1}", "zword (%rax,%r14,8){%k1}", "zword $0x10(%rax,%r14,8){%k1}"]],
    "mem64"            : [["qword [rax]", "qword [rax+rcx*8]", "qword [rax+rcx*8+0x10]"],
                          ["qword (%rax)", "qword (%rax,%rcx,8)", "qword $0x10(%rax,%rcx,8)"]],
    "mem64|far"        : [["far qword [rax]", "far qword [rax+rcx*8]", "far qword [rax+rcx*8+0x10]"],
                          ["far qword (%rax)", "far qword (%rax,%rcx,8)", "far qword $0x10(%rax,%rcx,8)"]],
    "mem64|mask"       : [["qword [rax]{k1}", "qword [rax+rcx*8]{k1}", "qword [rax+rcx*8+0x10]{k1}"],
                          ["qword (%rax){%k1}", "qword (%rax,%rcx,8){%k1}", "qword $0x10(%rax,%rcx,8){%k1}"]],
    "mem8"             : [["byte [eax+ecx*8+0x10]"],
                          ["byte $0x10(%eax,%ecx,8)"]],
    "mem80"            : [[ "[0x1000]"],
                          ["[$0x1000]"]],
    "mem_offs"         : [["[near1]"],
                          ["[near1]"]],
    "mmxreg"           : [["mm0"],
                          ["%mm0"]],
    "mmxrm"            : [["mm1", "dword [eax]"],
                          ["%mm1", "dword (%eax)"]],
    "mmxrm64"          : [["mm2", "qword [rax]"],
                          ["%mm2", "qword (%rax)"]],
    "reg16"            : [[ "ax"],
                          ["%ax"]],
    "reg16?"           : [[ "ax", ""],
                          ["%ax", ""]],
    "reg32"            : [[ "eax"],
                          ["%eax"]],
    "reg32*"           : [[ "eax", ""],
                          ["%eax", ""]],
    "reg32?"           : [[ "eax", ""],
                          ["%eax", ""]],
    "reg32na"          : [[ "ecx"],
                          ["%ecx"]],
    "reg64"            : [[ "rax"],
                          ["%rax"]],
    "reg64*"           : [[ "rax", ""],
                          ["%rax", ""]],
    "reg64?"           : [[ "rax", ""],
                          ["%rax", ""]],
    "reg64:reg64"      : [[ "rax"],
                          ["%rax"]],
    "reg8"             : [[ "bl"],
                          ["%bl"]],
    "reg8?"            : [["al", ""],
                          ["%al", ""]],
    "reg_al"           : [["al"],
                          ["%al"]],
    "reg_ax"           : [["ax"],
                          ["%ax"]],
    "reg_bx"           : [["bx"],
                          ["%bx"]],
    "reg_cl"           : [["cl"],
                          ["%cl"]],
    "reg_creg"         : [["cr0"],
                          ["%cr0"]],
    "reg_cs"           : [["cs"],
                          ["%cs"]],
    "reg_cx"           : [["cx"],
                          ["%cx"]],
    "reg_dreg"         : [["dr0"],
                          ["%dr0"]],
    "reg_ds"           : [["ds"],
                          ["%ds"]],
    "reg_dx"           : [["dx"],
                          ["%dx"]],
    "reg_eax"          : [["eax"],
                          ["%eax"]],
    "reg_ecx"          : [["ecx"],
                          ["%ecx"]],
    "reg_edx"          : [["edx"],
                          ["%edx"]],
    "reg_es"           : [["es"],
                          ["%es"]],
    "reg_fs"           : [["fs"],
                          ["%fs"]],
    "reg_gs"           : [["gs"],
                          ["%gs"]],
    "reg_rax"          : [["rax"],
                          ["%rax"]],
    "reg_rcx"          : [["rcx"],
                          ["%rcx"]],
    "reg_sreg"         : [["cs", "ds", "ss", "fs", "gs", "es"],
                          ["%cs", "%ds", "%ss", "%fs", "%gs", "%es"]],
    "reg_ss"           : [["ss"],
                          ["%ss"]],
    "reg_treg"         : [["tr0"],
                          ["%tr0"]],
    "rm16"             : [["ax", "word [eax]"],
                          ["%ax", "word (%eax)"]],
    "rm16*"            : [["ax", "word [eax]", ""],
                          ["%ax", "word (%eax)", ""]],
    "rm16|near"        : [["ax", "word near1"],
                          ["%ax", "word near1"]],
    "rm32"             : [["eax", "dword [eax]"],
                          ["%eax", "dword (%eax)"]],
    "rm32*"            : [["eax", "dword [eax]", ""],
                          ["%eax", "dword (%eax)", ""]],
    "rm32|er"          : [["eax", "dword [eax]", "eax,{rd-sae}"],
                          ["%eax", "dword (%eax)", "%eax,{rd-sae}"]],
    "rm32|near"        : [["eax", "dword near1"],
                          ["%eax", "dword near1"]],
    "rm64"             : [["rax", "qword [rax]"],
                          ["%rax", "qword (%rax)"]],
    "rm64*"            : [["rax", "qword [rax]", ""],
                          ["%rax", "qword (%rax)", ""]],
    "rm64|er"          : [["rax", "qword [rax]", "rax,{rd-sae}"],
                          ["%rax", "qword (%rax)", "%rax,{rd-sae}"]],
    "rm64|near"        : [["rax", "[rax+r14*8+0x10]", "qword near1"],
                          ["%rax", "$0x10(%rax,%r14,8)", "qword near1"]],
    "rm8"              : [["al", "byte [eax]"],
                          ["%al", "byte (%eax)"]],
    "rm_sel"           : [["ax", "word [eax]", "eax", "dword [eax]", "rax", "qword [rax]"],
                          ["%ax", "word (%eax)", "%eax", "dword (%eax)", "%rax", "qword (%rax)"]],
    "sbytedword32"     : [["0x7F"],
                          ["$0x7F"]],
    "sbytedword64"     : [["0x7F"],
                          ["$0x7F"]],
    "sbyteword16"      : [["0x7F"],
                          ["$0x7F"]],
    "sdword64"         : [["0x55AA55AA"],
                          ["$0x55AA55AA"]],
    "spec4"            : [["{dfv=}", "{dfv=cf}", "{dfv=zf}", "{dfv=sf}", "{dfv=of}", "{dfv=cf,zf}", "{dfv=sf,of}", "{dfv=cf,zf,of}", "{dfv=cf,zf,sf,of}"],
                          ["{dfv=}", "{dfv=cf}", "{dfv=zf}", "{dfv=sf}", "{dfv=of}", "{dfv=cf,zf}", "{dfv=sf,of}", "{dfv=cf,zf,of}", "{dfv=cf,zf,sf,of}"]],
    "tmmreg"           : [["tmm0", "tmm1", "tmm2"],
                          ["%tmm0", "%tmm1", "%tmm2"]],
    "udword64"         : [["qword [rax]"],
                          ["qword (%rax)"]],
    "unity"            : [["0x10"],
                          ["$0x10"]],
    "void"             : [[""],
                          [""]],
    "xmem32"           : [["dword [rbp+xmm7*2+0x8]"],
                          ["dword $0x8(%rbp,%xmm7,2)"]],
    "xmem32|mask"      : [["dword [rbp+xmm7*2+0x8]", "dword [rbp+xmm7*2]{k1}"],
                          ["dword $0x8(%rbp,%xmm7,2)", "dword (%rbp,%xmm7,2){%k1}"]],
    "xmem64"           : [["qword [rbp+xmm7*2+0x8]"],
                          ["qword $0x8(%rbp,%xmm7,2)"]],
    "xmem64|mask"      : [["qword [rbp+xmm7*2+0x8]", "qword [rbp+xmm7*2]{k1}"],
                          ["qword $0x8(%rbp,%xmm7,2)", "qword (%rbp,%xmm7,2){%k1}"]],
    "xmm0"             : [["xmm0"],
                          ["%xmm0"]],
    "xmmreg"           : [["xmm1"],
                          ["%xmm1"]],
    "xmmreg*"          : [["xmm2", ""],
                          ["%xmm2", ""]],
    "xmmreg|er"        : [["xmm7,{rd-sae}"],
                          ["%xmm7,{rd-sae}"]],
    "xmmreg|mask"      : [["xmm0", "xmm0{k7}"],
                          ["%xmm0", "%xmm0{%k7}"]],
    "xmmreg|mask|z"    : [["xmm0", "xmm0{k7}", "xmm0{k7}{z}"],
                          ["%xmm0", "%xmm0{%k7}", "%xmm0{%k7}{z}"]],
    "xmmrm"            : [["xmm4", "oword [rax+r14*8]"],
                          ["%xmm4", "oword (%rax,%r14,8)"]],
    "xmmrm128"         : [["xmm5", "oword [rax+r14*8]"],
                          ["%xmm5", "oword (%rax,%r14,8)"]],
    "xmmrm128*"        : [["xmm2", "oword [rax+r14*8]", ""],
                          ["%xmm2", "oword (%rax,%r14,8)", ""]],
    "xmmrm128|b16"     : [["xmm7", "oword [rax]", "oword [rbp+r14*2+0x8]", "word [rax]{1to8}", "word [rbp+r14*2+0x8]{1to8}"],
                          ["%xmm7", "oword (%rax)", "oword $0x8(%rbp,%r14,2)", "word (%rax){1to8}", "word $0x8(%rbp,%r14,2){1to8}"]],
    "xmmrm128|b16|er"  : [["xmm7", "oword [rax]", "oword [rbp+r14*2+0x8]", "xmm7,{rd-sae}"],
                          ["%xmm7", "oword (%rax)", "oword $0x8(%rbp,%r14,2)", "%xmm7,{rd-sae}"]],
    "xmmrm128|b16|sae" : [["xmm7", "oword [rax]", "oword [rbp+r14*2+0x8]", "xmm7,{sae}"],
                          ["%xmm7", "oword (%rax)", "oword $0x8(%rbp,%r14,2)", "%xmm7,{sae}"]],
    "xmmrm128|b32"     : [["xmm7", "oword [rax]", "oword [rbp+r14*2+0x8]", "dword [rax]{1to4}", "dword [rbp+r14*2+0x8]{1to4}"],
                          ["%xmm7", "oword (%rax)", "oword $0x8(%rbp,%r14,2)", "dword (%rax){1to4}", "dword $0x8(%rbp,%r14,2){1to4}"]],
    "xmmrm128|b32*"    : [["xmm7", "oword [rax]", "oword [rbp+r14*2+0x8]", "dword [rax]{1to4}", "dword [rbp+r14*2+0x8]{1to4}", ""],
                          ["%xmm7", "oword (%rax)", "oword $0x8(%rbp,%r14,2)", "dword (%rax){1to4}", "dword $0x8(%rbp,%r14,2){1to4}", ""]],
    "xmmrm128|b64"     : [["xmm7", "oword [rax]", "oword [rbp+r14*2+0x8]", "qword [rax]{1to2}", "qword [rbp+r14*2+0x8]{1to2}"],
                          ["%xmm7", "oword (%rax)", "oword $0x8(%rbp,%r14,2)", "qword (%rax){1to2}", "qword $0x8(%rbp,%r14,2){1to2}"]],
    "xmmrm128|b64*"    : [["xmm7", "oword [rax]", "oword [rbp+r14*2+0x8]", "qword [rax]{1to2}", "qword [rbp+r14*2+0x8]{1to2}", ""],
                          ["%xmm7", "oword (%rax)", "oword $0x8(%rbp,%r14,2)", "qword (%rax){1to2}", "qword $0x8(%rbp,%r14,2){1to2}", ""]],
    "xmmrm128|mask|z"  : [["xmm0", "xmm0{k7}", "xmm0{k7}{z}", "[rcx]", "[rcx]{k7}", "[rcx]{k7}{z}"],
                          ["%xmm0", "%xmm0{%k7}", "%xmm0{%k7}{z}", "(%rcx)", "(%rcx){%k7}", "(%rcx){%k7}{z}"]],
    "xmmrm16"          : [["xmm4", "word [rax]"],
                          ["%xmm4", "word (%rax)"]],
    "xmmrm16|b16"      : [["xmm7", "word [eax]", "word [ebp+r14*2+0x8]", "word [eax]{1to8}", "word [ebp+r14*2+0x8]{1to8}"],
                          ["%xmm7", "word (%eax)", "word $0x8(%ebp,%r14,2)", "word (%eax){1to8}", "word $0x8(%ebp,%r14,2){1to8}"]],
    "xmmrm16|er"       : [["xmm7", "word [eax]", "word [ebp+r14*2+0x8]", "xmm7,{rd-sae}"],
                          ["%xmm7", "word (%eax)", "word $0x8(%ebp,%r14,2)", "%xmm7,{rd-sae}"]],
    "xmmrm16|sae"      : [["xmm7", "word [eax]", "word [ebp+r14*2+0x8]", "xmm7,{sae}"],
                          ["%xmm7", "word (%eax)", "word $0x8(%ebp,%r14,2)", "%xmm7,{sae}"]],
    "xmmrm256|b16"     : [["xmm7", "yword [rax]", "yword [rbp+r14*2+0x8]"],
                          ["%xmm7", "word (%rax)", "word $0x8(%rbp,%r14,2)"]],
    "xmmrm32"          : [["xmm4", "dword [eax]"],
                          ["%xmm4", "dword (%eax)"]],
    "xmmrm32*"         : [["xmm5", "dword [eax]", ""],
                          ["%xmm5", "dword (%eax)", ""]],
    "xmmrm32|b16"      : [["xmm7", "dword [eax]", "word [ebp+r14*2+0x8]", "word [eax]{1to8}", "word [ebp+r14*2+0x8]{1to8}"],
                          ["%xmm7", "dword (%eax)", "word $0x8(%ebp,%r14,2)", "word (%eax){1to8}", "word $0x8(%ebp,%r14,2){1to8}"]],
    "xmmrm32|er"       : [["xmm7", "dword [eax]", "xmm7,{rd-sae}"],
                          ["%xmm7", "dword (%eax)", "%xmm7,{rd-sae}"]],
    "xmmrm32|sae"      : [["xmm7", "dword [eax]", "xmm7,{sae}"],
                          ["%xmm7", "dword (%eax)", "%xmm7,{sae}"]],
    "xmmrm64"          : [["xmm4", "qword [rax]"],
                          ["%xmm4", "qword (%rax)"]],
    "xmmrm64*"         : [["xmm5", "qword [rax]", ""],
                          ["%xmm5", "qword (%rax)", ""]],
    "xmmrm64|b16"      : [["xmm7", "qword [rax]", "qword [rbp+r14*2+0x8]", "word [rax]{1to8}", "word [rbp+r14*2+0x8]{1to8}"],
                          ["%xmm7", "qword (%rax)", "qword $0x8(%rbp,%r14,2)", "word (%rax){1to8}", "word $0x8(%rbp,%r14,2){1to8}"]],
    "xmmrm64|b32"      : [["xmm7", "qword [rax]", "qword [rbp+r14*2+0x8]", "dword [rax]{1to4}", "dword [rbp+r14*2+0x8]{1to4}"],
                          ["%xmm7", "qword (%rax)", "qword $0x8(%rbp,%r14,2)", "dword (%rax){1to4}", "dword $0x8(%rbp,%r14,2){1to4}"]],
    "xmmrm64|er"       : [["xmm7", "qword [rax]", "xmm7,{rd-sae}"],
                          ["%xmm7", "qword (%rax)", "%xmm7,{rd-sae}"]],
    "xmmrm64|sae"      : [["xmm7", "qword [rax]", "xmm7,{sae}"],
                          ["%xmm7", "qword (%rax)", "%xmm7,{sae}"]],
    "xmmrm8"           : [["xmm4", "byte [eax]"],
                          ["%xmm4", "byte (%eax)"]],
    "ymem32"           : [["dword [rbp+ymm7*2]"],
                          ["dword (%rbp,%ymm7,2)"]],
    "ymem32|mask"      : [["dword [rbp+ymm7*2]", "dword [rbp+ymm7*2]{k1}"],
                          ["dword (%rbp,%ymm7,2)", "dword (%rbp,%ymm7,2){%k1}"]],
    "ymem64"           : [["qword [rbp+ymm7*2]"],
                          ["qword (%rbp,%ymm7,2)"]],
    "ymem64|mask"      : [["qword [rbp+ymm7*2]", "qword [rbp+ymm7*2]{k1}"],
                          ["qword (%rbp,%ymm7,2)", "qword (%rbp,%ymm7,2){%k1}"]],
    "ymmreg"           : [["ymm1"],
                          ["%ymm1"]],
    "ymmreg*"          : [["ymm2", ""],
                          ["%ymm2", ""]],
    "ymmreg|mask"      : [["ymm0", "ymm0{k7}"],
                          ["%ymm0", "%ymm0{%k7}"]],
    "ymmreg|mask|z"    : [["ymm0", "ymm0{k7}", "ymm0{k7}{z}"],
                          ["%ymm0", "%ymm0{%k7}", "%ymm0{%k7}{z}"]],
    "ymmrm128"         : [["ymm15", "oword [rax+r14*8]"],
                          ["%ymm15", "oword (%rax,%r14,8)"]],
    "ymmrm128|b32"     : [["ymm15", "oword [rax]", "oword [rbp+r14*2]", "dword [rax]{1to8}", "dword [rbp+r14*2+0x8]{1to8}"],
                          ["%ymm15", "oword (%rax)", "oword (%rbp,%r14,2)", "dword [rax]{1to8}", "dword [rbp+r14*2+0x8]{1to8}"]],
    "ymmrm16|b16"      : [["ymm15", "word [eax]", "word [ebp+r14*2]", "word [rax]{1to16}", "word [rbp+r14*2+0x8]{1to16}"],
                          ["%ymm15", "word (%eax)", "word (%ebp,%r14,2)", "word (%rax){1to16}", "word $0x8(%rbp,%r14,2){1to16}"]],
    "ymmrm256"         : [["ymm15", "yword [rax+r14*8+0x10]"],
                          ["%ymm15", "yword $0x10(%rax,%r14,8)"]],
    "ymmrm256*"        : [["ymm7", "yword [rax+r14*8+0x10]", ""],
                          ["%ymm7", "yword $0x10(%rax,%r14,8)", ""]],
    "ymmrm256|b16"     : [["ymm15", "yword [rax]", "yword [rbp+r14*2+0x8]", "word [rax]{1to16}", "word [rbp+r14*2+0x8]{1to16}"],
                          ["y%m15", "yword (%rax)", "yword $0x8(%rbp,%r14,2)", "word (%rax){1to16}", "word $0x8(%rbp,%r14,2){1to16}"]],
    "ymmrm256|b16|er"  : [["ymm15", "yword [rax]", "yword [rbp+r14*2+0x8]", "ymm15,{rd-sae}"],
                          ["y%m15", "yword (%rax)", "yword $0x8(%rbp,%r14,2)", "%ymm15,{rd-sae}"]],
    "ymmrm256|b16|sae" : [["ymm15", "yword [rax]", "yword [rbp+r14*2+0x8]", "ymm15,{sae}"],
                          ["%ymm15", "yword (%rax)", "yword $0x8(%rbp,%r14,2)", "%ymm15,{sae}"]],
    "ymmrm256|b32"     : [["ymm15", "yword [rax]", "yword [rbp+r14*2+0x8]", "dword [rax]{1to8}", "dword [rbp+r14*2+0x8]{1to8}"],
                          ["%ymm15", "yword (%rax)", "yword $0x8(%rbp,%r14,2)", "dword [rax]{1to8}", "dword [rbp+r14*2+0x8]{1to8}"]],
    "ymmrm256|b32*"    : [["ymm15", "yword [rax]", "yword [rbp+r14*2+0x8]", "dword [rax]{1to8}", "dword [rbp+r14*2+0x8]{1to8}", ""],
                          ["%ymm15", "yword (%rax)", "yword $0x8(%rbp,%r14,2)", "dword [rax]{1to8}", "dword [rbp+r14*2+0x8]{1to8}", ""]],
    "ymmrm256|b32|er"  : [["ymm15", "yword [rax]", "yword [rbp+r14*2+0x8]", "ymm15,{rd-sae}"],
                          ["%ymm15", "yword (%rax)", "yword $0x8(%rbp,%r14,2)", "%ymm15,{rd-sae}"]],
    "ymmrm256|b32|sae" : [["ymm15", "yword [rax]", "yword [rbp+r14*2+0x8]", "ymm15,{sae}"],
                          ["%ymm15", "yword (%rax)", "yword $0x8(%rbp,%r14,2)", "%ymm15,{sae}"]],
    "ymmrm256|b64"     : [["ymm15", "yword [rax]", "yword [rbp+r14*2+0x8]", "qword [rax]{1to4}", "qword [rbp+r14*2+0x8]{1to4}"],
                          ["%ymm15", "yword (%rax)", "yword $0x8(%rbp,%r14,2)", "qword (%rax){1to4}", "qword $0x8(%rbp,%r14,2){1to4}"]],
    "ymmrm256|b64*"    : [["ymm15", "qword [rax]", "qword [rbp+r14*2+0x8]", "qword [rax]{1to4}", "qword [rbp+r14*2+0x8]{1to4}", ""],
                          ["%ymm15", "qword (%rax)", "qword $0x8(%rbp,%r14,2)", "qword (%rax){1to4}", "qword $0x8(%rbp,%r14,2){1to4}", ""]],
    "ymmrm256|mask|z"  : [["ymm0", "ymm0{k7}", "ymm0{k7}{z}", "[rcx]", "[rcx]{k7}", "[rcx]{k7}{z}"],
                          ["%ymm0", "%ymm0{%k7}", "%ymm0{%k7}{z}", "(%rcx)", "(%rcx){%k7}", "(%rcx){%k7}{z}"]],
    "ymmrm256|sae"     : [["ymm15", "yword [rax+r14*8+0x10]", "ymm15,{sae}"],
                          ["%ymm15", "yword $0x10(%rax,%r14,8)", "%ymm15,{sae}"]],
    "zmem32"           : [["dword [rbp+zmm7*2]"],
                          ["dword (%rbp,%zmm7,2)"]],
    "zmem32|mask"      : [["dword [rbp+zmm7*2]", "dword [rbp+zmm7*2]{k1}"],
                          ["dword (%rbp,%zmm7,2)", "dword (%rbp,%zmm7,2){%k1}"]],
    "zmem64"           : [["qword [rbp+zmm7*2]"],
                          ["qword (%rbp,%zmm7,2)"]],
    "zmem64|mask"      : [["qword [rbp+zmm7*2]", "qword [rbp+zmm7*2]{k1}"],
                          ["qword (%rbp,%zmm7,2)", "qword (%rbp,%zmm7,2){%k1}"]],
    "zmmreg"           : [["zmm3"],
                          ["%zmm3"]],
    "zmmreg*"          : [["zmm2", ""],
                          ["%zmm2", ""]],
    "zmmreg|mask"      : [["zmm0", "zmm0{k7}"],
                          ["%zmm0", "%zmm0{%k7}"]],
    "zmmreg|mask|z"    : [["zmm0", "zmm0{k7}", "zmm0{k7}{z}"],
                          ["%zmm0", "%zmm0{%k7}", "%zmm0{%k7}{z}"]],
    "zmmreg|rs4"       : [["zmm12+3"],
                          ["%zmm12+3"]],
    "zmmreg|sae"       : [["zmm15", "zmm15,{sae}"],
                          ["%zmm15", "%zmm15,{sae}"]],
    "zmmrm128|b32"     : [["zmm15", "oword [rax]", "oword [rbp+r14*2+0x8]", "dword [rax]{1to16}", "dword [rbp+r14*2+0x8]{1to16}"],
                          ["%zmm15", "oword (%rax)", "oword $0x8(%rbp,%r14,2)", "dword [rax]{1to16}", "dword [rbp+r14*2+0x8]{1to16}"]],
    "zmmrm16|b16|er"   : [["zmm15", "word [rax]", "word [rbp+r14*2+0x8]", "zmm15,{rd-sae}"],
                          ["%zmm15", "word (%rax)", "word $0x8(%rbp,%r14,2)", "%zmm15,{rd-sae}"]],
    "zmmrm16|b16|sae"  : [["zmm15", "word [rax]", "word [rbp+r14*2+0x8]", "zmm15,{sae}"],
                          ["%zmm15", "word (%rax)", "word $0x8(%rbp,%r14,2)", "%zmm15,{sae}"]],
    "zmmrm512"         : [["zmm1", "zword [rax+r14*8+0x10]"],
                          ["%zmm1", "zword $0x10(%rax,%r14,8)"]],
    "zmmrm512*"        : [["zmm2", "zword [rax+r14*8+0x10]", ""],
                          ["%zmm2", "zword $0x10(%rax,%r14,8)", ""]],
    "zmmrm512|b16"     : [["zmm15", "zword [rax]", "zword [rbp+r14*2+0x8]", "word [rax]{1to32}", "word [rbp+r14*2+0x8]{1to32}"],
                          ["%zmm15", "zword (%rax)", "zword $0x8(%rbp,%r14,2)", "word (%rax){1to32}", "word $0x8(%rbp,%r14,2){1to32}"]],
    "zmmrm512|b16|er"  : [["zmm15", "zword [rax]", "zword [rbp+r14*2+0x8]", "zmm15,{rd-sae}"],
                          ["%zmm15", "zword (%rax)", "zword $0x8(%rbp,%r14,2)", "%zmm15,{rd-sae}"]],
    "zmmrm512|b16|sae" : [["zmm15", "zword [rax]", "zword [rbp+r14*2+0x8]", "zmm15,{sae}"],
                          ["%zmm15", "zword (%rax)", "zword $0x8(%rbp,%r14,2)", "%zmm15,{sae}"]],
    "zmmrm512|b32"     : [["zmm15", "zword [rax]", "zword [rbp+r14*2+0x8]", "dword [rax]{1to16}", "dword [rbp+r14*2+0x8]{1to16}"],
                          ["%zmm15", "zword (%rax)", "zword $0x8(%rbp,%r14,2)", "dword [rax]{1to16}", "dword [rbp+r14*2+0x8]{1to16}"]],
    "zmmrm512|b32*"    : [["zmm15", "zword [rax]", "zword [rbp+r14*2+0x8]", "dword [rax]{1to16}", "dword [rbp+r14*2+0x8]{1to16}", ""],
                          ["%zmm15", "zword (%rax)", "zword $0x8(%rbp,%r14,2)", "dword [rax]{1to16}", "dword [rbp+r14*2+0x8]{1to16}", ""]],
    "zmmrm512|b32|er"  : [["zmm15", "zword [rax]", "zword [rbp+r14*2+0x8]", "zmm15,{rd-sae}"],
                          ["%zmm15", "zword (%rax)", "zword $0x8(%rbp,%r14,2)", "%zmm15,{rd-sae}"]],
    "zmmrm512|b32|sae" : [["zmm15", "zword [rax]", "zword [rbp+r14*2+0x8]", "zmm15,{sae}"],
                          ["%zmm15", "zword (%rax)", "zword $0x8(%rbp,%r14,2)", "%zmm15,{sae}"]],
    "zmmrm512|b64"     : [["zmm15", "zword [rax]", "zword [rbp+r14*2+0x8]", "qword [rax]{1to8}", "qword [rbp+r14*2+0x8]{1to8}"],
                          ["%zmm15", "zword (%rax)", "zword $0x8(%rbp,%r14,2)", "qword (%rax){1to8}", "qword $0x8(%rbp,%r14,2){1to8}"]],
    "zmmrm512|b64*"    : [["zmm15", "zword [rax]", "zword [rbp+r14*2+0x8]", "qword [rax]{1to8}", "qword [rbp+r14*2+0x8]{1to8}", ""],
                          ["%zmm15", "zword (%rax)", "zword $0x8(%rbp,%r14,2)", "qword (%rax){1to8}", "qword $0x8(%rbp,%r14,2){1to8}", ""]],
    "zmmrm512|b64|er"  : [["zmm15", "zword [rax]", "zword [rbp+r14*2+0x8]", "zmm15,{rd-sae}"],
                          ["%zmm15", "zword (%rax)", "zword $0x8(%rbp,%r14,2)", "%zmm15,{rd-sae}"]],
    "zmmrm512|b64|sae" : [["zmm15", "zword [rax]", "zword [rbp+r14*2+0x8]", "zmm15,{sae}"],
                          ["%zmm1", "zword (%rax)", "zword $0x8(%rbp,%r14,2)", "%zmm1,{sae}"]],
    "zmmrm512|mask|z"  : [["zmm0", "zmm0{k7}", "zmm0{k7}{z}", "zword [rcx]", "zword [rcx]{k7}", "zword [rcx]{k7}{z}"],
                          ["%zmm0", "%zmm0{%k7}", "%zmm0{%k7}{z}", "zword (%rcx)", "zword (%rcx){%k7}", "zword (%rcx){%k7}{z}"]]
}

blacklist_non_64bit_opcodes = [
    "AAA",
    "AAD",
    "AAM",
    "AAS",
    "ARPL",
    "BNDCL",
    "BNDCN",
    "BNDCU",
    "BNDLDX",
    "BNDSTX",
    "BOUND",
    "CALL",
    "CLZERO",
    "CMPXCHG486",
    "DAA",
    "DAS",
    "DMINT",
    "IBTS",
    "INTO",
    "INVLPGA",
    "JCXZ",
    "LDS",
    "LES",
    "LOOP",
    "LOOPE",
    "LOOPEW",
    "LOOPNE",
    "LOOPNEW",
    "LOOPNZ",
    "LOOPNZW",
    "LOOPW",
    "LOOPZ",
    "LOOPZW",
    "MONITOR",
    "MONITORW",
    "MONITORX",
    "POP",
    "POPA",
    "POPAD",
    "POPAW",
    "PUSH",
    "PUSHA",
    "PUSHAD",
    "PUSHAW",
    "RDM",
    "RDSHR",
    "RSDC",
    "RSLDT",
    "RSTS",
    "SALC",
    "SMINT",
    "SMINTOLD",
    "SVDC",
    "SVLDT",
    "SVTS",
    "UMONITOR",
    "UMOV",
    "VMREAD",
    "VMWRITE",
    "WRSHR",
    "XBTS"
]

blacklist_non_intel_opcodes = [
    "BB0_RESET",
    "BB1_RESET",
    "BLCFILL",
    "BLCI",
    "BLCIC",
    "BLCMSK",
    "BLCS",
    "BLSFILL",
    "BLSIC",
    "CLGI",
    "CLZERO",
    "CPU_READ",
    "CPU_WRITE",
    "DMINT",
    "EXTRQ",
    "INSERTQ",
    "INVLPGA",
    "LLWPCB",
    "LWPINS",
    "LWPVAL",
    "MONITORX",
    "MONTMUL",
    "MOVNTSD",
    "MOVNTSS",
    "MWAITX",
    "PADDSIW",
    "PAVEB",
    "PDISTIB",
    "PFRCPV",
    "PFRSQRTV",
    "PMACHRIW",
    "PMAGW",
    "PMULHRIW",
    "PMULHRWC",
    "PMVGEZB",
    "PMVLZB",
    "PMVNZB",
    "PMVZB",
    "PSUBSIW",
    "PVALIDATE",
    "RDM",
    "RDSHR",
    "RMPADJUST",
    "RSDC",
    "RSLDT",
    "RSTS",
    "SLWPCB",
    "SMINT",
    "SMINTOLD",
    "STGI",
    "SVDC",
    "SVLDT",
    "SVTS",
    "T1MSKC",
    "TZMSK",
    "VFMADDPD",
    "VFMADDPS",
    "VFMADDSD",
    "VFMADDSS",
    "VFMADDSUBPD",
    "VFMADDSUBPS",
    "VFMSUBADDPD",
    "VFMSUBADDPS",
    "VFMSUBPD",
    "VFMSUBPS",
    "VFMSUBSD",
    "VFMSUBSS",
    "VFNMADDPD",
    "VFNMADDPS",
    "VFNMADDSD",
    "VFNMADDSS",
    "VFNMSUBPD",
    "VFNMSUBPS",
    "VFNMSUBSD",
    "VFNMSUBSS",
    "VFRCZPD",
    "VFRCZPS",
    "VFRCZSD",
    "VFRCZSS",
    "VMGEXIT",
    "VMLOAD",
    "VMMCALL",
    "VMRUN",
    "VMSAVE",
    "VPCMOV",
    "VPCOMB",
    "VPCOMD",
    "VPCOMQ",
    "VPCOMUB",
    "VPCOMUD",
    "VPCOMUQ",
    "VPCOMUW",
    "VPCOMW",
    "VPHADDBD",
    "VPHADDBQ",
    "VPHADDBW",
    "VPHADDDQ",
    "VPHADDUBD",
    "VPHADDUBQ",
    "VPHADDUBW",
    "VPHADDUDQ",
    "VPHADDUWD",
    "VPHADDUWQ",
    "VPHADDWD",
    "VPHADDWQ",
    "VPHSUBBW",
    "VPHSUBDQ",
    "VPHSUBWD",
    "VPMACSDD",
    "VPMACSDQH",
    "VPMACSDQL",
    "VPMACSSDD",
    "VPMACSSDQH",
    "VPMACSSDQL",
    "VPMACSSWD",
    "VPMACSSWW",
    "VPMACSWD",
    "VPMACSWW",
    "VPMADCSSWD",
    "VPMADCSWD",
    "VPPERM",
    "VPROTB",
    "VPROTD",
    "VPROTQ",
    "VPROTW",
    "VPSHAB",
    "VPSHAD",
    "VPSHAQ",
    "VPSHAW",
    "VPSHLB",
    "VPSHLQ",
    "VPSHLW",
    "WRSHR",
    "XCRYPTCBC",
    "XCRYPTCFB",
    "XCRYPTCTR",
    "XCRYPTECB",
    "XCRYPTOFB",
    "XSHA1",
    "XSHA256",
    "XSTORE"
]

opcode_translation_table = {
    "CCMPscc"   : ["CCMPB", "CCMPBE", "CCMPBE", "CCMPF", "CCMPL", "CCMPLE", "CCMPNB", "CCMPNBE",
                    "CCMPNL", "CCMPNLE", "CCMPNO", "CCMPNS", "CCMPNZ", "CCMPO", "CCMPS", "CCMPT", "CCMPZ"],
    "CFCMOVcc"  : ["CFCMOVB", "CFCMOVBE", "CFCMOVL", "CFCMOVLE", "CFCMOVNB", "CFCMOVNBE",
                    "CFCMOVNL", "CFCMOVNLE", "CFCMOVNO", "CFCMOVNP", "CFCMOVNS", "CFCMOVNZ",
                    "CFCMOVO", "CFCMOVP", "CFCMOVS", "CFCMOVZ"],
    "CMOVcc"    : ["CMOVA", "CMOVAE", "CMOVB", "CMOVBE", "CMOVC", "CMOVE", "CMOVG", "CMOVGE",
                    "CMOVL", "CMOVLE", "CMOVNA", "CMOVNAE", "CMOVNB", "CMOVNBE", "CMOVNC",
                    "CMOVNE", "CMOVNG", "CMOVNGE", "CMOVNL", "CMOVNLE", "CMOVNO", "CMOVNP",
                    "CMOVNS", "CMOVNZ", "CMOVO", "CMOVP", "CMOVPE", "CMOVPO", "CMOVS", "CMOVZ"],
    "CMPccXADD" : ["CMPBEXADD", "CMPBXADD", "CMPLEXADD", "CMPLXADD", "CMPNBEXADD", "CMPNBXADD",
                    "CMPNLEXADD", "CMPNLXADD", "CMPNOXADD", "CMPNPXADD", "CMPNSXADD", "CMPNZXADD",
                    "CMPOXADD", "CMPPXADD", "CMPSXADD", "CMPZXADD"],
    "CTESTscc"  : ["CTESTB", "CTESTBE", "CTESTF", "CTESTL", "CTESTLE", "CTESTNB", "CTESTNBE",
                    "CTESTNL", "CTESTNLE", "CTESTNO", "CTESTNS", "CTESTNZ", "CTESTO", "CTESTS",
                    "CTESTT", "CTESTZ"],
    "Jcc"       : ["JA", "JAE", "JB", "JBE", "JC", "JCXZ", "JECXZ", "JE", "JG", "JGE", "JL", "JLE",
                    "JNA", "JNAE", "JNB", "JNBE", "JNC", "JNE", "JNG", "JNGE", "JNL", "JNLE",
                    "JNO", "JNP", "JNS", "JNZ", "JO", "JP", "JPE", "JPO", "JS", "JZ", "JA", "JAE",
                    "JB", "JBE", "JC", "JE", "JZ", "JG", "JGE", "JL", "JLE", "JNA", "JNAE", "JNB",
                    "JNBE", "JNC", "JNE", "JNG", "JNGE", "JNL", "JNLE", "JNO", "JNP", "JNS", "JNZ",
                    "JO", "JP", "JPE", "JPO", "JS", "JZ"],
    "SETcc"     : ["SETA", "SETAE", "SETB", "SETBE", "SETC", "SETE", "SETG", "SETGE", "SETL",
                    "SETLE", "SETNA", "SETNAE", "SETNB", "SETNBE", "SETNC", "SETNE", "SETNG",
                    "SETNGE", "SETNL", "SETNLE", "SETNO", "SETNP", "SETNS", "SETNZ", "SETO",
                    "SETP", "SETPE", "SETPO", "SETS", "SETZ"],
    "SETccZU"   : ["SETB", "SETBE", "SETL", "SETLE", "SETNB", "SETNBE", "SETNL", "SETNLE", "SETNO",
                    "SETNP", "SETNS", "SETNZ", "SETO", "SETP", "SETS", "SETZ"]
}

prefix_by_opcode_table = {
    "SETccZU"   : "{zu} "
}

def SplitOperands(operandStr):
    # Split by comma
    parts = re.split(r',', operandStr)
    return [part.strip() for part in parts]

def ExtractUniqueColumn(filename, column=0):
    column_set = set()
    with open(filename, 'r') as f:
        for line in f:
            line = line.split(';', 1)[0]  # Remove comments
            if not line.strip():          # Skip empty lines
                continue
            column_set.add(line.split()[column])
    return list(column_set)

def GetOpcodeList(xdaFile):
    return ExtractUniqueColumn(xdaFile, 0)

def GetOperandList(xdaFile):
    return ExtractUniqueColumn(xdaFile, 1)

def RemoveBlacklistedOpcodes(opcodeList):
    filtered_opcodes = []
    for opcode in opcodeList:
        if opcode in blacklist_non_64bit_opcodes:
            print(f"Skipping non-64bit opcode '{opcode}'")
            continue
        if opcode in blacklist_non_intel_opcodes:
            print(f"Skipping non-Intel opcode '{opcode}'")
            continue
        filtered_opcodes.append(opcode)
    return filtered_opcodes

def GetOpcodeAndPrefix(line: str, opcode: str):
    opcodesEx = [opcode]
    prefix = ""

    if line.find("evex.scc") != -1:
        prefix = ""
    elif line.find("evex.") != -1:
        prefix = "{evex} "
    elif line.find("vex.") != -1 or line.find("vex+.") != -1:
        prefix = "{vex} "

    if opcode in opcode_translation_table:
        opcodesEx = opcode_translation_table[opcode]
    if opcode in prefix_by_opcode_table:
        prefix += prefix_by_opcode_table[opcode]

    return opcodesEx, prefix

def PopulateOperandMapping(operandList: list, pos: int, temp: list, outputOperands: list, dir: int):
    for operand in operandList[pos]:
        temp[pos] = operand
        #print(f"Position {pos}, Operand: {operand}, Temp: {temp}")
        if pos + dir >= len(operandList) or pos + dir < 0: # Last position
            #print(f"Adding combination to output: {temp}")
            outputOperands.append(temp.copy())
        else:
            PopulateOperandMapping(operandList, pos + dir, temp, outputOperands, dir)
            
    return outputOperands

def GenerateNasmInstructions(opcodes, xdaFile):
    nasm_instructions = []
    for opcode in opcodes:
        all_instruction_combinations = []
        with open(xdaFile, 'r') as f:
            for line in f:
                line = line.split(';', 1)[0]
                if not line.strip():
                    continue
                if line.split()[0] == opcode:
                    opcodesEx, prefix = GetOpcodeAndPrefix(line, opcode)
                    operandStr = line.split()[1]
                    operands = SplitOperands(operandStr)
                    nasm_operands = []
                    for operand in operands:
                        if operand in operand_to_nasm_gas_mapping and operand_to_nasm_gas_mapping[operand][NASM]:
                            nasm_operands.append(operand_to_nasm_gas_mapping[operand][NASM])
                        else:
                            print(f"Warning: No NASM mapping for operand '{operand}' in opcode '{opcode}'")
                            break
                    if len(operands) != len(nasm_operands):
                        print(f"Skipping line '{line}' due to missing operand mappings")
                        continue
                    temp = [None] * len(nasm_operands)
                    all_operand_combinations = PopulateOperandMapping(nasm_operands, 0, temp, [], 1)
                    for opcodeEx in opcodesEx:
                        for nasm_operand_combination in all_operand_combinations:
                            nasm_operand_combination.remove("") if "" in nasm_operand_combination else None
                            suffix = ""
                            # remove the first element if the first element includes string '{dfv=...}' and put it as a suffix to opcode
                            operands_list = nasm_operand_combination.copy()
                            if operands_list and '{dfv=' in operands_list[0]:
                                suffix = operands_list[0]
                                operands_list.pop(0)
                            nasm_instruction = f"{prefix}{opcodeEx} {suffix} " + ", ".join(operands_list)
                            all_instruction_combinations.append(nasm_instruction)
        #print (opcode, all_instruction_combinations)
        nasm_instructions.append({opcode: all_instruction_combinations})
    return nasm_instructions

def GenerateGasInstructions(opcodes, xdaFile):
    gas_instructions = []
    for opcode in opcodes:
        all_instruction_combinations = []
        with open(xdaFile, 'r') as f:
            for line in f:
                line = line.split(';', 1)[0]
                if not line.strip():
                    continue
                if line.split()[0] == opcode:
                    opcodesEx, prefix = GetOpcodeAndPrefix(line, opcode)
                    operandStr = line.split()[1]
                    operands = SplitOperands(operandStr)
                    gas_operands = []
                    for operand in operands:
                        if operand in operand_to_nasm_gas_mapping and operand_to_nasm_gas_mapping[operand][GAS]:
                            gas_operands.insert(0, operand_to_nasm_gas_mapping[operand][GAS])
                        else:
                            print(f"Warning: No GAS mapping for operand '{operand}' in opcode '{opcode}'")
                            break
                    if len(operands) != len(gas_operands):
                        print(f"Skipping line '{line}' due to missing operand mappings")
                        continue
                    temp = [None] * len(gas_operands)
                    all_operand_combinations = PopulateOperandMapping(gas_operands, len(gas_operands) - 1, temp, [], -1)
                    for opcodeEx in opcodesEx:
                        for gas_operand_combination in all_operand_combinations:
                            gas_operand_combination.remove("") if "" in gas_operand_combination else None
                            suffix = ""
                            # remove the last element if the last element includes string '{dfv=...}' and put it as a suffix to opcode
                            operands_list = gas_operand_combination.copy()
                            if operands_list and '{dfv=' in operands_list[-1]:
                                suffix = operands_list[-1]
                                operands_list.pop(-1)
                            gas_instruction = f"{prefix}{opcodeEx} {suffix} " + ", ".join(operands_list)
                            all_instruction_combinations.append(gas_instruction)
        gas_instructions.append({opcode: all_instruction_combinations})
    return gas_instructions

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--xdafile", "-i", type=str, default="../x86/insns.xda", help="The instruction database from nasm")
    args = parser.parse_args()

    opcodes = GetOpcodeList(args.xdafile)
    opcodes = RemoveBlacklistedOpcodes(opcodes)
    #opcodes = ["AADD"] # For testing
    operands = GetOperandList(args.xdafile)

    print(f"Found {len(opcodes)} opcodes and {len(operands)} operands in {args.xdafile}")
    #print("Opcodes:")
    #for opcode in opcodes:
    #    print(f'    "{opcode}",')
    #print("Operands:")
    #for op in operands:
    #    print(f'    "{op}",')

    nasm_instructions = GenerateNasmInstructions(opcodes, args.xdafile)
    #json_str = json.dumps(nasm_instructions, indent=2)
    #print(f"Generated NASM instructions:\n{json_str}\n")
    for instruction in nasm_instructions:
        for opcode, insns in instruction.items():
            print (f"Generating NASM test file for opcode '{opcode}' with {len(insns)} instructions\n")
            for i in range(len(insns)):
                target_path = os.path.join(os.getcwd(), "target_src", "nasm", f"test_{opcode}_{i}_nasm.asm")
                with open(target_path, 'w') as f:
                    f.write(NASM_HEADER % (opcode, opcode))
                    f.write(f"        {insns[i]}\n")
                    f.write(NASM_FOOTER)

    gas_instructions = GenerateGasInstructions(opcodes, args.xdafile)
    #json_str = json.dumps(gas_instructions, indent=2)
    #print(f"Generated GAS instructions:\n{json_str}\n")
    for instruction in gas_instructions:
        for opcode, insns in instruction.items():
            print (f"Generating GAS test file for opcode '{opcode}' with {len(insns)} instructions\n")
            for i in range(len(insns)):
                target_path = os.path.join(os.getcwd(), "target_src", "gas", f"test_{opcode}_{i}_gas.s")
                with open(target_path, 'w') as f:
                    f.write(GAS_HEADER % (opcode, opcode))
                    f.write(f"        {insns[i]}\n")
                    f.write(GAS_FOOTER)
