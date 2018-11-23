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

bool positionFound(
    const std::map<FileReplaceDirectives::Position,
                   FileReplaceDirectives::ReplacementPair>& RMap,
    size_t Line,
    size_t Col)
{
    return RMap.find(std::make_pair(Line, Col)) != RMap.end();
}

bool positionFound(
    const std::vector<FileReplaceDirectives::Position>& PVec,
    size_t Line,
    size_t Col)
{
    return std::find(PVec.begin(), PVec.end(),
                     std::make_pair(Line, Col)) !=
           PVec.end();
}

bool nameMatched(
    const std::map<FileReplaceDirectives::Position,
                   FileReplaceDirectives::ReplacementPair>& RMap,
    std::string Name)
{
    return std::find_if(RMap.begin(), RMap.end(),
        [&Name](auto& E)
        {
            return E.second.first == Name;
        }) != RMap.end();
}

bool nameMatchedAtPosition(
    const std::map<FileReplaceDirectives::Position,
                   FileReplaceDirectives::ReplacementPair>& RMap,
    std::string Name,
    size_t Line,
    size_t Col)
{
    auto It = RMap.find(std::make_pair(Line, Col));
    if (It == RMap.end())
        return false;

    return It->second.first == Name;
}

int main(int argc, const char** argv)
{
    ::testing::InitGoogleTest(&argc, const_cast<char**>(argv));
    return RUN_ALL_TESTS();
}
