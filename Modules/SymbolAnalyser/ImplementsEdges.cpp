#include "ImplementsEdges.h"

#include <initializer_list>
#include <iostream>
#include <utility>

namespace SymbolAnalyser
{

ImplementsEdges::ImplementsEdges(std::string Filepath)
    : Filepath(std::move(Filepath))
{}

void ImplementsEdges::AddImplemented(std::string Filename,
                                     std::string ImplementedSymbol)
{
    auto ItP = ImplementationMap.try_emplace(
        std::move(Filename), std::initializer_list<std::string>{});
    ItP.first->second.emplace(std::move(ImplementedSymbol));
}

const std::string& ImplementsEdges::getFilepath() const
{
    return Filepath;
}

const ImplementsEdges::ImplementsMap&
ImplementsEdges::getImplementationMap() const
{
    return ImplementationMap;
}

void writeImplementsOutput(
    std::ostream& Output,
    const ImplementsEdges& Implementses)
{
    const std::string& FP = Implementses.getFilepath();
    for (const auto& E : Implementses.getImplementationMap())
        for (const std::string& Symbol : E.second)
            Output << FP << "##" << E.first << "##" << Symbol << std::endl;
}

} // namespace SymbolAnalyser
