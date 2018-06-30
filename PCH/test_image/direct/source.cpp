#pragma GCC warning "Source file compiled..."

int main()
{
    int i = f();
    g(i);

    std::string foo = "Foo";
    g(foo);

    return f();
}