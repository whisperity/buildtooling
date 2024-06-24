#!/bin/bash

echo "#define MODULE_EXPORT" > module.cppm
echo "" >> module.cppm
echo "export module FULL_NAME_$1;" >> module.cppm

echo -e "\n/* Header files */\n" >> module.cppm

find . -type f \
  | tr ' ' '\n' \
  | grep -E "\.(h|hpp|hxx|hh)$" \
  | sed -s 's/^/#include "/g' \
  | sed -s 's/$/"/g' >> module.cppm

echo -e "\n/* Source files */\n" >> module.cppm

find . -type f \
  | tr ' ' '\n' \
  | grep -E "\.(c|cpp|cxx|cc|i|ipp|ixx|ii)$" \
  | sed -s 's/^/#include "/g' \
  | sed -s 's/$/"/g' >> module.cppm
