
all: tc_gen

tc_gen: ../x86/insns.xda src/tc_gen.py
	rm -rf target_src/*
	mkdir -p target_src/nasm target_src/gas
	python3 src/tc_gen.py | tee gen.log

tc_build: target_src/nasm target_src/gas
	mkdir -p output/nasm.2.16.03 output/nasm.3.00.rc3 output/gas
	bash src/tc_build.sh 2>&1 | tee build.log

tc_check: output/nasm.2.16.03 output/nasm.3.00.rc3 output/gas
	bash src/tc_check.sh | tee check.log

travis_gen:
	bash src/travis_gen.sh | tee gen_travis.log
clean:
	rm gen.log gen_travis.log build.log check.log
	rm -rf target_src/nasm target_src/gas
	rm -rf output/nasm.2.16.03 output/nasm.3.00.rc3 output/gas

