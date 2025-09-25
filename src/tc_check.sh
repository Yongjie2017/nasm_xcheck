#!/bin/bash

cur_dir=${PWD}

src_nasm=target_src/nasm
src_gas=target_src/gas

output_2_16_03=${cur_dir}/output/nasm.2.16.03
output_3_00_rc3=${cur_dir}/output/nasm.3.00.rc3

output_gas=${cur_dir}/output/gas

# prepare the instruction list
pushd $src_nasm
nasm_insns=$(ls | sed 's/^test_//' | sed 's/_nasm\.asm//' | sort -u -V)
popd

# compare output between nasm 2.16.03 and 3.00.rc3
echo "Comparing output between nasm 2.16.03 and 3.00.rc3"
for insn in $nasm_insns
do
	if [ -f ${output_3_00_rc3}/test_${insn}_nasm.asm.o -a -f ${output_2_16_03}/test_${insn}_nasm.asm.o ]; then
		echo -n "$insn ... "
		objdump -d ${output_2_16_03}/test_${insn}_nasm.asm.o | tail -n +4 > /tmp/2_16_03.dump
		objdump -d ${output_3_00_rc3}/test_${insn}_nasm.asm.o | tail -n +4 > /tmp/3_00_rc3.dump

		# applying a work around on prefix group3/4 order, if doesn't match
		if ! diff /tmp/2_16_03.dump /tmp/3_00_rc3.dump >/dev/null; then
			sed -i 's/:\t67 66 /:\t66 67 /' /tmp/3_00_rc3.dump
		fi

		if ! diff /tmp/2_16_03.dump /tmp/3_00_rc3.dump >/dev/null; then
			echo ""
			diff /tmp/2_16_03.dump /tmp/3_00_rc3.dump
			cat $src_nasm/test_${insn}_nasm.asm
		else
			echo "Done"
		fi
	fi
done

# compare output between nasm 3.00.rc3 and gas
echo "Comparing output between nasm gas and 3.00.rc3"
for insn in $nasm_insns
do
	if [ -f ${output_3_00_rc3}/test_${insn}_nasm.asm.o -a -f ${output_gas}/test_${insn}_gas.s.o ]; then
		echo -n "$insn ... "
		objdump -d --no-show-raw-insn --no-addresses ${output_gas}/test_${insn}_gas.s.o | tail -n +4 > /tmp/gas.dump
		objdump -d --no-show-raw-insn --no-addresses ${output_3_00_rc3}/test_${insn}_nasm.asm.o | tail -n +4 > /tmp/3_00_rc3.dump

		# applying a work around on offset
		sed -i -e 's/0x0(%eax/(%eax/' -e 's/0x0(%ax/(%ax/' -e 's/0x0(%rax/(%rax/' /tmp/gas.dump
		
		if ! diff /tmp/gas.dump /tmp/3_00_rc3.dump >/dev/null; then
			echo ""
			diff /tmp/gas.dump /tmp/3_00_rc3.dump 
			cat $src_nasm/test_${insn}_nasm.asm
			cat $src_gas/test_${insn}_gas.s
		else
			echo "Done"
		fi
	fi
done
