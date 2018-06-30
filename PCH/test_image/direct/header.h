#include <iostream>

#ifndef HEADER
#define HEADER

#pragma GCC warning "Compiled header.h..."

int f();

template <typename T>
void g(T t)
{
    std::cout << &t << std::endl;
}

#else
#pragma GCC warning "Skip compilation of header.h"
#endif // HEADER