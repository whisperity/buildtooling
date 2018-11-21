#ifndef SYMBOLREWRITER_EXECUTOR_H
#define SYMBOLREWRITER_EXECUTOR_H

#include <map>
#include <string>
#include <vector>

namespace clang
{
namespace tooling
{

class CompilationDatabase;

} // namespace tooling
} // namespace clang


namespace SymbolRewriter
{

typedef std::map<std::string, std::string> FileMap;

/**
 * Execute the rewriting collector tool's implementation on the given file
 * using compiler options from the given compilation database.
 *
 * @returns The result status of ClangTool#run().
 */
int ExecuteTool(clang::tooling::CompilationDatabase& CompDb,
                const std::string& Filename);

/**
 * Execute the rewriting collector tool's on the given file map (path to content
 * buffer) and a source file that has contents in the map, using the fabricated
 * compilation command.
 *
 * @returns The result status of ClangTool#run().
 */
int ExecuteTool(const FileMap& FileMap,
                const std::string& SourceName,
                const std::vector<std::string>& CompileCommand);

} // namespace SymbolRewriter

#endif // SYMBOLREWRITER_EXECUTOR_H
