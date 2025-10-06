#!/bin/bash

cur_dir=${PWD}
build_nasm=1
build_gas=1

if [ "$1" == "nasm" ]; then
	build_gas=0
elif [ "$1" == "gas" ]; then
	build_nasm=0
else
	echo "Usage: $0 <nasm|gas>" >&2
	exit 1
fi

nasm_ref=nasm
nasm_cur=../nasm

gas=as

src_nasm=target_src/nasm
src_gas=target_src/gas

output_ref=${cur_dir}/output/nasm.ref
output_cur=${cur_dir}/output/nasm.cur

output_gas=${cur_dir}/output/gas

# build nasm source with ref and the cur

# prepare the instruction list
pushd $src_nasm
nasm_insns=$(ls | sed 's/^test_//' | sed 's/_nasm\.asm//' | sort -u -V)
popd

if [ "$build_nasm" -eq "1" ]; then
	# build with ref
	rm -rf $output_ref
	mkdir -p $output_ref

	echo "Compiling by nasm ref ..." | tee /dev/stderr
	for nasm_insn in $nasm_insns
	do
		${nasm_ref} -f elf64 -o ${output_ref}/test_${nasm_insn}_nasm.asm.o $src_nasm/test_${nasm_insn}_nasm.asm
	done
fi

# always build current nasm
rm -rf $output_cur
mkdir -p $output_cur

echo "Compiling by nasm cur ..." | tee /dev/stderr
for nasm_insn in $nasm_insns
do
	${nasm_cur} -f elf64 -o ${output_cur}/test_${nasm_insn}_nasm.asm.o $src_nasm/test_${nasm_insn}_nasm.asm
done

# build gas source

# prepare the instruction list
pushd $src_gas
gas_insns=$(ls | sed 's/^test_//' | sed 's/_gas\.s//' | sort -u -V)
popd

if [ "$build_gas" -eq "1" ]; then
	# build with gas
	rm -rf $output_gas
	mkdir -p $output_gas

	echo "Compiling by gas ..." >&2
	for gas_insn in $gas_insns
	do
		${gas} -o ${output_gas}/test_${gas_insn}_gas.s.o $src_gas/test_${gas_insn}_gas.s
	done
fi
