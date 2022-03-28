#include "Replacement.h"

#include <iostream>
#include <utility>

namespace SymbolAnalyser
{

FileReplaceDirectives::FileReplaceDirectives(std::string Filepath,
                                             std::string RewritePrefixStr)
    : Filepath(std::move(Filepath))
    , RewritePrefix(std::move(RewritePrefixStr))
{
    // Fix identifier name if it begins with a number.
    if (std::isdigit(RewritePrefix.front()))
    {
        std::cerr << "WARN: Filename '" << RewritePrefix
                  << "' starts with digit, renaming..." << std::endl;
        RewritePrefix.insert(RewritePrefix.begin(), '_');
    }

    // Fix some more bogus characters that create invalid identifiers.
    auto It = RewritePrefix.begin();
    const auto End = RewritePrefix.end();
    for (auto It = RewritePrefix.begin(); It != End; ++It)
    {
        if (*It == '-' || *It == '.')
        {
            std::cerr << "WARN: Identifier-invalid character '" << *It
                      << "' encountered in '" << RewritePrefix
                      << "', replacing with '_'" << std::endl;
            *It = '_';
        }
    }
}

void FileReplaceDirectives::SetReplacementBinding(std::string From,
                                                  const void* BindingID)
{
    ReplacementPair Replacement{From, RewritePrefix + "_" + From};
    Bindings.emplace(BindingID, std::move(Replacement));
}

void FileReplaceDirectives::AddReplacementPosition(size_t AtLine,
                                                   size_t AtCol,
                                                   std::string OfWhat,
                                                   const void* BindingID)
{
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
            // There can be cases where a position for replacement was marked
            // but the targeted binding doesn't exist. Disregard these fake
            // matches.
            continue;
        else
            ReplaceTo = It->second.second;

        Ret.emplace(std::make_pair(Rep.Line, Rep.Col),
                    std::make_pair(Rep.What, ReplaceTo));
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

void writeReplacementOutput(std::ostream& Output,
                            const FileReplaceDirectives& Directives)
{
    const std::string& FP = Directives.getFilepath();
    for (const auto& E : Directives.getReplacements())
    {
        Output << FP << "##"
            << E.first.first << ":" << E.first.second << "##"
            << E.second.first << "##" << E.second.second << '\n';
    }
}

} // namespace SymbolAnalyser
