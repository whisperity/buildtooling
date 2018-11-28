#ifndef SYMBOLREWRITER_IMPLEMENTSEDGES_H
#define SYMBOLREWRITER_IMPLEMENTSEDGES_H

#include <iosfwd>
#include <set>

namespace SymbolRewriter
{

/**
 * Wrapper class that contains the mapping that a file specified to the
 * constructor implements things from other files.
 */
class ImplementsEdges
{

public:
    ImplementsEdges(std::string Filepath);

    void AddFileImplemented(std::string Implemented);

    const std::string& getFilepath() const;

    /**
     * Get the files that are implemented by the instance's file.
     */
    const std::set<std::string>& getImplementedFiles() const;

private:
    const std::string Filepath;
    std::set<std::string> ImplementedSet;

};

/**
 * Write the relation edges formatted to the given output stream. This output
 * can be machine-read.
 */
void writeImplementsOutput(std::ostream& Output,
                           const ImplementsEdges& Implementses);

} // namespace SymbolRewriter

#endif // SYMBOLREWRITER_IMPLEMENTSEDGES_H
