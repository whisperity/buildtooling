#include "Executor.h"

#include <algorithm>
#include <iostream>
#include <utility>

#include <clang/Tooling/CompilationDatabase.h>
#include <clang/Tooling/Tooling.h>
#include <llvm/Support/Path.h>

#include "ImplementsEdges.h"
#include "Replacement.h"
#include "SymbolTableDump.h"
#include "TheFinder.h"

using namespace clang::tooling;
using namespace llvm::sys::path;

namespace SymbolAnalyser
{

ToolExecution::ToolExecution(clang::tooling::CompilationDatabase& CompDb,
                             std::string Filepath)
    : Compilations(CompDb)
    , Filepath(std::move(Filepath))
{}

ToolResult ToolExecution::operator()()
{
    assert(!Executed && "Execute called multiple times on the same job!");
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
    auto Replacements = std::make_unique<FileReplaceDirectives>(
        Filepath, stem(Filepath));
    auto Implementses = std::make_unique<ImplementsEdges>(Filepath);
    auto SymbolTableDumper = std::make_unique<SymbolTableDump>();
    MatcherFactory Factory{*Replacements,
                           *Implementses,
                           *SymbolTableDumper};

    std::cout << "Running for '" << Filepath << "'..." << std::endl;
    int Result = Tool.run(newFrontendActionFactory(&Factory()).get());
    if (Result)
    {
        std::cerr << "Non-zero result code " << Result
                  << " for " << Filepath << std::endl;
        return Result;
    }
    return std::make_tuple(std::move(Replacements),
                           std::move(Implementses),
                           std::move(SymbolTableDumper));
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
    auto Replacements = std::make_unique<FileReplaceDirectives>(
        SourceName, stem(SourceName));
    auto Implementses = std::make_unique<ImplementsEdges>(SourceName);
    auto SymbolTableDumper = std::make_unique<SymbolTableDump>();
    MatcherFactory Factory{*Replacements,
                           *Implementses,
                           *SymbolTableDumper};

    std::cout << "Running for '" << SourceName << "'..." << std::endl;
    int Result = Tool.run(newFrontendActionFactory(&Factory()).get());
    if (Result)
    {
        std::cerr << "Non-zero result code " << Result
                  << " for " << SourceName << std::endl;
        return Result;
    }
    return std::make_tuple(std::move(Replacements),
                           std::move(Implementses),
                           std::move(SymbolTableDumper));
}

} // namespace SymbolAnalyser