#!/bin/bash
#

TC_FILE=apx/apx.asm
rm -f ${TC_FILE}
echo ";Testname=apx; Arguments=-fbin -oapx.bin -O0 -DSRC; Files=stdout stderr apx.bin" > ${TC_FILE}
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

	grep "$x " insns.dat | while read -r line
	do
		for y in $(cat insns.translate.table | awk -F "=" '{ print $1 }' | sort -u)
		do
			if echo $line | grep " ${y} " >/dev/null; then
				grep "^${y} " insns.translate.table | while read -r trans_line
				do
					a=$(echo $trans_line | awk -F "=" '{ print $2 }' | sed s/instruction/${x}/)
					echo -e "\tbits 64\n\t$a" > /tmp/tmp.asm
					../nasm.apx.wip/nasm -f BIN -o /tmp/tmp.bin /tmp/tmp.asm
					b=$(xxd -i /tmp/tmp.bin | grep "^ ")
					printf "testcase        {%-76s}, { %s }\n" "$b" "$a" >> ${TC_FILE}
				done
			fi
		done
	done
done
