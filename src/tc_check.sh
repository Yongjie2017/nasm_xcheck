#!/bin/bash

cur_dir=${PWD}
check_nasm=1
check_gas=1

if [ "$1" == "nasm" ]; then
	check_gas=0
elif [ "$1" == "gas" ]; then
	check_nasm=0
else
	echo "Usage: $0 <nasm|gas>" >&2
	exit 1
fi

src_nasm=target_src/nasm
src_gas=target_src/gas

output_ref=${cur_dir}/output/nasm.ref
output_cur=${cur_dir}/output/nasm.cur

output_gas=${cur_dir}/output/gas

# prepare the instruction list
pushd $src_nasm
nasm_insns=$(ls | sed 's/^test_//' | sed 's/_nasm\.asm//' | sort -u -V)
popd

if [ "$check_nasm" -eq "1" ]; then
	# compare output between nasm ref and cur
	echo "Comparing output between nasm ref and cur"
	for insn in $nasm_insns
	do
		if [ -f ${output_cur}/test_${insn}_nasm.asm.o -a -f ${output_ref}/test_${insn}_nasm.asm.o ]; then
			echo -n "$insn ... "
			objdump -d ${output_ref}/test_${insn}_nasm.asm.o | tail -n +4 > /tmp/ref.dump
			objdump -d ${output_cur}/test_${insn}_nasm.asm.o | tail -n +4 > /tmp/cur.dump

			# applying a work around on prefix group3/4 order, if doesn't match
			if ! diff /tmp/ref.dump /tmp/cur.dump >/dev/null; then
				sed -i 's/:\t67 66 /:\t66 67 /' /tmp/cur.dump
			fi

			if ! diff /tmp/ref.dump /tmp/cur.dump >/dev/null; then
				echo ""
				diff /tmp/ref.dump /tmp/cur.dump
				cat $src_nasm/test_${insn}_nasm.asm
			else
				echo "Done"
			fi
		fi
	done
fi

if [ "$check_gas" -eq "1" ]; then
	# compare output between nasm cur and gas
	echo "Comparing output between nasm gas and cur"
	for insn in $nasm_insns
	do
		if [ -f ${output_cur}/test_${insn}_nasm.asm.o -a -f ${output_gas}/test_${insn}_gas.s.o ]; then
			echo -n "$insn ... "
			objdump -d --no-show-raw-insn --no-addresses ${output_gas}/test_${insn}_gas.s.o | tail -n +4 > /tmp/gas.dump
			objdump -d --no-show-raw-insn --no-addresses ${output_cur}/test_${insn}_nasm.asm.o | tail -n +4 > /tmp/cur.dump

			# applying a work around on offset
			sed -i -e 's/0x0(%eax/(%eax/' -e 's/0x0(%ax/(%ax/' -e 's/0x0(%rax/(%rax/' /tmp/gas.dump
			
			if ! diff /tmp/gas.dump /tmp/cur.dump >/dev/null; then
				echo ""
				diff /tmp/gas.dump /tmp/cur.dump 
				cat $src_nasm/test_${insn}_nasm.asm
				cat $src_gas/test_${insn}_gas.s
			else
				echo "Done"
			fi
		fi
	done
fi
