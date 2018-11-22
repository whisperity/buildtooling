#include "Test.h"

#include <algorithm>
#include <memory>

std::vector<std::string> TrivialCompileCommand = {
    "/usr/bin/c++",
    "-std=c++14",
    "-c",
    "main.cpp",
    "-o",
    "main.o"
};

UsableResult getReplacementsForCompilation(
    const FileMap& FileMap,
    const std::string& Filename,
    const std::vector<std::string>& CompileCommand)
{
    ToolResult Result = ExecuteTool(FileMap, Filename, CompileCommand);
    if (std::get_if<int>(&Result))
        return nullptr;
    return std::move(std::get<UsableResult>(Result));
}

bool inPositionVector(
    const std::vector<FileReplaceDirectives::Position>& PVec,
    size_t Line,
    size_t Col)
{
    return std::find(PVec.begin(), PVec.end(),
                     std::make_pair(Line, Col)) !=
           PVec.end();
}


int main(int argc, const char** argv)
{
    ::testing::InitGoogleTest(&argc, const_cast<char**>(argv));
    return RUN_ALL_TESTS();
}
