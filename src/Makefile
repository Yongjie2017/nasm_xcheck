
all: tc_gen

tc_gen: insns.xda src/tc_gen.py
	rm -rf target_src/*
	mkdir -p target_src/nasm target_src/gas
	python3 src/tc_gen.py

tc_build: target_src/nasm target_src/gas
	mkdir -p output/nasm.2.16.03 output/nasm.3.00.rc3 output/gas
	bash src/tc_build.sh

tc_check: output/nasm.2.16.03 output/nasm.3.00.rc3 output/gas
	bash src/tc_check.sh

clean:
	rm -rf target_src/nasm target_src/gas
	rm -rf output/nasm.2.16.03 output/nasm.3.00.rc3 output/gas

