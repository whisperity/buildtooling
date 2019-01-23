#ifndef SYMBOLANALYSER_IMPLEMENTSEDGES_H
#define SYMBOLANALYSER_IMPLEMENTSEDGES_H

#include <iosfwd>
#include <map>
#include <set>

namespace SymbolAnalyser
{

/**
 * Wrapper class that contains the mapping that a file specified to the
 * constructor implements things from other files.
 */
class ImplementsEdges
{

public:
    typedef std::map<std::string, std::set<std::string>> ImplementsMap;

    ImplementsEdges(std::string Filepath);

    void AddImplemented(std::string Filename,
                        std::string ImplementedSymbol);

    const std::string& getFilepath() const;

    /**
     * Get the files that are implemented by the instance's file.
     */
    const ImplementsMap& getImplementationMap() const;

private:
    const std::string Filepath;
    ImplementsMap ImplementationMap;

};

/**
 * Write the relation edges formatted to the given output stream. This output
 * can be machine-read.
 */
void writeImplementsOutput(std::ostream& Output,
                           const ImplementsEdges& Implementses);

} // namespace SymbolAnalyser

#endif // SYMBOLANALYSER_IMPLEMENTSEDGES_H
