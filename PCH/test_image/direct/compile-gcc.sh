#!/usr/bin/env bash

echo "/---> Compiling implementation file for f() in header WITHOUT gch!"
# This is to test that the header is actually compiled, seek the warning on stderr.
g++ -include header.h -c implementation.cpp -o /dev/null

echo "/---> Creating precompiled header file from header.h ..."
g++ -xc++-header header.h -o header.h.gch

echo "/---> Creating precompiled header file from header2.h ..."
g++ -xc++-header header2.h -o header2.h.gch

echo "/---> Compiling implementation file for f() in header."
# This won't compile header.h as the gch exists.
g++ -include header.h -c implementation.cpp

echo "/---> Compiling implementation file with header2."
echo "      This should fail - double definition"
# The gch created from header2 already contains a definition for f().
g++ -include header2.h -c implementation.cpp -o implementation2.o

echo "/---> Compiling main source with header..."
g++ -include header.h -c source.cpp

echo "/---> Compiling main source file with header2."
g++ -include header2.h -c source.cpp -o source2.o

echo "/---> Linking executables... with header content."
g++ implementation.o source.o -o source

echo "/---> Linking executables with source made via header2..."
echo "      This should fail because f() is double definition."
g++ implementation.o source2.o -o source2

echo "/---> Creating binary for source2 object with gch generated implementation"
g++ source2.o -o source2b

echo "\---> Compiling chained gch..."
g++ -include header.h -xc++-header chain.h -o chain.h.gch
g++ -include chain.h -c chain.cpp -o chain.o
g++ chain.o -o chain.out
