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
    ASSERT_EQ(getReplacementAt(R, 2, 13), "main_I");
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
    ASSERT_EQ(getReplacementAt(R, 4, 12), "main_S");
    ASSERT_EQ(getReplacementAt(R, 12, 5), "main_S");
    ASSERT_FALSE(nameMatched(R, "x"));
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
    ASSERT_EQ(getReplacementAt(R, 4, 9), "main_f");
    ASSERT_EQ(getReplacementAt(R, 12, 12), "main_f");
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
    ASSERT_EQ(getReplacementAt(R, 2, 13), "main_I");
    ASSERT_EQ(getReplacementAt(R, 6, 5), "main_I");
    ASSERT_EQ(getReplacementAt(R, 6, 7), "main_f");
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
              S s, S& sr, S* sp, S** spp, const S& scr,
              volatile int vi, volatile I vi2, const volatile L* cvlp,
              const L& clr, S&& s_xv,
              const I* * const *& cippcpr);
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 21);
    ASSERT_EQ(getReplacementAt(R, 2, 13), "main_I");
    ASSERT_EQ(getReplacementAt(R, 3, 14), "main_L");
    ASSERT_EQ(getReplacementAt(R, 7, 12), "main_S");

    ASSERT_EQ(getReplacementAt(R, 10, 13), "main_f");

    ASSERT_EQ(getReplacementAt(R, 10, 15), "main_I");
    ASSERT_EQ(getReplacementAt(R, 10, 20), "main_L");
    ASSERT_EQ(getReplacementAt(R, 10, 25), "main_I");
    ASSERT_EQ(getReplacementAt(R, 10, 32), "main_L");
    ASSERT_EQ(getReplacementAt(R, 10, 39), "main_I");
    ASSERT_EQ(getReplacementAt(R, 10, 46), "main_L");
    ASSERT_EQ(getReplacementAt(R, 10, 53), "main_I");

    ASSERT_EQ(getReplacementAt(R, 11, 15), "main_S");
    ASSERT_EQ(getReplacementAt(R, 11, 20), "main_S");
    ASSERT_EQ(getReplacementAt(R, 11, 27), "main_S");
    ASSERT_EQ(getReplacementAt(R, 11, 34), "main_S");
    ASSERT_EQ(getReplacementAt(R, 11, 49), "main_S");

    ASSERT_EQ(getReplacementAt(R, 12, 41), "main_I");
    ASSERT_EQ(getReplacementAt(R, 12, 63), "main_L");

    ASSERT_EQ(getReplacementAt(R, 13, 21), "main_L");
    ASSERT_EQ(getReplacementAt(R, 13, 29), "main_S");
}

TEST(RewriteUsagePoints, Variable)
{
    FileMap map = {
        {"main.cpp", R"FILE(
namespace
{
    long l = 42l;
}

int main()
{
    return l;
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 2);
    ASSERT_EQ(getReplacementAt(R, 4, 10), "main_l");
    ASSERT_EQ(getReplacementAt(R, 9, 12), "main_l");
}

TEST(RewriteUsagePoints, LocalVariableOfProblematicType)
{
    FileMap map = {
        {"main.cpp", R"FILE(
typedef int I;

int main()
{
    I i = 4;
    const I ci = 8;
    I& ir = i;
    const I& cir = ir;
    I* ip = &i;
    const I* cip = &ci;
    I* const icp = ip;
    const I* const cicp = cip;
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 9);
    ASSERT_EQ(getReplacementAt(R, 2, 13), "main_I");
    ASSERT_EQ(getReplacementAt(R, 6, 5), "main_I");
    ASSERT_EQ(getReplacementAt(R, 7, 11), "main_I");
    ASSERT_EQ(getReplacementAt(R, 8, 5), "main_I");
    ASSERT_EQ(getReplacementAt(R, 9, 11), "main_I");
    ASSERT_EQ(getReplacementAt(R, 10, 5), "main_I");
    ASSERT_EQ(getReplacementAt(R, 11, 11), "main_I");
    ASSERT_EQ(getReplacementAt(R, 12, 5), "main_I");
    ASSERT_EQ(getReplacementAt(R, 13, 11), "main_I");
}

TEST(RewriteUsagePoints, QualifiedGlobalVariable)
{
    FileMap map = {
        {"main.cpp", R"FILE(
typedef int I;

static const I* cip;
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 3);
    ASSERT_EQ(getReplacementAt(R, 2, 13), "main_I");
    ASSERT_EQ(getReplacementAt(R, 4, 14), "main_I");
    ASSERT_EQ(getReplacementAt(R, 4, 17), "main_cip");
}

TEST(RewriteUsagePoints, GlobalVariableWithTypedefFromHeader)
{
    FileMap map = {
        {"header.h", R"FILE(
namespace X
{
    typedef int I;
}
)FILE"},
        {"main.cpp", R"FILE(
#include "header.h"

typedef long L;

static const X::I* cip;
static const    L* clp;
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 4);
    ASSERT_FALSE(nameMatched(R, "I"));
    ASSERT_EQ(getReplacementAt(R, 4, 14), "main_L");
    ASSERT_EQ(getReplacementAt(R, 6, 20), "main_cip");
    ASSERT_EQ(getReplacementAt(R, 7, 17), "main_L");
    ASSERT_EQ(getReplacementAt(R, 7, 20), "main_clp");
}