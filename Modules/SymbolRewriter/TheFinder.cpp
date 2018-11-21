#include "TheFinder.h"

#include <iostream>

#include <clang/AST/DeclCXX.h>

using namespace clang;
using namespace clang::ast_matchers;

/**
 * A match result callback class that handles the rewriting of problematic
 * declarations.
 */
class HandleDeclarations
    : public MatchFinder::MatchCallback
{

public:
    void run(const MatchFinder::MatchResult& Result) override
    {
        auto* ND = Result.Nodes.getNodeAs<NamedDecl>("id");
        assert(ND && "Something matched as `id` but it wasn't a `NamedDecl`?");

        std::cout << "Matched problematic symbol " << ND->getDeclKindName()
                  << ": " << ND->getName().str() << std::endl;
    }

};

/**
 * A match result callback class that handles >usages< of problematic symbols.
 */
class HandleUsagePoints
    : public MatchFinder::MatchCallback
{

    void HandleTypeLoc(const TypeLoc* Loc, const SourceManager& SM)
    {
        std::cout << "Matched mention of problematic type symbol starting at "
                  << std::endl
                  << Loc->getSourceRange().getBegin().printToString(SM)
                  << std::endl;
    }

    void HandleDeclRefExpr(const DeclRefExpr* DRE)
    {
        std::cout << "Matched usage of problematic symbol in:" << std::endl;
        DRE->dumpColor();
    }

public:
    void run(const MatchFinder::MatchResult& Result) override
    {
        const auto Item = Result.Nodes.getMap().begin();
        if (Item->first == "typeLoc")
            return HandleTypeLoc(Result.Nodes.getNodeAs<TypeLoc>("typeLoc"),
                                 *Result.SourceManager);
        if (Item->first == "declRefExpr")
            return HandleDeclRefExpr(
                Result.Nodes.getNodeAs<DeclRefExpr>("declRefExpr"));
    }

};

namespace
{

/**
 * Search all declarations that have a usable name identifier, and that are
 * expanded in the main file - i.e. they aren't in the TU because they are in
 * an included header.
 */
auto LocalInTheTU = namedDecl(
    allOf(
        unless(hasExternalFormalLinkage()),
        isExpansionInMainFile()));

/**
 * However, the previous matcher would also match things like a local variable
 * in a "static void f()". For this very reason, we only consider "things" that
 * are kinda global-y in the TU itself, i.e. they are in the truly global scope,
 * or in a namespace.
 *
 * E.g. inner classes need not be matched, because if their outer class' name is
 * rewritten, the inner class can be properly referenced.
 */
auto InSomeGlobalishScope = anyOf(
    hasParent(translationUnitDecl()),
    hasParent(namespaceDecl()));      /* NOTE: Need to match every namespace
                                       * because one can put a TU-local typedef
                                       * or class into a non-anonymous namespace
                                       * which is still visible only to that TU.
                                       */

/**
 * Renaming such TU-Internal declarations is enough to break ambiguity.
 */
auto TUInternalTraits = allOf(LocalInTheTU, InSomeGlobalishScope);

} // namespace (anonymous)

namespace SymbolRewriter
{

MatcherFactory::MatcherFactory(const std::string& Filename)
{
    // Create matchers for named declarations which are to be renamed.
    auto ProblematicNamedDeclarations = {
        // Basically every name-able "top-level" thing.
        functionDecl(TUInternalTraits),
        varDecl(TUInternalTraits),
        recordDecl(TUInternalTraits),
        typedefNameDecl(TUInternalTraits)
    };
    for (auto Matcher : ProblematicNamedDeclarations)
        AddIDBoundMatcher<HandleDeclarations>(Matcher);

    // Add a matchers that will report the usage of such a named declaration.
    /*{
        auto ProblematicDeclUsages = {
            // These matchers match on every type locations that eventually name
            // problematic types.
            loc(qualType(hasDeclaration(recordDecl(TUInternalTraits)))),
            loc(qualType(hasDeclaration(typedefNameDecl(TUInternalTraits))))
        };
        for (auto Matcher : ProblematicDeclUsages)
            AddIDBoundMatcher<HandleUsagePoints>("typeLoc", Matcher);
    }
    {
        auto ProblematicDeclUsages = {
            // These matchers match the references to the problematic callables.
            declRefExpr(to(functionDecl(TUInternalTraits))),
            declRefExpr(to(varDecl(TUInternalTraits)))
        };
        for (auto Matcher : ProblematicDeclUsages)
            AddIDBoundMatcher<HandleUsagePoints>("declRefExpr", Matcher);
    }*/
}

MatcherFactory::~MatcherFactory()
{
    // The finder does not take ownership of the match callbacks, so they need
    // to be deleted now.
    for (MatchFinder::MatchCallback* Callback : Callbacks)
        delete Callback;
}

MatchFinder& MatcherFactory::operator()() { return TheFinder; }

template <class Handler>
MatchFinder::MatchCallback* MatcherFactory::CreateCallback()
{
    Callbacks.push_back(new Handler{});
    return Callbacks.back();
}

template <class Handler, class Matcher>
void MatcherFactory::AddIDBoundMatcher(const char* ID, Matcher&& TheMatcher)
{
    TheFinder.addMatcher(id(ID, TheMatcher),
                         this->CreateCallback<Handler>());
}

template <class Handler, class Matcher>
void MatcherFactory::AddIDBoundMatcher(Matcher&& TheMatcher)
{
    this->AddIDBoundMatcher<Handler>("id", TheMatcher);
}

} // namespace SymbolRewriter
