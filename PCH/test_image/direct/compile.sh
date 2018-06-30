#!/usr/bin/env bash

echo "/---> Compiling implementation file for f() in header WITHOUT PCH!"
# This is to test that the header is actually compiled, seek the warning on stderr.
clang++ -include header.h -c implementation.cpp -o /dev/null

echo "/---> Creating precompiled header file from header.h ..."
clang++ -xc++-header header.h -o header.h.pch

echo "/---> Creating precompiled header file from header2.h ..."
clang++ -xc++-header header2.h -o header2.h.pch

echo "/---> Compiling implementation file for f() in header."
# This won't compile header.h as the PCH exists.
clang++ -include header.h -c implementation.cpp

echo "/---> Compiling implementation file with header2."
echo "      This should fail - double definition"
# The PCH created from header2 already contains a definition for f().
clang++ -include header2.h -c implementation.cpp -o implementation2.o

echo "/---> Compiling main source with header..."
clang++ -include header.h -c source.cpp

echo "/---> Compiling main source file with header2."
clang++ -include header2.h -c source.cpp -o source2.o

echo "/---> Linking executables... with header content."
clang++ implementation.o source.o -o source

echo "/---> Linking executables with source made via header2..."
echo "      This should fail because f() is double definition."
clang++ implementation.o source2.o -o source2

echo "/---> Creating binary for source2 object with PCH generated implementation"
clang++ source2.o -o source2b

echo "\---> Compiling chained PCH..."
clang++ -include header.h -xc++-header chain.h -o chain.h.pch
clang++ -include chain.h -c chain.cpp -o chain.o
clang++ chain.o -o chain.out
