# NASM Cross Check

This project is for cross checking the functionality of NASM (netwide assembler) development based on a different source.
For example, using GCC/GAS or even another stable NASM version to check the cutting edge NASM development.

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
