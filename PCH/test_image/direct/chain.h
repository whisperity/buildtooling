#ifndef CHAIN
#define CHAIN

int g();

class A
{
  public:
    int i;
    long l;
};

void h(int i, long l)
{
    A a;
    a.i = i;
    a.l = l;

    g(i);
    g(l);
    g(a);
}

#endif // CHAIN
