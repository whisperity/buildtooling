#ifndef FIBONACCI
#define FIBONACCI

// Calculate the value passed as T
template <int T>
struct Fibonacci
{
    enum { value = (Fibonacci<T - 1>::value + Fibonacci<T - 2>::value) };
};

// In the template meta-programming, we do not have conditionals, so instead
// we use struct-overloading like mechanism to set constraints, we do this for
// numbers 0, 1 and 2, just like our algorithm in the function above.
template <>
struct Fibonacci<0>
{
    enum { value = 1 };
};

template <>
struct Fibonacci<1>
{
    enum { value = 1 };
};

template <>
struct Fibonacci<2>
{
    enum { value = 1 };
};

#endif // FIBONACCI
