#!/bin/bash
#

TC_NAME=$1

TC_FILE=${TC_NAME}.asm
rm -f ${TC_FILE}
echo ";Testname=${TC_NAME}; Arguments=-fbin -o${TC_NAME}.bin -O0 -DSRC; Files=stdout stderr ${TC_NAME}.bin" > ${TC_FILE}
echo "" >> ${TC_FILE}
echo -e "%macro testcase 2\n\
 %ifdef BIN\n\
  db %1\n\
 %endif\n\
 %ifdef SRC\n\
  %2\n\
 %endif\n\
%endmacro" >> ${TC_FILE}

echo -e "\n\nbits 64\n" >> ${TC_FILE}

for x in $(cat insns.list)
do
	echo Test case generating for instruction $x

	pushd output/nasm.3.00.rc3
	tests=$(ls test_${x}_*_nasm.asm.o | sed 's/\.o//')
	popd
	for t in $tests
	do
		t_gas=$(echo $t | sed 's/nasm\.asm/gas.s/')
		if [ -f output/gas/${t_gas}.o ]; then
			a=$(grep " $x" target_src/nasm/$t)
			echo -e "\tbits 64\n\t${a}" > /tmp/tmp.asm
			../nasm -f BIN -o /tmp/tmp.bin /tmp/tmp.asm
			b=$(xxd -i /tmp/tmp.bin | grep "^ ")
			printf "testcase        {%-76s}, {%-76s }\n" "$b" "$a" >> ${TC_FILE}
		fi
	done
done
