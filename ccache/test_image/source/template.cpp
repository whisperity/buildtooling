#include <iostream>
#include "factorial.h"
#include "fibonacci.h"

#pragma GCC warning "template.cpp compiled"

int main()
{
  std::cout << Factorial<400>::value << " " << Fibonacci<320>::value << std::endl;
  return Fibonacci<200>::value;
}
