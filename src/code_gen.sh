#!/bin/bash
#
for x in $(cat insns.list)
do
	echo Test code generating for instruction $x

	rm -f apx/apx-${x}.asm
	echo "bits 64" > apx/apx-${x}.asm
	echo -e "global avx10_2_${x}\n" >> apx/apx-${x}.asm
	echo "avx10_2_${x}:" >> apx/apx-${x}.asm
	echo -e "\tpush rbp\n\tmov rbp,rsp" >> apx/apx-${x}.asm

	rm -f apx/apx-${x}.c
	echo -e "void avx10_2_$x(void)\n{\n" > apx/apx-${x}.c

	grep "$x " insns.dat | while read -r line
	do
		for y in $(cat insns.translate.table | awk -F "=" '{ print $1 }' | sort -u)
		do
			if echo $line | grep " ${y} "; then
				grep "^${y} " insns.translate.table | while read -r trans_line
				do
					a=$(echo $trans_line | awk -F "=" '{ print $2 }' | sed s/instruction/${x}/)
					echo -e "\t$a" >> apx/apx-${x}.asm
					c=$(echo $trans_line | awk -F "=" '{ print $3 }' | sed s/instruction/${x}/)
					echo -e "\tasm volatile(\"${c}\");" >> apx/apx-${x}.c
				done
			fi
		done
	done

	echo -e "}\n" >> apx/apx-${x}.c
	echo -e "\tnop\n\tpop rbp\n\tret" >> apx/apx-${x}.asm
done
