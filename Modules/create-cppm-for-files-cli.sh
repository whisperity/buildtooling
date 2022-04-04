#!/bin/bash

MODULE_NAME=$1
MODULE_FILE=$2

shift 2

echo "#define MODULE_EXPORT" > $MODULE_FILE.cppm
echo "" >> $MODULE_FILE.cppm
echo "export module FULL_NAME_$MODULE_NAME;" >> $MODULE_FILE.cppm

echo -e "\n/* Header files */\n" >> $MODULE_FILE.cppm

echo $@ \
  | tr ' ' '\n' \
  | grep -E "\.(h|hpp|hxx|hh)$" \
  | sed -s 's/^/#include "/g' \
  | sed -s 's/$/"/g' >> $MODULE_FILE.cppm

echo -e "\n/* Source files */\n" >> $MODULE_FILE.cppm

echo $@ \
  | tr ' ' '\n' \
  | grep -E "\.(c|cpp|cxx|cc|i|ipp|ixx|ii)$" \
  | sed -s 's/^/#include "/g' \
  | sed -s 's/$/"/g' >> $MODULE_FILE.cppm
