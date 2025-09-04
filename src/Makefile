SRC ?= avx10.2/avx10.2-xxx
ASM  = $(SRC).asm
CSRC = $(SRC).c

all:
	../nasm.apx.wip/nasm -f elf64 $(ASM) -o $(ASM).o
	gcc $(CSRC) -c -o $(CSRC).o

dump:
	objdump -d $(ASM).o
	objdump -d $(CSRC).o

dump_check:
	@objdump -d $(ASM).o | tail -n +4 > /tmp/asm.dump
	@objdump -d $(CSRC).o | tail -n +4 > /tmp/c.dump
	@if ! diff /tmp/c.dump /tmp/asm.dump; then objdump -d $(ASM).o; objdump -d $(CSRC).o; fi

clean:
	find -type f -name "*.o" | xargs rm -f
