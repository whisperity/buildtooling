#ifndef SYMBOLREWRITER_EXECUTOR_H
#define SYMBOLREWRITER_EXECUTOR_H

#include <map>
#include <memory>
#include <string>
#include <variant>
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

class FileReplaceDirectives;
class ImplementsEdges;
class SymbolTableDump;

typedef std::map<std::string, std::string> FileMap;

typedef std::tuple<
    std::unique_ptr<FileReplaceDirectives>,
    std::unique_ptr<ImplementsEdges>,
    std::unique_ptr<SymbolTableDump>> UsefulResultType;

typedef std::variant<int, UsefulResultType> ToolResult;

/**
 * Wrapper class that saves an 'ExecuteTool' call's inputs and allows later
 * execution on the contained data.
 *
 * @warning Make sure the owner of the compilation database does not die before
 * "Execute" is called.
 */
class ToolExecution
{
public:
    ToolExecution(clang::tooling::CompilationDatabase& CompDb,
                  std::string Filename);

    /**
     * Runs ExecuteTool() with the stored arguments.
     *
     * @note A single ToolExecution should only be executed ONCE.
     */
    // TODO: enable_unique_from_this? ;)
    ToolResult operator()();

    const std::string& filepath() const;
    std::string filepathWithoutExtension() const;
    std::string filename() const;
    std::string extension() const;

private:
    bool Executed = false;

    clang::tooling::CompilationDatabase& Compilations;
    std::string Filepath;
};

/**
 * Execute the rewriting collector tool's implementation on the given file
 * using compiler options from the given compilation database.
 *
 * @returns The result status of ClangTool#run().
 */
ToolResult ExecuteTool(clang::tooling::CompilationDatabase& CompDb,
                       const std::string& Filepath);

/**
 * Execute the rewriting collector tool's on the given file map (path to content
 * buffer) and a source file that has contents in the map, using the fabricated
 * compilation command.
 *
 * @returns The result status of ClangTool#run().
 */
ToolResult ExecuteTool(const FileMap& FileMap,
                       const std::string& SourceName,
                       const std::vector<std::string>& CompileCommand);

} // namespace SymbolRewriter

#endif // SYMBOLREWRITER_EXECUTOR_H
