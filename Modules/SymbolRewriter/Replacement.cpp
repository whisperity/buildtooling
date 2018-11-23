#include "Replacement.h"

#include <iostream>
#include <utility>

namespace SymbolRewriter
{

FileReplaceDirectives::FileReplaceDirectives(std::string Filepath,
                                             std::string RewritePrefix)
    : Filepath(std::move(Filepath))
    , RewritePrefix(std::move(RewritePrefix))
{
    // FIXME: What to do if RewritePrefix invalid (e.g. file is "512FooFoo.cpp")
}

void FileReplaceDirectives::SetReplacementBinding(std::string From,
                                                  const void* BindingID)
{
    std::cout << "Replacing for node " << BindingID << " set from " << From
              << std::endl;

    ReplacementPair Replacement{From, RewritePrefix + "_" + From};
    Bindings.emplace(BindingID, std::move(Replacement));
}

void FileReplaceDirectives::AddReplacementPosition(size_t AtLine,
                                                   size_t AtCol,
                                                   std::string OfWhat,
                                                   const void* BindingID)
{
    std::cout << "Added a replacement location in the file at " << AtLine <<
              ":" << AtCol << " for string " << OfWhat << " bound to binding "
              << BindingID << std::endl;

    Replacements.emplace_back(AtLine, AtCol, OfWhat, BindingID);
}

const std::string& FileReplaceDirectives::getFilepath() const
{
    return Filepath;
}

std::vector<FileReplaceDirectives::Position>
FileReplaceDirectives::getReplacementPositions() const
{
    std::vector<std::pair<size_t, size_t>> Ret{};

    for (const Replacement& Rep : Replacements)
        Ret.emplace_back(Rep.Line, Rep.Col);

    return Ret;
}

std::map<FileReplaceDirectives::Position,
         FileReplaceDirectives::ReplacementPair>
FileReplaceDirectives::getReplacements() const
{
    std::map<FileReplaceDirectives::Position,
             FileReplaceDirectives::ReplacementPair> Ret;

    for (const Replacement& Rep : Replacements)
    {
        std::string ReplaceTo;
        auto It = Bindings.find(Rep.BindingID);
        if (It == Bindings.end())
            ReplaceTo = Rep.What + "__Unknown";
        else
            ReplaceTo = It->second.second;

        std::cerr << "[DUMP] Replacement at " << Rep.Line << ":" << Rep.Col
                  << " is " << Rep.What << " -> " << ReplaceTo << std::endl;
        Ret.emplace(std::make_pair(Rep.Line, Rep.Col),
                    std::make_pair(Rep.What, ReplaceTo));
        // FIXME: The "unknown" should be an actual replacement!
    }

    return Ret;
}

FileReplaceDirectives::Replacement::Replacement(size_t Line,
                                                size_t Col,
                                                std::string What,
                                                const void* BindingID)
    : BindingID(BindingID)
    , Line(Line)
    , Col(Col)
    , What(std::move(What))
{}

} // namespace SymbolRewriter