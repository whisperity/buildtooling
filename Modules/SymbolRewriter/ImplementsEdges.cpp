#include "ImplementsEdges.h"

#include <iostream>
#include <utility>

namespace SymbolRewriter
{

ImplementsEdges::ImplementsEdges(std::string Filepath)
    : Filepath(std::move(Filepath))
{}

void ImplementsEdges::AddFileImplemented(std::string Implemented)
{
    ImplementedSet.emplace(std::move(Implemented));
}

const std::string& ImplementsEdges::getFilepath() const
{
    return Filepath;
}

const std::set<std::string>& ImplementsEdges::getImplementedFiles() const
{
    return ImplementedSet;
}

void writeImplementsOutput(
    std::ostream& Output,
    const ImplementsEdges& Implementses)
{
    const std::string& FP = Implementses.getFilepath();
    for (const std::string& File : Implementses.getImplementedFiles())
        Output << FP << "##" << File << std::endl;
}

} // namespace SymbolRewriter
