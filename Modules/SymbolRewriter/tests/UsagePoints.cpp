#include "Test.h"

TEST(RewriteUsagePoints, Typedef)
{
    FileMap map = {
        {"main.cpp", R"FILE(
typedef int I;

int main()
{
    I i = 2;
    return i;
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 2);
    ASSERT_EQ(getReplacementAt(R, 2, 1), "main_I");
    ASSERT_EQ(getReplacementAt(R, 6, 5), "main_I");
}

TEST(RewriteUsagePoints, LocalRecord)
{
    FileMap map = {
        {"main.cpp", R"FILE(
namespace
{
    struct S
    {
        int x;
    };
}

int main()
{
    S s;
    s.x = 4;
    return s.x + 1;
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 2);
    ASSERT_EQ(getReplacementAt(R, 4, 5), "main_S");
    ASSERT_EQ(getReplacementAt(R, 12, 5), "main_S");
}

TEST(RewriteUsagePoints, FunctionCall)
{
    FileMap map = {
        {"main.cpp", R"FILE(
namespace
{
    int f()
    {
        return 0;
    }
}

int main()
{
    return f();
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 2);
    ASSERT_EQ(getReplacementAt(R, 4, 5), "main_f");
    ASSERT_EQ(getReplacementAt(R, 14, 12), "main_f");
}

TEST(RewriteUsagePoints, FunctionCallWithLocalType)
{
    FileMap map = {
        {"main.cpp", R"FILE(
typedef int I;

namespace
{
    I f()
    {
        return 0;
    }
}

int main()
{
    return f();
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 4);
    ASSERT_EQ(getReplacementAt(R, 2, 1), "main_I");
    ASSERT_EQ(getReplacementAt(R, 4, 5), "main_I");
    ASSERT_EQ(getReplacementAt(R, 4, 7), "main_f");
    ASSERT_EQ(getReplacementAt(R, 14, 12), "main_f");
}

TEST(RewriteUsagePoints, LocalTypesInArgumentList)
{
    FileMap map = {
        {"main.cpp", R"FILE(
typedef int I;
typedef long L;

namespace
{
    struct S {};
}

static void f(I i, L l, I& ir, L& lr, I* ip, L* lp, I** ipp,
              S s, S& sr, S* sp, S** ssp, const S& scr);
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 16);
    ASSERT_EQ(getReplacementAt(R, 2, 1), "main_I");
    ASSERT_EQ(getReplacementAt(R, 3, 1), "main_L");
    ASSERT_EQ(getReplacementAt(R, 7, 5), "main_S");

    ASSERT_EQ(getReplacementAt(R, 10, 1), "main_f");
    ASSERT_EQ(getReplacementAt(R, 10, 15), "main_I");
    ASSERT_EQ(getReplacementAt(R, 10, 20), "main_L");
    ASSERT_EQ(getReplacementAt(R, 10, 25), "main_I");
    ASSERT_EQ(getReplacementAt(R, 10, 32), "main_L");
    ASSERT_EQ(getReplacementAt(R, 10, 39), "main_I");
    ASSERT_EQ(getReplacementAt(R, 10, 46), "main_L");
    ASSERT_EQ(getReplacementAt(R, 10, 51), "main_I");

    ASSERT_EQ(getReplacementAt(R, 11, 15), "main_S");
    ASSERT_EQ(getReplacementAt(R, 11, 20), "main_S");
    ASSERT_EQ(getReplacementAt(R, 11, 27), "main_S");
    ASSERT_EQ(getReplacementAt(R, 11, 34), "main_S");
    ASSERT_EQ(getReplacementAt(R, 11, 43), "main_S");
}
