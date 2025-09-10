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
    "mem"              : [["[rax+r14*8+0x10]"],
                          ["$0x10(%rax,%r14,8)"]],
    "mem128"           : [["oword [rax+r14*8]"],
                          ["oword (%rax,%r14,8)"]],
    "mem128|mask"      : [["oword [rax+r14*8]{k1}"],
                          ["oword (%rax,%r14,8){%k1}"]],
    "mem16"            : [["word [eax]"],
                          ["word (%eax)"]],
    "mem16|far"        : [["word [eax]", "far word [eax]"],
                          ["word (%eax)", "far word (%eax)"]],
    "mem16|mask"       : [["word [eax]{k1}"],
                          ["word (%eax){%k1}"]],
    "mem256"           : [["yword [rax+r14*8]"],
                          ["yword (%rax,%r14,8)"]],
    "mem256|mask"      : [["yword [rax+r14*8]{k1}"],
                          ["yword (%rax,%r14,8){%k1}"]],
    "mem32"            : [["dword [eax+ecx*8+0x10]"],
                          ["dword $0x10(%eax,%ecx,8)"]],
    "mem32|far"        : [["far dword [eax]"],
                          ["far dword (%eax)"]],
    "mem32|mask"       : [["far dword [eax]{k1}"],
                          ["far dword (%eax){%k1}"]],
    "mem512"           : [["zword [rax+r14*8+0x10]"],
                          ["zword $0x10(%rax,%r14,8)"]],
    "mem512|mask"      : [["zword [rax+r14*8+0x10]{k1}"],
                          ["zword $0x10(%rax,%r14,8){%k1}"]],
    "mem64"            : [["qword [rax+rcx*8+0x10]"],
                          ["qword $0x10(%rax,%rcx,8)"]],
    "mem64|far"        : [["far qword [rax]"],
                          ["far qword (%rax)"]],
    "mem64|mask"       : [["qword [rax+rcx*8+0x10]{k1}"],
                          ["qword $0x10(%rax,%rcx,8){%k1}"]],
    "mem8"             : [["byte [eax+ecx*8+0x10]"],
                          ["byte $0x10(%eax,%ecx,8)"]],
    "mem80"            : [[ "[0x1000]"],
                          ["[$0x1000]"]],
    "mem_offs"         : [["[near1]"],
                          ["[near1]"]],
    "mmxreg"           : [["mm0"],
                          ["%mm0"]],
    "mmxrm"            : [["mm0", "dword [eax]"],
                          ["%mm0", "dword (%eax)"]],
    "mmxrm64"          : [["mm0", "qword [rax]"],
                          ["%mm0", "qword (%rax)"]],
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
    "reg_creg"         : [["cx"],
                          ["%cx"]],
    "reg_cs"           : [["cs"],
                          ["%cs"]],
    "reg_cx"           : [["cx"],
                          ["%cx"]],
    "reg_dreg"         : [["dx"],
                          ["%dx"]],
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
    "reg_sreg"         : [["ss"],
                          ["%ss"]],
    "reg_ss"           : [["ss"],
                          ["%ss"]],
    "reg_treg"         : [["tx"],
                          ["%tx"]],
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
    "rm32|er"          : [["eax,{rd-sae}", "dword [eax],{rd-sae}"],
                          ["%eax,{rd-sae}", "dword (%eax),{rd-sae}"]],
    "rm32|near"        : [["eax", "dword near1"],
                          ["%eax", "dword near1"]],
    "rm64"             : [["rax", "qword [rax]"],
                          ["%rax", "qword (%rax)"]],
    "rm64*"            : [["rax", "qword [rax]", ""],
                          ["%rax", "qword (%rax)", ""]],
    "rm64|er"          : [["rax,{rd-sae}", "qword [rax],{rd-sae}"],
                          ["%rax,{rd-sae}", "qword (%rax),{rd-sae}"]],
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
    "spec4"            : [["[rax+r14*8+0x10]", "[rax]"],
                          ["0x10(%rax,%r14,8)", "(%rax)"]],
    "tmmreg"           : [["tmm0"],
                          ["%tmm0"]],
    "udword64"         : [["qword [rax]"],
                          ["qword (%rax)"]],
    "unity"            : [["0x10"],
                          ["$0x10"]],
    "void"             : [[""],
                          [""]],
    "xmem32"           : [["dword [ebp+xmm7*2+0x8]"],
                          ["dword 0x8(%ebp,%xmm7,2)"]],
    "xmem32|mask"      : [["dword [ebp+xmm7*2+0x8]", "dword [ebp+xmm7*2]{k1}"],
                          ["dword 0x8(%ebp,%xmm7,2)", "dword (%ebp,%xmm7,2){%k1}"]],
    "xmem64"           : [["qword [ebp+xmm7*2+0x8]"],
                          ["qword 0x8(%ebp,%xmm7,2)"]],
    "xmem64|mask"      : [["qword [ebp+xmm7*2+0x8]", "qword [ebp+xmm7*2]{k1}"],
                          ["qword 0x8(%ebp,%xmm7,2)", "qword (%ebp,%xmm7,2){%k1}"]],
    "xmm0"             : [["xmm0"],
                          ["%xmm0"]],
    "xmmreg"           : [["xmm1"],
                          ["%xmm1"]],
    "xmmreg*"          : [["xmm1", ""],
                          ["%xmm1", ""]],
    "xmmreg|er"        : [["xmm1,{rd-sae}"],
                          ["%xmm1,{rd-sae}"]],
    "xmmreg|mask"      : [["xmm1", "xmm1{k7}"],
                          ["%xmm1", "%xmm1{%k7}"]],
    "xmmreg|mask|z"    : [["xmm1", "xmm1{k7}", "xmm1{k7}{z}"],
                          ["%xmm1", "%xmm1{%k7}", "%xmm1{%k7}{z}"]],
    "xmmrm"            : [["xmm1", "oword [rax+r14*8]"],
                          ["%xmm1", "oword (%rax,%r14,8)"]],
    "xmmrm128"         : [["xmm1", "oword [rax+r14*8]"],
                          ["%xmm1", "oword (%rax,%r14,8)"]],
    "xmmrm128*"        : [["xmm1", "oword [rax+r14*8]", ""],
                          ["%xmm1", "oword (%rax,%r14,8)", ""]],
    "xmmrm128|b16"     : [["xmm1", "word [eax]", "word [ebp+xmm7*2+0x8]"],
                          ["%xmm1", "word (%eax)", "word 0x8(%ebp,%xmm7,2)"]],
    "xmmrm128|b16|er"  : [["xmm1", "word [eax]", "word [ebp+xmm7*2+0x8]", "xmm1,{rd-sae}", "word [eax],{rd-sae}", "word [ebp+xmm7*2+0x8],{rd-sae}"],
                          ["%xmm1", "word (%eax)", "word 0x8(%ebp,%xmm7,2)", "%xmm1,{rd-sae}", "word (%eax),{rd-sae}", "word 0x8(%ebp,%xmm7,2),{rd-sae}"]],
    "xmmrm128|b16|sae" : [["xmm1", "word [eax]", "word [ebp+xmm7*2+0x8]", "xmm1,{sae}", "word [eax],{sae}", "word [ebp+xmm7*2+0x8],{sae}"],
                          ["%xmm1", "word (%eax)", "word 0x8(%ebp,%xmm7,2)", "%xmm1,{sae}", "word (%eax),{sae}", "word 0x8(%ebp,%xmm7,2),{sae}"]],
    "xmmrm128|b32"     : [["xmm1", "dword [eax]", "dword [ebp+xmm7*2+0x8]"],
                          ["%xmm1", "dword (%eax)", "dword 0x8(%ebp,%xmm7,2)"]],
    "xmmrm128|b32*"    : [["xmm1", "dword [eax]", "dword [ebp+xmm7*2+0x8]", ""],
                          ["%xmm1", "dword (%eax)", "dword 0x8(%ebp,%xmm7,2)", ""]],
    "xmmrm128|b64"     : [["xmm1", "qword [eax]", "qword [rbp+xmm7*2+0x8]"],
                          ["%xmm1", "qword (%eax)", "qword 0x8(%rbp,%xmm7,2)"]],
    "xmmrm128|b64*"    : [["xmm1", "qword [eax]", "qword [rbp+xmm7*2+0x8]", ""],
                          ["%xmm1", "qword (%eax)", "qword 0x8(%rbp,%xmm7,2)", ""]],
    "xmmrm128|mask|z"  : [["xmm1", "xmm1{k7}", "xmm1{k7}{z}", "[rcx]", "[rcx]{k7}", "[rcx]{k7}{z}"],
                          ["%xmm1", "%xmm1{%k7}", "%xmm1{%k7}{z}", "(%rcx)", "(%rcx){%k7}", "(%rcx){%k7}{z}"]],
    "xmmrm16"          : [["xmm1", "word [eax]"],
                          ["%xmm1", "word (%eax)"]],
    "xmmrm16|b16"      : [["xmm1", "word [eax]", "word [ebp+xmm7*2+0x8]"],
                          ["%xmm1", "word (%eax)", "word 0x8(%ebp,%xmm7,2)"]],
    "xmmrm16|er"       : [["xmm1", "word [eax]", "word [ebp+xmm7*2+0x8]", "xmm1,{rd-sae}", "word [eax],{rd-sae}", "word [ebp+xmm7*2+0x8],{rd-sae}"],
                          ["%xmm1", "word (%eax)", "word 0x8(%ebp,%xmm7,2)", "%xmm1,{rd-sae}", "word (%eax),{rd-sae}", "word 0x8(%ebp,%xmm7,2),{rd-sae}"]],
    "xmmrm16|sae"      : [["xmm1", "word [eax]", "word [ebp+xmm7*2+0x8]", "xmm1,{sae}", "word [eax],{sae}", "word [ebp+xmm7*2+0x8],{sae}"],
                          ["%xmm1", "word (%eax)", "word 0x8(%ebp,%xmm7,2)", "%xmm1,{sae}", "word (%eax),{sae}", "word 0x8(%ebp,%xmm7,2),{sae}"]],
    "xmmrm256|b16"     : [["xmm1", "word [rax]", "word [rbp+xmm7*2+0x8]"],
                          ["%xmm1", "word (%rax)", "word 0x8(%rbp,%xmm7,2)"]],
    "xmmrm32"          : [["xmm1", "dword [eax]"],
                          ["%xmm1", "dword (%eax)"]],
    "xmmrm32*"         : [["xmm1", "dword [eax]", ""],
                          ["%xmm1", "dword (%eax)", ""]],
    "xmmrm32|b16"      : [["xmm1", "dword [eax]", "word [ebp+xmm7*2+0x8]"],
                          ["%xmm1", "dword (%eax)", "word 0x8(%ebp,%xmm7,2)"]],
    "xmmrm32|er"       : [["xmm1", "dword [eax]", "xmm1,{rd-sae}", "dword [eax],{rd-sae}"],
                          ["%xmm1", "dword (%eax)", "%xmm1,{rd-sae}", "dword (%eax),{rd-sae}"]],
    "xmmrm32|sae"      : [["xmm1", "dword [eax]", "xmm1,{sae}", "dword [eax],{sae}"],
                          ["%xmm1", "dword (%eax)", "%xmm1,{sae}", "dword (%eax),{sae}"]],
    "xmmrm64"          : [["xmm1", "qword [rax]"],
                          ["%xmm1", "qword (%rax)"]],
    "xmmrm64*"         : [["xmm1", "qword [rax]", ""],
                          ["%xmm1", "qword (%rax)", ""]],
    "xmmrm64|b16"      : [["xmm1", "qword [rax]", "word [rbp+xmm7*2+0x8]"],
                          ["%xmm1", "qword (%rax)", "word 0x8(%rbp,%xmm7,2)"]],
    "xmmrm64|b32"      : [["xmm1", "qword [rax]", "dword [rbp+xmm7*2+0x8]"],
                          ["%xmm1", "qword (%rax)", "dword 0x8(%rbp,%xmm7,2)"]],
    "xmmrm64|er"       : [["xmm1", "qword [rax]", "xmm1,{rd-sae}", "qword [rax],{rd-sae}"],
                          ["%xmm1", "qword (%rax)", "%xmm1,{rd-sae}", "qword (%rax),{rd-sae}"]],
    "xmmrm64|sae"      : [["xmm1", "qword [rax]", "xmm1,{sae}", "qword [rax],{sae}"],
                          ["%xmm1", "qword (%rax)", "%xmm1,{sae}", "qword (%rax),{sae}"]],
    "xmmrm8"           : [["xmm1", "byte [eax]"],
                          ["%xmm1", "byte (%eax)"]],
    "ymem32"           : [["dword [ebp+ymm7*2]"],
                          ["dword (%ebp,%ymm7,2)"]],
    "ymem32|mask"      : [["dword [ebp+ymm7*2]", "dword [ebp+ymm7*2]{k1}"],
                          ["dword (%ebp,%ymm7,2)", "dword (%ebp,%ymm7,2){%k1}"]],
    "ymem64"           : [["qword [rbp+ymm7*2]"],
                          ["qword (%rbp,%ymm7,2)"]],
    "ymem64|mask"      : [["qword [rbp+ymm7*2]", "qword [rbp+ymm7*2]{k1}"],
                          ["qword (%rbp,%ymm7,2)", "qword (%rbp,%ymm7,2){%k1}"]],
    "ymmreg"           : [["ymm1"],
                          ["%ymm1"]],
    "ymmreg*"          : [["ymm1", ""],
                          ["%ymm1", ""]],
    "ymmreg|mask"      : [["ymm1", "ymm1{k7}"],
                          ["%ymm1", "%ymm1{%k7}"]],
    "ymmreg|mask|z"    : [["ymm1", "ymm1{k7}", "ymm1{k7}{z}"],
                          ["%ymm1", "%ymm1{%k7}", "%ymm1{%k7}{z}"]],
    "ymmrm128"         : [["ymm1", "oword [rax+r14*8]"],
                          ["%ymm1", "oword (%rax,%r14,8)"]],
    "ymmrm128|b32"     : [["ymm1", "dword [eax]", "dword [ebp+ymm7*2]"],
                          ["%ymm1", "dword (%eax)", "dword (%ebp,%ymm7,2)"]],
    "ymmrm16|b16"      : [["ymm1", "word [eax]", "word [ebp+ymm7*2]"],
                          ["%ymm1", "word (%eax)", "word (%ebp,%ymm7,2)"]],
    "ymmrm256"         : [["ymm1", "yword [rax+r14*8+0x10]"],
                          ["%ymm1", "yword $0x10(%rax,%r14,8)"]],
    "ymmrm256*"        : [["ymm1", "yword [rax+r14*8+0x10]", ""],
                          ["%ymm1", "yword $0x10(%rax,%r14,8)", ""]],
    "ymmrm256|b16"     : [["ymm1", "word [eax]", "word [ebp+ymm7*2+0x8]"],
                          ["y%m1", "word (%eax)", "word 0x8(%ebp,%ymm7,2)"]],
    "ymmrm256|b16|er"  : [["ymm1", "word [eax]", "word [ebp+ymm7*2+0x8]", "ymm1{rd-sae}", "word [eax],{rd-sae}", "word [ebp+ymm7*2+0x8],{rd-sae}"],
                          ["y%m1", "word (%eax)", "word 0x8(%ebp,%ymm7,2)", "%ymm1{rd-sae}", "word (%eax),{rd-sae}", "word 0x8(%ebp,%ymm7,2),{rd-sae}"]],
    "ymmrm256|b16|sae" : [["ymm1", "word [eax]", "word [ebp+ymm7*2+0x8]", "ymm1{sae}", "word [eax],{sae}", "word [ebp+ymm7*2+0x8],{sae}"],
                          ["%ymm1", "word (%eax)", "word 0x8(%ebp,%ymm7,2)", "%ymm1{sae}", "word (%eax),{sae}", "word 0x8(%ebp,%ymm7,2),{sae}"]],
    "ymmrm256|b32"     : [["ymm1", "dword [eax]", "dword [ebp+ymm7*2+0x8]"],
                          ["%ymm1", "dword (%eax)", "dword 0x8(%ebp,%ymm7,2)"]],
    "ymmrm256|b32*"    : [["ymm1", "dword [eax]", "dword [ebp+ymm7*2+0x8]", ""],
                          ["%ymm1", "dword (%eax)", "dword 0x8(%ebp,%ymm7,2)", ""]],
    "ymmrm256|b32|er"  : [["ymm1", "dword [eax]", "dword [ebp+ymm7*2+0x8]", "ymm1,{rd-sae}", "dword [eax],{rd-sae}", "dword [ebp+ymm7*2+0x8],{rd-sae}"],
                          ["%ymm1", "dword (%eax)", "dword 0x8(%ebp,%ymm7,2)", "%ymm1,{rd-sae}", "dword (%eax),{rd-sae}", "dword 0x8(%ebp,%ymm7,2),{rd-sae}"]],
    "ymmrm256|b32|sae" : [["ymm1", "dword [eax]", "dword [ebp+ymm7*2+0x8]", "ymm1,{sae}", "dword [eax],{sae}", "dword [ebp+ymm7*2+0x8],{sae}"],
                          ["%ymm1", "dword (%eax)", "dword 0x8(%ebp,%ymm7,2)", "%ymm1,{sae}", "dword (%eax),{sae}", "dword 0x8(%ebp,%ymm7,2),{sae}"]],
    "ymmrm256|b64"     : [["ymm1", "qword [rax]", "qword [rbp+ymm7*2+0x8]"],
                          ["%ymm1", "qword (%rax)", "qword 0x8(%rbp,%ymm7,2)"]],
    "ymmrm256|b64*"    : [["ymm1", "qword [rax]", "qword [rbp+ymm7*2+0x8]", ""],
                          ["%ymm1", "qword (%rax)", "qword 0x8(%rbp,%ymm7,2)", ""]],
    "ymmrm256|mask|z"  : [["ymm1", "ymm1{k7}", "ymm1{k7}{z}", "[rcx]", "[rcx]{k7}", "[rcx]{k7}{z}"],
                          ["%ymm1", "%ymm1{%k7}", "%ymm1{%k7}{z}", "(%rcx)", "(%rcx){%k7}", "(%rcx){%k7}{z}"]],
    "ymmrm256|sae"     : [["ymm1", "yword [rax+r14*8+0x10]", "ymm1,{sae}", "yword [rax+r14*8+0x10],{sae}"],
                          ["%ymm1", "yword $0x10(%rax,%r14,8)", "%ymm1,{sae}", "yword $0x10(%rax,%r14,8),{sae}"]],
    "zmem32"           : [["dword [ebp+zmm7*2]"],
                          ["dword (%ebp,%zmm7,2)"]],
    "zmem32|mask"      : [["dword [ebp+zmm7*2]", "dword [ebp+zmm7*2]{k1}"],
                          ["dword (%ebp,%zmm7,2)", "dword (%ebp,%zmm7,2){%k1}"]],
    "zmem64"           : [["qword [rbp+zmm7*2]"],
                          ["qword (%rbp,%zmm7,2)"]],
    "zmem64|mask"      : [["qword [rbp+zmm7*2]", "qword [rbp+zmm7*2]{k1}"],
                          ["qword (%rbp,%zmm7,2)", "qword (%rbp,%zmm7,2){%k1}"]],
    "zmmreg"           : [["zmm0"],
                          ["%zmm0"]],
    "zmmreg*"          : [["zmm0", ""],
                          ["%zmm0", ""]],
    "zmmreg|mask"      : [["zmm0", "zmm0{k7}"],
                          ["%zmm0", "%zmm0{%k7}"]],
    "zmmreg|mask|z"    : [["zmm0", "zmm0{k7}", "zmm0{k7}{z}"],
                          ["%zmm0", "%zmm0{%k7}", "%zmm0{%k7}{z}"]],
    "zmmreg|rs4"       : [["zmm0+3"],
                          ["%zmm0+3"]],
    "zmmreg|sae"       : [["zmm1", "zmm1,{sae}"],
                          ["%zmm1", "%zmm1,{sae}"]],
    "zmmrm128|b32"     : [["zmm1", "oword [rax]", "dword [ebp+zmm7*2+0x8]"],
                          ["%zmm1", "oword (%rax)", "dword 0x8(%ebp,%zmm7,2)"]],
    "zmmrm16|b16|er"   : [["zmm1", "word [eax]", "word [ebp+zmm7*2+0x8]", "zmm1,{rd-sae}", "word [eax],{rd-sae}", "word [ebp+zmm7*2+0x8],{rd-sae}"],
                          ["%zmm1", "word (%eax)", "word 0x8(%ebp,%zmm7,2)", "%zmm1,{rd-sae}", "word (%eax),{rd-sae}", "word 0x8(%ebp,%zmm7,2),{rd-sae}"]],
    "zmmrm16|b16|sae"  : [["zmm1", "word [eax]", "word [ebp+zmm7*2+0x8]", "zmm1,{sae}", "word [eax],{sae}", "word [ebp+zmm7*2+0x8],{sae}"],
                          ["%zmm1", "word (%eax)", "word 0x8(%ebp,%zmm7,2)", "%zmm1,{sae}", "word (%eax),{sae}", "word 0x8(%ebp,%zmm7,2),{sae}"]],
    "zmmrm512"         : [["zmm1", "zword [rax+r14*8+0x10]"],
                          ["%zmm1", "zword $0x10(%rax,%r14,8)"]],
    "zmmrm512*"        : [["zmm1", "zword [rax+r14*8+0x10]", ""],
                          ["%zmm1", "zword $0x10(%rax,%r14,8)", ""]],
    "zmmrm512|b16"     : [["zmm1", "zword [rax]", "word [rbp+zmm7*2+0x8]"],
                          ["%zmm1", "zword (%rax)", "word 0x8(%rbp,%zmm7,2)"]],
    "zmmrm512|b16|er"  : [["zmm1", "zword [rax]", "word [ebp+zmm7*2+0x8]", "zmm1,{rd-sae}", "zword [rax],{rd-sae}", "word [ebp+zmm7*2+0x8],{rd-sae}"],
                          ["%zmm1", "zword (%rax)", "word 0x8(%ebp,%zmm7,2)", "%zmm1,{rd-sae}", "zword (%rax),{rd-sae}", "word 0x8(%ebp,%zmm7,2),{rd-sae}"]],
    "zmmrm512|b16|sae" : [["zmm1", "zword [rax]", "word [ebp+zmm7*2+0x8]", "zmm1,{sae}", "zword [rax],{sae}", "word [ebp+zmm7*2+0x8],{sae}"],
                          ["%zmm1", "zword (%rax)", "word 0x8(%ebp,%zmm7,2)", "%zmm1,{sae}", "zword (%rax),{sae}", "word 0x8(%ebp,%zmm7,2),{sae}"]],
    "zmmrm512|b32"     : [["zmm1", "zword [rax]", "dword [ebp+zmm7*2+0x8]"],
                          ["%zmm1", "zword (%rax)", "dword 0x8(%ebp,%zmm7,2)"]],
    "zmmrm512|b32*"    : [["zmm1", "zword [rax]", "dword [ebp+zmm7*2+0x8]", ""],
                          ["%zmm1", "zword (%rax)", "dword 0x8(%ebp,%zmm7,2)", ""]],
    "zmmrm512|b32|er"  : [["zmm1", "zword [rax]", "dword [ebp+zmm7*2+0x8]", "zmm1,{rd-sae}", "zword [rax],{rd-sae}", "dword [ebp+zmm7*2+0x8],{rd-sae}"],
                          ["%zmm1", "zword (%rax)", "dword 0x8(%ebp,%zmm7,2)", "%zmm1,{rd-sae}", "zword (%rax),{rd-sae}", "dword 0x8(%ebp,%zmm7,2),{rd-sae}"]],
    "zmmrm512|b32|sae" : [["zmm1", "zword [rax]", "dword [ebp+zmm7*2+0x8]", "zmm1,{sae}", "zword [rax],{sae}", "dword [ebp+zmm7*2+0x8],{sae}"],
                          ["%zmm1", "zword (%rax)", "dword 0x8(%ebp,%zmm7,2)", "%zmm1,{sae}", "zword (%rax),{sae}", "dword 0x8(%ebp,%zmm7,2),{sae}"]],
    "zmmrm512|b64"     : [["zmm1", "zword [rax]", "qword [rbp+zmm7*2+0x8]"],
                          ["%zmm1", "zword (%rax)", "qword 0x8(%rbp,%zmm7,2)"]],
    "zmmrm512|b64*"    : [["zmm1", "zword [rax]", "qword [rbp+zmm7*2+0x8]", ""],
                          ["%zmm1", "zword (%rax)", "qword 0x8(%rbp,%zmm7,2)", ""]],
    "zmmrm512|b64|er"  : [["zmm1", "zword [rax]", "qword [ebp+zmm7*2+0x8]", "zmm1,{rd-sae}", "zword [rax],{rd-sae}", "qword [ebp+zmm7*2+0x8],{rd-sae}"],
                          ["%zmm1", "zword (%rax)", "qword 0x8(%ebp,%zmm7,2)", "%zmm1,{rd-sae}", "zword (%rax),{rd-sae}", "qword 0x8(%ebp,%zmm7,2),{rd-sae}"]],
    "zmmrm512|b64|sae" : [["zmm1", "zword [rax]", "qword [ebp+zmm7*2+0x8]", "zmm1,{sae}", "zword [rax],{sae}", "qword [ebp+zmm7*2+0x8],{sae}"],
                          ["%zmm1", "zword (%rax)", "qword 0x8(%ebp,%zmm7,2)", "%zmm1,{sae}", "zword (%rax),{sae}", "qword 0x8(%ebp,%zmm7,2),{sae}"]],
    "zmmrm512|mask|z"  : [["zmm1", "zmm1{k7}", "zmm1{k7}{z}", "[rcx]", "[rcx]{k7}", "[rcx]{k7}{z}"],
                          ["%zmm1", "%zmm1{%k7}", "%zmm1{%k7}{z}", "(%rcx)", "(%rcx){%k7}", "(%rcx){%k7}{z}"]]
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
    "INVEPT",
    "INVLPGA",
    "INVPCID",
    "INVVPID",
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
    "BEXTR",
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
    "LFENCE",
    "LLWPCB",
    "LWPINS",
    "LWPVAL",
    "MFENCE",
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
    "SFENCE",
    "SLWPCB",
    "SMINT",
    "SMINTOLD",
    "STGI",
    "SVDC",
    "SVLDT",
    "SVTS",
    "SYSCALL",
    "SYSRET",
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
    "VPSHLD",
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

def GetPrefix(line: str):
    if line.find("evex.") != -1:
        return "{evex} "
    if line.find("vex.") != -1 or line.find("vex+.") != -1:
        return "{vex} "
    return ""

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
                    prefix = GetPrefix(line)
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
                    for nasm_operand_combination in all_operand_combinations:
                        nasm_operand_combination.remove("") if "" in nasm_operand_combination else None
                        nasm_instruction = f"{prefix}{opcode} " + ", ".join(nasm_operand_combination)
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
                    prefix = GetPrefix(line)
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
                    for gas_operand_combination in all_operand_combinations:
                        gas_operand_combination.remove("") if "" in gas_operand_combination else None
                        gas_instruction = f"{prefix}{opcode} " + ", ".join(gas_operand_combination)
                        all_instruction_combinations.append(gas_instruction)
        gas_instructions.append({opcode: all_instruction_combinations})
    return gas_instructions

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--xdafile", "-i", type=str, default="insns.xda", help="The instruction database from nasm")
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
