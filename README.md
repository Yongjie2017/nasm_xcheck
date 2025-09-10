# NASM Cross Check

This project is for cross checking the functionality of NASM (netwide assembler) development based on a different source.
For example, using GCC/GAS or even another stable NASM version to check the cutting edge NASM development.

## Prerequisite
1. Put this project in the root folder of a NASM source code.
2. Build the NASM source code so that x86/insns.xda and nasm are available.
3. Install nasm package to get the official 2.16.03 (you can use newer version if you know what you are doing).
4. Please instal binutils. GNU assembler (gas) and objdump as part of binutils are needed.

## How to use it

### Step 1. Generate test case
```
make tc_gen
```

### Step 2. Build test case
```
make tc_build
```

### Step 3. Use test case to cross check among different assemblers
```
make tc_check
```
