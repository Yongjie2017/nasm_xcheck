#!/bin/bash

cur_dir=${PWD}

nasm_2_16_03=nasm
nasm_3_00_rc3=../nasm

gas=as

src_nasm=target_src/nasm
src_gas=target_src/gas

output_2_16_03=${cur_dir}/output/nasm.2.16.03
output_3_00_rc3=${cur_dir}/output/nasm.3.00.rc3

output_gas=${cur_dir}/output/gas

# build nasm source with 2.16.03 and the 3.00.rc3

# prepare the instruction list
pushd $src_nasm
nasm_insns=$(ls | sed 's/^test_//' | sed 's/_nasm\.asm//' | sort -u)
popd

# build with 2.16.03
rm -rf $output_2_16_03
mkdir -p $output_2_16_03

echo "Compiling by nasm 2.16.03 ..." | tee /dev/stderr
for nasm_insn in $nasm_insns
do
	${nasm_2_16_03} -f elf64 -o ${output_2_16_03}/test_${nasm_insn}_nasm.asm.o $src_nasm/test_${nasm_insn}_nasm.asm
done

# build with 3.00.rc3
rm -rf $output_3_00_rc3
mkdir -p $output_3_00_rc3

echo "Compiling by nasm 3.00.rc3 ..." | tee /dev/stderr
for nasm_insn in $nasm_insns
do
	${nasm_3_00_rc3} -f elf64 -o ${output_3_00_rc3}/test_${nasm_insn}_nasm.asm.o $src_nasm/test_${nasm_insn}_nasm.asm
done

# build gas source

# prepare the instruction list
pushd $src_gas
gas_insns=$(ls | sed 's/^test_//' | sed 's/_gas\.s//' | sort -u)
popd

# build with gas
rm -rf $output_gas
mkdir -p $output_gas

echo "Compiling by gas ..." >&2
for gas_insn in $gas_insns
do
	${gas} -o ${output_gas}/test_${gas_insn}_gas.s.o $src_gas/test_${gas_insn}_gas.s
done
