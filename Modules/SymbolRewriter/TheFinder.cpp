#include "TheFinder.h"

#include <iostream>

#include <clang/AST/DeclCXX.h>

#include "Replacement.h"

using namespace clang;
using namespace clang::ast_matchers;
using namespace SymbolRewriter;

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
 *
 * @note Need to match every namespace because one can put a TU-local typedef
 * or class into a non-anonymous namespace which is still visible only to that
 * TU.
 */
auto InSomeGlobalishScope = anyOf(
    hasParent(translationUnitDecl()),
    hasParent(namespaceDecl())
);

/**
 * Renaming such TU-Internal declarations is enough to break ambiguity.
 */
auto TUInternalTraits = allOf(LocalInTheTU, InSomeGlobalishScope);

/**
 * A match result callback class that handles the rewriting of problematic
 * declarations.
 */
class HandleDeclarations
    : public MatchFinder::MatchCallback
{

public:
    HandleDeclarations(FileReplaceDirectives& Replacements)
        : Replacements(Replacements)
    {}

    void run(const MatchFinder::MatchResult& Result) override
    {
        auto* ND = Result.Nodes.getNodeAs<NamedDecl>("id");
        assert(ND && "Something matched as `id` but it wasn't a `NamedDecl`?");

        if (!ND->getDeclName().isIdentifier() || ND->getName().str().empty())
            // If the declaration hasn't a name, it cannot be renamed.
            return;

        const std::string& DeclName = ND->getName().str();
        const SourceLocation& Loc = Result.SourceManager->getSpellingLoc(
            ND->getLocation());
        std::string Filename = Result.SourceManager->getFilename(Loc);
        size_t Line = Result.SourceManager->getSpellingLineNumber(Loc);
        size_t Column = Result.SourceManager->getSpellingColumnNumber(Loc);

        Replacements.SetReplacementBinding(ND->getName().str(), ND);
        if (Loc.isInvalid())
            return;
        if (Replacements.getFilepath() != Filename)
            return;

        Replacements.AddReplacementPosition(
            Line,
            Column,
            DeclName,
            ND);
    }

private:
    FileReplaceDirectives& Replacements;
};

/**
 * A match result callback class that handles >usages< of problematic symbols.
 */
class HandleUsagePoints
    : public MatchFinder::MatchCallback
{

public:
    HandleUsagePoints(FileReplaceDirectives& Replacements)
        : Replacements(Replacements)
    {}

    void run(const MatchFinder::MatchResult& Result) override
    {
        const auto Item = Result.Nodes.getMap().begin();
        if (Item->first == "typeLoc")
            return HandleTypeLoc(Result.Nodes.getNodeAs<TypeLoc>("typeLoc"),
                                 *Result.SourceManager);
        if (Item->first == "declRefExpr")
            return HandleDeclRefExpr(
                Result.Nodes.getNodeAs<DeclRefExpr>("declRefExpr"),
                *Result.SourceManager);

        assert(std::string("Should not have reached this point!").empty());
    }

private:
    void HandleTypeLoc(const TypeLoc* Loc, const SourceManager& SM)
    {
        const SourceLocation& SLoc = SM.getSpellingLoc(Loc->getLocStart());
        std::string Filename = SM.getFilename(SLoc);
        if (SLoc.isInvalid())
            return;
        if (Replacements.getFilepath() != Filename)
            return;

        const Type* Type = Loc->getTypePtr();
        // Try different kinds of type location usages.
        if (HandleDeclForTypeLoc<TypedefNameDecl>(
            Type->getAsAdjusted<TypedefType>(), SM, SLoc))
            return;

        if (HandleDeclForTypeLoc<RecordDecl>(
            Type->getAsAdjusted<RecordType>(), SM, SLoc))
            return;

        // It's not directly a problem if a TypeLoc was matched that does not
        // refer to any of the above cases.
    }

    /**
     * Helper function that matches on a Type's declaration and adds a rewrite
     * to the TypeLoc at the file position SLoc if certain criteria (such as
     * the referred Decl being in the local translation unit's global scope,
     * not coming from an externally nameable namespace) match.
     */
    template <typename DeclT, typename TypeT>
    bool HandleDeclForTypeLoc(const TypeT* Ty,
                              const SourceManager& SM,
                              const SourceLocation& SLoc)
    {
        if (!Ty)
            return false;
        const DeclT* D = Ty->getDecl();
        if (!D)
            return false;

        // Try to see if the TypeLoc's referred Decl matches the usual criteria.
        auto Match = ast_matchers::match(
            decl(TUInternalTraits), *D, D->getASTContext());
        if (Match.empty())
            return false;

        if (!D->getDeclName().isIdentifier() || D->getName().str().empty())
            // Identifiers without a name cannot be renamed.
            return false;

        Replacements.AddReplacementPosition(
            SM.getSpellingLineNumber(SLoc),
            SM.getSpellingColumnNumber(SLoc),
            D->getName().str(),
            D);

        return true;
    }

    void HandleDeclRefExpr(const DeclRefExpr* DRE, const SourceManager& SM)
    {
        const SourceLocation& Loc = SM.getSpellingLoc(DRE->getLocation());
        std::string Filename = SM.getFilename(Loc);
        size_t Line = SM.getSpellingLineNumber(Loc);
        size_t Column = SM.getSpellingColumnNumber(Loc);
        if (Loc.isInvalid())
            return;
        if (Replacements.getFilepath() != Filename)
            return;

        if (!DRE->getDecl()->getDeclName().isIdentifier())
            // Identifiers without a name cannot be renamed.
            return;

        Replacements.AddReplacementPosition(
            Line,
            Column,
            DRE->getDecl()->getName().str(),
            DRE->getDecl());
    }

    FileReplaceDirectives& Replacements;
};

} // namespace (anonymous)

namespace SymbolRewriter
{

MatcherFactory::MatcherFactory(const std::string& Filename,
                               FileReplaceDirectives& Replacements)
   : Replacements(Replacements)
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
    {
        auto DeclaringToRecord = hasDeclaration(recordDecl(TUInternalTraits));
        auto DeclaringToTypedef = hasDeclaration(
            typedefNameDecl(TUInternalTraits));

        auto ProblematicDeclUsages = {
            // Match type locations that are in the main file.
            // (This will match, e.g. for a "const T*&", the outer type
            // const&, the inner type T*, and the innermost type T. In case this
            // T is a problematic symbol, a match will eventually take care of
            // it.
            typeLoc(isExpansionInMainFile())
        };
        for (auto Matcher : ProblematicDeclUsages)
            AddIDBoundMatcher<HandleUsagePoints>("typeLoc", Matcher);
    }
    {
        auto ProblematicDeclUsages = {
            // These matchers match declaration references to problematic
            // TU-local functions or variables. This matches more than
            // "TUInternalTraits", but there are certain cases (e.g. lambdas)
            // where a parent matcher can't be used...
            // (These extra cases are not considered valid later on.)
            declRefExpr(to(functionDecl(LocalInTheTU))),
            declRefExpr(to(varDecl(LocalInTheTU)))
        };
        for (auto Matcher : ProblematicDeclUsages)
            AddIDBoundMatcher<HandleUsagePoints>("declRefExpr", Matcher);
    }
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
    Callbacks.push_back(new Handler{this->Replacements});
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
