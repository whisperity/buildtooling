#include "TheFinder.h"

#include <iostream>

#include <clang/AST/DeclCXX.h>

using namespace clang;
using namespace clang::ast_matchers;

class HandleTULocalNames
    : public MatchFinder::MatchCallback
{

public:
    void run(const MatchFinder::MatchResult& Result) override
    {
        auto* ND = Result.Nodes.getNodeAs<NamedDecl>("id");
        if (!ND)
        {
            std::cerr << "Error! Something was matched, but it is not a "
                         "`NamedDecl`..." << std::endl;
            auto* D = Result.Nodes.getNodeAs<Decl>("id");
            if (!D)
                std::cerr << "Even bigger error! It's not even a `Decl`?!"
                          << std::endl;
            else
                D->dump();

            return;
        }

        std::cout << "Matched " << ND->getDeclKindName() << ": "
                  << ND->getName().str() << std::endl;
    }

};

namespace
{

auto LocalInTheTU = namedDecl(
    allOf(
        unless(hasExternalFormalLinkage()),
        isExpansionInMainFile()));

auto InGloballyAnonymousScope = anyOf(
    hasParent(translationUnitDecl()),
    hasParent(namespaceDecl(isAnonymous())));

auto TUInternalTraits = allOf(LocalInTheTU, InGloballyAnonymousScope);

} // namespace (anonymous)

namespace SymbolRewriter
{

MatcherFactory::MatcherFactory(const std::string& Filename)
{
    AddIDBoundMatcher<HandleTULocalNames>(functionDecl(TUInternalTraits));
    AddIDBoundMatcher<HandleTULocalNames>(varDecl(TUInternalTraits));
    AddIDBoundMatcher<HandleTULocalNames>(recordDecl(TUInternalTraits));
    AddIDBoundMatcher<HandleTULocalNames>(typedefNameDecl(TUInternalTraits));
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
void MatcherFactory::AddIDBoundMatcher(Matcher&& TheMatcher)
{
    TheFinder.addMatcher(id("id", TheMatcher),
                         this->CreateCallback<Handler>());
}

} // namespace SymbolRewriter
