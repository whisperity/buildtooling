#ifndef SYMBOLANALYSER_SYMBOLTABLEDUMP_H
#define SYMBOLANALYSER_SYMBOLTABLEDUMP_H

#include <map>
#include <set>
#include <vector>

namespace SymbolAnalyser
{

/**
 *
 */

class SymbolTableDump
{

public:
    struct SymbolWithPosition
    {
        std::size_t Line;
        std::size_t Col;
        std::string Symbol;
    };

    typedef std::vector<SymbolWithPosition> SymbolVector;

    void AddDefinition(std::string Filepath,
                       std::size_t Line,
                       std::size_t Col,
                       std::string Symbol);
    void AddForwardDeclaration(std::string Filepath,
                       std::size_t Line,
                       std::size_t Col,
                       std::string Symbol);

    const std::set<std::string> getKnownFiles() const;

    const SymbolVector& getDefinitions(std::string Filepath) const;
    const SymbolVector& getForwardDeclarations(std::string Filepath) const;

    //const ImplementsMap& getImplementationMap() const;

private:
    typedef std::map<std::string, SymbolVector> SymbolMapToFile;

    SymbolMapToFile CollectedForwardDeclarations;
    SymbolMapToFile CollectedDefinitions;
};

/**
 * Write the definitions formatted to the given output stream. This output
 * can be machine-read.
 */
void writeSymbolDefinitionsOutput(std::ostream& Output,
                        const std::string& FileToWrite,
                        const SymbolTableDump& SymbolTable);

/**
 * Write the collected forwards formatted to the given output stream. This
 * output can be machine-read.
 */
void writeSymbolForwardDeclarationsOutput(std::ostream& Output,
                                          const std::string& FileToWrite,
                                          const SymbolTableDump& SymbolTable);

} // namespace SymbolAnalyser

#endif // SYMBOLANALYSER_SYMBOLTABLEDUMP_H
