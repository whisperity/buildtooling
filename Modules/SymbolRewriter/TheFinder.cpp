#include "TheFinder.h"

#include <iostream>

#include <clang/AST/DeclCXX.h>

using namespace clang;
using namespace clang::ast_matchers;

class HandleMatch
    : public MatchFinder::MatchCallback
{

public:
    void run(const MatchFinder::MatchResult& Result) override
    {
        const CXXRecordDecl *Class =
            Result.Nodes.getNodeAs<CXXRecordDecl>("id");
        if (!Class)
        {
            std::cerr << "ERR: No match..." << std::endl;
            return;
        }

        std::cout << "Matched class: " << Class->getName().str() << std::endl;
    }

};

SymbolRewriter::MatcherFactory::MatcherFactory(const std::string& Filename)
{
    std::cout << "CREATE " << Filename << std::endl;

    MatchFinder::MatchCallback* Handle = new HandleMatch;
    Callbacks.push_back(Handle);
    TheFinder.addMatcher(id("id", cxxRecordDecl()), Handle);
}

SymbolRewriter::MatcherFactory::~MatcherFactory()
{
    // The finder does not take ownership of the match callbacks, so they need
    // to be deleted now.
    for (MatchFinder::MatchCallback* Callback : Callbacks)
        delete Callback;
}

MatchFinder& SymbolRewriter::MatcherFactory::operator()() { return TheFinder; }
