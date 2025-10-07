
all: nasm gas

.Phony: nasm gas

# target nasm depends on tc_gen_nasm, tc_build_nasm, and tc_check_nasm
nasm: tc_gen_nasm tc_build_nasm tc_check_nasm

# target gas depends on tc_gen_gas, tc_build_gas, and tc_check_gas
gas: tc_gen_gas tc_build_gas tc_check_gas

tc_gen_nasm: ../x86/insns.xda src/tc_gen.py
	rm -rf target_src/nasm
	mkdir -p target_src/nasm
	python3 src/tc_gen.py --target nasm | tee gen_nasm.log

tc_gen_gas: ../x86/insns.xda src/tc_gen.py
	rm -rf target_src/gas
	mkdir -p target_src/gas
	python3 src/tc_gen.py --target gas | tee gen_gas.log

tc_build_nasm: target_src/nasm
	mkdir -p output/nasm.ref output/nasm.cur
	cp Makefile.nasm output/nasm.ref/Makefile
	cp Makefile.nasm output/nasm.cur/Makefile
	make -j -C output/nasm.ref NASM=nasm 2>&1 | tee build_nasm_ref.log
	make -j -C output/nasm.cur NASM="../../../nasm" 2>&1 | tee build_nasm_cur1.log

tc_build_gas: target_src/gas
	mkdir -p output/gas output/nasm.cur
	cp Makefile.nasm output/nasm.ref/Makefile
	cp Makefile.gas output/gas/Makefile
	make -j -C output/nasm.cur NASM="../../../nasm" 2>&1 | tee build_nasm_cur2.log
	make -j -C output/gas GAS="as" 2>&1 | tee build_gas.log

tc_check_nasm: output/nasm.ref output/nasm.cur
	bash src/tc_check.sh nasm | tee check_nasm.log

tc_check_gas: output/nasm.cur output/gas
	bash src/tc_check.sh gas | tee check_gas.log

travis_gen:
	bash src/travis_gen.sh | tee gen_travis.log

clean:
	rm -rf gen*.log build*.log check*.log gen_travis.log
	rm -rf target_src/nasm target_src/gas
	rm -rf output/nasm.ref output/nasm.cur output/gas

