
# build by reference nasm compiler

SRCS_DIR    := ../../target_src/nasm

SRCS_NASM   := $(wildcard $(SRCS_DIR)/*.asm)
OBJS_NASM   := $(subst ../../target_src/nasm/,,$(subst .asm,.o,$(SRCS_NASM)))

NASM ?= "nasm"

%.o: $(SRCS_DIR)/%.asm
	-$(NASM) -f elf64 $< -o $@

all: $(OBJS_NASM)
	
