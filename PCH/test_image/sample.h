#ifndef SAMPLE
#define SAMPLE

// This is a sample header to allow to see what are in PCHs.

int i(int* ip)
{
    return *ip + 2;
}

constexpr long l()
{
    return 8;
}

template <class T>
T inc(const T& t)
{
    return t + 1;
}

#endif // SAMPLE
