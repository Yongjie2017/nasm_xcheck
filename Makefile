
all: code_gen code_build instruction_validation testcase_gen

code_gen:
	for x in src/*.xda; do src/code_gen.sh $x; done

code_build:
	for x in src/*.xda; do src/build_all.sh $x; done

instruction_validation:
	for x in src/*.xda; do src/build_all.sh $x dump_check; done

testcase_gen:
	src/testcase_gen.sh

clean:
	find -type f -name "*.o" | xargs rm -f

