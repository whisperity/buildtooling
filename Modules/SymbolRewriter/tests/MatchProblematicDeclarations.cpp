#include "Test.h"

TEST(MatchProblematicDeclarations, OnEmptyFile)
{
    FileMap map = {
        {"main.cpp", ""}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    ASSERT_EQ(FRD->getReplacementPositions().size(), 0);
}

TEST(MatchProblematicDeclarations, InAnonymousNSSingleTypedef)
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
    auto R = FRD->getReplacementPositions();

    ASSERT_EQ(R.size(), 1);
    ASSERT_TRUE(inPositionVector(R, 4, 5));
}

TEST(MatchProblematicDeclarations, InAnonymousNSSingleRecord)
{
    FileMap map = {
        {"main.cpp", R"FILE(
namespace
{
    struct S {};
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacementPositions();

    ASSERT_EQ(R.size(), 1);
    ASSERT_TRUE(inPositionVector(R, 4, 5));
}

TEST(MatchProblematicDeclarations, InAnonymousNSSingleGlobalVar)
{
    FileMap map = {
        {"main.cpp", R"FILE(
namespace
{
    int i;
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacementPositions();

    ASSERT_EQ(R.size(), 1);
    ASSERT_TRUE(inPositionVector(R, 4, 5));
}

TEST(MatchProblematicDeclarations, InAnonymousNSSingleFunction)
{
    FileMap map = {
        {"main.cpp", R"FILE(
namespace
{
    void f() {}
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacementPositions();

    ASSERT_EQ(R.size(), 1);
    ASSERT_TRUE(inPositionVector(R, 4, 5));
}

TEST(MatchProblematicDeclarations, StaticGlobalVar)
{
    FileMap map = {
        {"main.cpp", R"FILE(
static int i;
extern int i2; // no-match
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacementPositions();

    ASSERT_EQ(R.size(), 1);
    ASSERT_TRUE(inPositionVector(R, 2, 1));
}

TEST(MatchProblematicDeclarations, StaticFunction)
{
    FileMap map = {
        {"main.cpp", R"FILE(
static void f() {}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "main.cpp", TrivialCompileCommand);
    auto R = FRD->getReplacementPositions();

    ASSERT_EQ(R.size(), 1);
    ASSERT_TRUE(inPositionVector(R, 2, 1));
}
