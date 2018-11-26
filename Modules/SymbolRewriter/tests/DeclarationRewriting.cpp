#include "Test.h"

TEST(DeclarationRewriting, SimpleTypedef)
{
    FileMap map = {
        {"main.cpp", R"FILE(
namespace
{
    typedef int MyIntType;
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 1);
    ASSERT_EQ(getReplacementAt(R, 4, 17), "main_MyIntType");
}

TEST(DeclarationRewriting, SimpleFunction)
{
    FileMap map = {
        {"main.cpp", R"FILE(
namespace
{
    long f() { return 0; }
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 1);
    ASSERT_EQ(getReplacementAt(R, 4, 10), "main_f");
}

TEST(DeclarationRewriting_AnotherFilename, SimpleFunction)
{
    FileMap map = {
        {"foo.cpp", R"FILE(
namespace
{
    long f() { return 0; }
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "foo.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 1);
    ASSERT_EQ(getReplacementAt(R, 4, 10), "foo_f");
}

TEST(DeclarationRewriting, SimpleFunctionWithPrototype)
{
    FileMap map = {
        {"main.cpp", R"FILE(
namespace
{
    long l();
}

namespace
{
    long l()
    {
        return 4;
    }
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacements();

    ASSERT_EQ(R.size(), 2);
    ASSERT_EQ(getReplacementAt(R, 4, 10), "main_l");
    ASSERT_EQ(getReplacementAt(R, 9, 10), "main_l");
}
