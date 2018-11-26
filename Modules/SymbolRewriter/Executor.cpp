#include "Executor.h"

#include <algorithm>
#include <iostream>
#include <utility>

#include <clang/Tooling/CompilationDatabase.h>
#include <clang/Tooling/Tooling.h>
#include <llvm/Support/Path.h>

#include "Replacement.h"
#include "TheFinder.h"

using namespace clang::tooling;
using namespace llvm::sys::path;

namespace SymbolRewriter
{

ToolExecution::ToolExecution(clang::tooling::CompilationDatabase& CompDb,
                             std::string Filepath)
    : Compilations(CompDb)
    , Filepath(std::move(Filepath))
{
}

ToolResult ToolExecution::operator()()
{
    assert(!Executed && "Execute called multiple times on the job!");
    Executed = true;
    return ExecuteTool(Compilations, Filepath);
}

const std::string& ToolExecution::filepath() const
{
    return Filepath;
}

std::string ToolExecution::filepathWithoutExtension() const
{
    std::string Path = Filepath;
    const std::string& Extension = extension();
    auto It = Path.find(Extension);
    if (It != std::string::npos)
        Path.replace(It, Extension.length(), "");

    return Path;
}

std::string ToolExecution::filename() const
{
    return stem(Filepath);
}

std::string ToolExecution::extension() const
{
    return ::extension(Filepath);
}

ToolResult ExecuteTool(clang::tooling::CompilationDatabase& CompDb,
                       const std::string& Filepath)
{
    ClangTool Tool(CompDb, {Filepath});
    std::cout << "Running for '" << Filepath << "'" << std::endl;

    auto Replacements = std::make_unique<FileReplaceDirectives>(
        Filepath, stem(Filepath));

    MatcherFactory Factory{Filepath, *Replacements};

    int Result = Tool.run(newFrontendActionFactory(&Factory()).get());
    std::cout << "Result code: " << Result << std::endl;

    if (Result)
        return Result;
    return std::move(Replacements);
}

ToolResult ExecuteTool(const FileMap& FileMap,
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

    auto Replacements = std::make_unique<FileReplaceDirectives>(
        SourceName, stem(SourceName));
    MatcherFactory Factory{SourceName, *Replacements};

    int Result = Tool.run(newFrontendActionFactory(&Factory()).get());
    std::cout << "Result code: " << Result << std::endl;

    if (Result)
        return Result;
    return std::move(Replacements);
}

} // namespace SymbolRewriter