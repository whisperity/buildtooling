#!/bin/bash

echo "#define MODULE_EXPORT" > module.cppm
echo "" >> module.cppm
echo "export module FULL_NAME_???;" >> module.cppm

echo -e "\n/* Header files */\n" >> module.cppm

echo * \
  | tr ' ' '\n' \
  | grep -E "\.(h|hpp)$" \
  | sed -s 's/^/#include "/g' \
  | sed -s 's/$/"/g' >> module.cppm

echo -e "\n/* Source files */\n" >> module.cppm

echo * \
  | tr ' ' '\n' \
  | grep -E "\.(c|cpp)$" \
  | sed -s 's/^/#include "/g' \
  | sed -s 's/$/"/g' >> module.cppm
