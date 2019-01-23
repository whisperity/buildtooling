#include "SymbolTableDump.h"

#include <iostream>
#include <initializer_list>
#include <utility>

static SymbolAnalyser::SymbolTableDump::SymbolVector EmptySymbolVector{};

namespace SymbolAnalyser
{

void SymbolTableDump::AddDefinition(std::string Filepath,
                                    std::size_t Line,
                                    std::size_t Col,
                                    std::string Symbol)
{
    auto ItP = CollectedDefinitions.try_emplace(
        std::move(Filepath), std::initializer_list<SymbolWithPosition>{});
    ItP.first->second.emplace_back(SymbolWithPosition{Line,
                                                      Col,
                                                      std::move(Symbol)});
}

void
SymbolTableDump::AddForwardDeclaration(std::string Filepath,
                                       std::size_t Line,
                                       std::size_t Col,
                                       std::string Symbol)
{
    auto ItP = CollectedForwardDeclarations.try_emplace(
        std::move(Filepath), std::initializer_list<SymbolWithPosition>{});
    ItP.first->second.emplace_back(SymbolWithPosition{Line,
                                                      Col,
                                                      std::move(Symbol)});
}

const std::set<std::string>
SymbolTableDump::getKnownFiles() const
{
    std::set<std::string> Ret;
    for (const auto& Entry : CollectedDefinitions)
        Ret.emplace(Entry.first);
    for (const auto& Entry : CollectedForwardDeclarations)
        Ret.emplace(Entry.first);
    return Ret;
}

const SymbolTableDump::SymbolVector&
SymbolTableDump::getDefinitions(std::string Filepath) const
{
    auto It = CollectedDefinitions.find(Filepath);
    if (It == CollectedDefinitions.end())
        return EmptySymbolVector;
    return It->second;
}

const SymbolTableDump::SymbolVector&
SymbolTableDump::getForwardDeclarations(
    std::string Filepath) const
{
    auto It = CollectedForwardDeclarations.find(Filepath);
    if (It == CollectedForwardDeclarations.end())
        return EmptySymbolVector;
    return It->second;
}


void writeSymbolDefinitionsOutput(std::ostream& Output,
                                  const std::string& FileToWrite,
                                  const SymbolTableDump& SymbolTable)
{
    for (const auto& S : SymbolTable.getDefinitions(FileToWrite))
        Output << FileToWrite
               << "##" << S.Line
               << "##" << S.Col
               << "##" << S.Symbol << std::endl;
}

void writeSymbolForwardDeclarationsOutput(std::ostream& Output,
                                          const std::string& FileToWrite,
                                          const SymbolTableDump& SymbolTable)
{
    for (const auto& S : SymbolTable.getForwardDeclarations(FileToWrite))
        Output << FileToWrite
               << "##" << S.Line
               << "##" << S.Col
               << "##" << S.Symbol << std::endl;
}

} // namespace SymbolAnalyser
