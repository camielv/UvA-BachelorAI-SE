#!/bin/bash
# Unzip all .tgz files for each year
for year in `ls -1`
do
    cd $year
    for file in `ls -1 *.tgz`
    do
        echo $year, $file
        tar zxf $file
    done
    cd ..
done

