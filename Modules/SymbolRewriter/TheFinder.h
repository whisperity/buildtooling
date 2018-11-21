#ifndef SYMBOLREWRITER_THEVISITOR_H
#define SYMBOLREWRITER_THEVISITOR_H

#include <string>
#include <vector>

#include <clang/ASTMatchers/ASTMatchFinder.h>

namespace SymbolRewriter
{

/**
 * A helper class that creates the necessary matchers for this tool based on the
 * given filename to search for.
 *
 * This class is used to clean up after the callback instances created.
 */
class MatcherFactory
{
public:
    MatcherFactory(const std::string& Filename);
    ~MatcherFactory();

    clang::ast_matchers::MatchFinder& operator()();

private:
    clang::ast_matchers::MatchFinder TheFinder;
    std::vector<clang::ast_matchers::MatchFinder::MatchCallback*> Callbacks;

    template <class Handler>
    clang::ast_matchers::MatchFinder::MatchCallback* CreateCallback();

    template <class Handler, class Matcher>
    inline void AddIDBoundMatcher(Matcher&& TheMatcher);
};

} // namespace SymbolRewriter

#endif //SYMBOLREWRITER_THEVISITOR_H
