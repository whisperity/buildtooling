#include <gtest/gtest.h>

#include "Executor.h"

using namespace SymbolRewriter;

namespace
{

static std::vector<std::string> TrivialCompileCommand = {
    "/usr/bin/c++",
    "-std=c++14",
    "-c",
    "main.cpp",
    "-o",
    "main.o"
};

} // namespace (anonymous)

int main(int argc, const char** argv)
{
    ::testing::InitGoogleTest(&argc, const_cast<char**>(argv));
    return RUN_ALL_TESTS();
}

TEST(Try, Try)
{
    FileMap map = {
        {"main.cpp",
         "#include <iostream>"}
    };

    int R = ExecuteTool(map, "main.cpp", TrivialCompileCommand);
    ASSERT_EQ(R, 0);
}
