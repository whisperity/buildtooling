#ifndef SYMBOLREWRITER_THEVISITOR_H
#define SYMBOLREWRITER_THEVISITOR_H

#include <string>
#include <vector>

#include <clang/ASTMatchers/ASTMatchFinder.h>

namespace SymbolRewriter
{

class FileReplaceDirectives;
class ImplementsEdges;

/**
 * A helper class that creates the necessary matchers for this tool based on the
 * given filename to search for.
 *
 * This class is used to clean up after the callback instances created.
 */
class MatcherFactory
{
public:
    MatcherFactory(FileReplaceDirectives& Replacements,
                   ImplementsEdges& ImplementsEdges);
    ~MatcherFactory();

    clang::ast_matchers::MatchFinder& operator()();

private:
    FileReplaceDirectives& Replacements;
    ImplementsEdges& Implementses;

    clang::ast_matchers::MatchFinder TheFinder;
    std::vector<clang::ast_matchers::MatchFinder::MatchCallback*> Callbacks;

    template <class Handler>
    clang::ast_matchers::MatchFinder::MatchCallback* CreateCallback();

    template <class Handler, class Matcher>
    inline void AddIDBoundMatcher(const char* ID, Matcher&& TheMatcher);
    template <class Handler, class Matcher>
    inline void AddIDBoundMatcher(Matcher&& TheMatcher);
};

} // namespace SymbolRewriter

#endif // SYMBOLREWRITER_THEVISITOR_H
