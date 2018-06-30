#include <iostream>

#ifndef HEADER
#define HEADER

#pragma GCC warning "Compiled header2.h..."

int f()
{
    return 2;
}

template <typename T>
void g(T t)
{
    std::cout << &t << " " << t + 1 << std::endl;
}

template <>
void g(std::string t)
{
    std::cout << &t << " " << t << std::endl;
}

#else
#pragma GCC warning "Skip compilation of header2.h"
#endif // HEADER