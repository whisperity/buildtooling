#include "Executor.h"
#include "TheFinder.h"

#include <algorithm>
#include <iostream>

#include <clang/Tooling/CompilationDatabase.h>
#include <clang/Tooling/Tooling.h>

using namespace clang::tooling;

namespace SymbolRewriter
{

int ExecuteTool(clang::tooling::CompilationDatabase& CompDb,
                const std::string& Filename)
{
    ClangTool Tool(CompDb, {Filename});
    std::cout << "Running for '" << Filename << "'" << std::endl;
    MatcherFactory Factory{Filename};
    int Result = Tool.run(newFrontendActionFactory(&Factory()).get());
    std::cout << "Result code: " << Result << std::endl;
    return Result;
}

int ExecuteTool(const FileMap& FileMap,
                const std::string& SourceName,
                const std::vector<std::string>& CompileCommand)
{
    std::vector<const char*> Argv;
    Argv.reserve(CompileCommand.size());
    Argv.push_back("--");
    std::transform(CompileCommand.begin(), CompileCommand.end(),
                   std::back_inserter(Argv),
                   [](const auto& E) { return E.c_str(); });

    std::unique_ptr<FixedCompilationDatabase> CompDb;
    {
        // HACK: Clang wants to int& to this...
        auto Argc = static_cast<int>(Argv.size());
        std::string LoadError;
        CompDb = FixedCompilationDatabase::loadFromCommandLine(
            Argc, Argv.data(), LoadError);
        if (!CompDb)
        {
            std::cerr << "Couldn't create in-memory compilation database, "
                         "because:" << std::endl;
            std::cerr << '\t' << LoadError << std::endl;
            return 1;
        }
    }

    ClangTool Tool(*CompDb, {SourceName});
    for (const auto& e : FileMap)
        Tool.mapVirtualFile(e.first, e.second);
    std::cout << "Running for '" << SourceName << "'" << std::endl;
    MatcherFactory Factory{SourceName};
    int Result = Tool.run(newFrontendActionFactory(&Factory()).get());
    std::cout << "Result code: " << Result << std::endl;
    return Result;
}

} // namespace SymbolRewriter