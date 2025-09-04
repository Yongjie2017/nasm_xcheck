#!/bin/bash

for x in $(cat insns.list)
do
	echo $x; make SRC=apx/apx-$x $1
done
