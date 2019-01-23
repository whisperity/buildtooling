#include "TheFinder.h"

#include <clang/AST/DeclCXX.h>
#include <llvm/ADT/Twine.h>

#include "ImplementsEdges.h"
#include "Replacement.h"
#include "SymbolTableDump.h"

using namespace clang;
using namespace clang::ast_matchers;
using namespace SymbolAnalyser;

namespace
{

/**
 * Search all declarations that have a usable name identifier but cannot be
 * named from the outside, and that are expanded in the main file - i.e. they
 * aren't in the TU because they are in an included header.
 */
auto LocalInTheTU = namedDecl(
    unless(hasExternalFormalLinkage()),
    isExpansionInMainFile());

/**
 * Matches outside-addressable named declarations that are implemented in the
 * current TU.
 */
auto ExternallyNamedButImplementedInTheTU = namedDecl(
    hasExternalFormalLinkage(),
    isExpansionInMainFile());

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
    hasParent(namespaceDecl()));

/**
 * Renaming such TU-Internal declarations is enough to break ambiguity.
 */
auto TUInternalTraits = allOf(
    LocalInTheTU,
    InSomeGlobalishScope);

/**
 * To seek out which headers are implemented in the current TU, we need only the
 * declarations that are in the above global-ish scope.
 */
auto TUVisibleTraits = allOf(
    ExternallyNamedButImplementedInTheTU,
    InSomeGlobalishScope);

/**
 * A match result callback class that handles the renaming of problematically
 * named declarations.
 */
class HandleDeclarations
    : public MatchFinder::MatchCallback
{

public:
    HandleDeclarations(FileReplaceDirectives& Replacements,
                       ImplementsEdges&,
                       SymbolTableDump&)
        : Replacements(Replacements)
    {}

    void run(const MatchFinder::MatchResult& Result) override
    {
        const NamedDecl* ND = nullptr;
        if ((ND = Result.Nodes.getNodeAs<FunctionDecl>("inline")))
        {
            // If an 'inline' function is matched in the TU, it must be checked
            // if it is an inline member function (otherwise wrongfully, but
            // this is an example from live code) implemented in an
            // implementation (source) file...

            // (In reality, the 'inline' specifier here only makes sure that
            // even though the member is "public" (if it is...) it can ONLY be
            // called from the implementation file itself.

            // The matcher matches this function because it appears to be a
            // full TU-local inline, but it has to be ignored if it is a class
            // member.
            if (isa<CXXMethodDecl>(ND))
                return;
        }
        else
        {
            // Otherwise try the default matcher bind...
            ND = Result.Nodes.getNodeAs<NamedDecl>("id");
            assert(ND && "Something matched as `id` but it wasn't a "
                         "`NamedDecl`?");
        }

        if (!ND->getDeclName().isIdentifier() || ND->getName().str().empty())
            // If the declaration hasn't a name, it cannot be renamed.
            return;

        const std::string& DeclName = ND->getName().str();
        const SourceLocation& Loc = Result.SourceManager->getSpellingLoc(
            ND->getLocation());
        std::string Filename = Result.SourceManager->getFilename(Loc);
        Replacements.SetReplacementBinding(ND->getName().str(), ND);
        if (Loc.isInvalid())
            return;
        if (Replacements.getFilepath() != Filename)
            return;

        Replacements.AddReplacementPosition(
            Result.SourceManager->getSpellingLineNumber(Loc),
            Result.SourceManager->getSpellingColumnNumber(Loc),
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
    HandleUsagePoints(FileReplaceDirectives& Replacements,
                      ImplementsEdges&,
                      SymbolTableDump&)
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
        if (Item->first == "declRefExpr-toInline")
        {
            const auto* DRE = Result.Nodes.getNodeAs<DeclRefExpr>(
                "declRefExpr-toInline");
            // Same logic as in 'HandleDeclarations': the inline member defined
            // "out of line" (...) must not be renamed, nor its usages
            // rewritten.
            if (isa<CXXMethodDecl>(DRE->getDecl()))
                return;

            return HandleDeclRefExpr(DRE, *Result.SourceManager);
        }

        assert(std::string("Should not have reached this point!").empty());
    }

private:
    void HandleTypeLoc(const TypeLoc* Loc, const SourceManager& SM)
    {
        const SourceLocation& SLoc = SM.getSpellingLoc(Loc->getBeginLoc());
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
        if (Loc.isInvalid())
            return;
        if (Replacements.getFilepath() != Filename)
            return;
        if (!DRE->getDecl()->getDeclName().isIdentifier())
            // Identifiers without a name cannot be renamed.
            return;

        Replacements.AddReplacementPosition(
            SM.getSpellingLineNumber(Loc),
            SM.getSpellingColumnNumber(Loc),
            DRE->getDecl()->getName().str(),
            DRE->getDecl());
    }

    FileReplaceDirectives& Replacements;
};

/**
 * A match result callback that registers that the source file implements
 * symbols from a header.
 */
class HandleFindingImplementsRelation
    : public MatchFinder::MatchCallback
{
public:
    HandleFindingImplementsRelation(FileReplaceDirectives&,
                                    ImplementsEdges& Implementses,
                                    SymbolTableDump&)
        : Implementses(Implementses)
    {}

    void run(const MatchFinder::MatchResult& Result) override
    {
        const auto* ND = Result.Nodes.getNodeAs<NamedDecl>("id");
        assert(ND && "Something matched as `id` but it wasn't a `NamedDecl`?");
        const Decl* PD = ND->getPreviousDecl();
        if (!PD)
            // If no PreviousDecl is found then the current declaration is the
            // one and only. In this case, this is some local symbol that was
            // never defined in a header but still has external linkage.
            // (This might be a case of developer oversight, or simply bad code,
            // or a symbol that is loaded dynamically. We unfortunately can't
            // support these cases in a nice fashion.)
            return;

        const SourceManager& SM = PD->getASTContext().getSourceManager();
        const SourceLocation& SLoc = SM.getSpellingLoc(PD->getBeginLoc());
        std::string Filename = SM.getFilename(SLoc);
        if (SLoc.isInvalid())
            return;
        if (SM.isInSystemHeader(SLoc) || SM.isInSystemMacro(SLoc))
            // System headers should stay where they are...
            return;
        if (Implementses.getFilepath() == Filename)
            // Ignore PreviousDecl's that are still in the current file. This
            // can happen if e.g. someone put a forward declaration after
            // another one, and before the main definition.
            return;

        // Try fetching the Decl's name from either the identifier (if it is
        // identifiable), or through other means (e.g. for operator+,
        // operator new).
        std::string DeclName;
        if (ND->getDeclName().isIdentifier())
            DeclName = ND->getName().str();
        else
            DeclName = ND->getDeclName().getAsString();

        if (DeclName.empty())
        {
            // If the name could not had been fetched, create a dummy symbol
            // name.
            using llvm::Twine;
            unsigned int Line = SM.getSpellingLineNumber(SLoc);
            unsigned int Column = SM.getSpellingColumnNumber(SLoc);
            DeclName = (Twine("unnameable_decl_at__") + Twine(Line) +
                "_" + Twine(Column)).str();
        }

        // Note: Declaration chains need not be walked transitively, because the
        // matcher matches on every declaration.
        Implementses.AddImplemented(Filename, DeclName);
    }

private:
    ImplementsEdges& Implementses;
};

/**
 * A match callback that handles filling the map with symbol table entries that
 * create subtle "uses" dependencies between headers and TUs.
 *
 * One such example is the forward declaration of classes, which must be kept
 * within the boundary of an emitted module.
 */
class HandleSymbolTableRelation
    : public MatchFinder::MatchCallback
{
public:
    HandleSymbolTableRelation(FileReplaceDirectives&,
                              ImplementsEdges&,
                              SymbolTableDump& SymbolTableDump)
      : SymbolTableDumper(SymbolTableDump)
    {}

    void run(const MatchFinder::MatchResult& Result) override
    {
        if (const auto* FwdND = Result.Nodes.getNodeAs<NamedDecl>("forward"))
            return HandleForwardDeclaration(FwdND);
        else if (const auto* DefND = Result.Nodes.getNodeAs<NamedDecl>(
            "define"))
        {
            if (const auto* RD = dyn_cast<CXXRecordDecl>(DefND))
            {
                if (RD->getDefinition() == RD)
                    return HandleDefinition(RD);
                else
                    // Sometimes a class can be "forward declared" in a file
                    // later (with regards to the full TU tokenstream) than it
                    // was defined, in which case it would be picked up as a
                    // fully defined (hasDefinition() is true) node.
                    return HandleForwardDeclaration(RD);
            }

            if (!DefND->hasBody())
                return HandleForwardDeclaration(DefND);
            return HandleDefinition(DefND);
        }

        assert(std::string("Matched something with an unhandled category.").
            empty());
    }

private:

    void HandleDefinition(const NamedDecl* ND)
    {
        if (isa<FieldDecl>(ND) || isa<CXXMethodDecl>(ND))
            // Definitions for record members might exist outside the record's
            // subtree e.g. out-of-line method implementations. However, these
            // symbols cannot be forward-declared out-of-line, hence they can be
            // omitted from this handler.
            return;

        const SourceManager& SM = ND->getASTContext().getSourceManager();
        const SourceLocation& SLoc = SM.getSpellingLoc(ND->getBeginLoc());
        std::string Filename = SM.getFilename(SLoc);
        if (SLoc.isInvalid())
            return;
        if (SM.isInSystemHeader(SLoc) || SM.isInSystemMacro(SLoc))
            // System headers should stay where they are...
            return;
        if (!ND->getDeclName().isIdentifier() || ND->getName().str().empty())
            // Identifiers without a name cannot be forward declared in writing.
            return;

        SymbolTableDumper.AddDefinition(
            Filename,
            SM.getSpellingLineNumber(SLoc),
            SM.getSpellingColumnNumber(SLoc),
            ND->getQualifiedNameAsString());
    }

    void HandleForwardDeclaration(const NamedDecl* ND)
    {
        const SourceManager& SM = ND->getASTContext().getSourceManager();
        const SourceLocation& SLoc = SM.getSpellingLoc(ND->getBeginLoc());
        std::string Filename = SM.getFilename(SLoc);
        if (SLoc.isInvalid())
            return;
        if (SM.isInSystemHeader(SLoc) || SM.isInSystemMacro(SLoc))
            // System headers should stay where they are...
            return;
        if (!ND->getDeclName().isIdentifier() || ND->getName().str().empty())
            // Identifiers without a name cannot be forward declared in writing.
            return;

        if (const auto* Fun = dyn_cast<FunctionDecl>(ND))
            if (const FunctionDecl* FunDef = Fun->getDefinition())
            {
                const SourceLocation& DefLoc = SM.getSpellingLoc(
                    FunDef->getBeginLoc());
                if (DefLoc.isValid() && SM.isInMainFile(DefLoc) &&
                    SM.isInMainFile(SLoc))
                {
                    // If the function is forward declared *and* defined in the
                    // same file, then it is most likely just a coding
                    // convention of a "local" symbol (and the code writers did
                    // not care about the symbol name having external linkage).
                    return;
                }
            }

        SymbolTableDumper.AddForwardDeclaration(
            Filename,
            SM.getSpellingLineNumber(SLoc),
            SM.getSpellingColumnNumber(SLoc),
            ND->getQualifiedNameAsString());
    }

    SymbolTableDump& SymbolTableDumper;
};

} // namespace (anonymous)

namespace SymbolAnalyser
{

MatcherFactory::MatcherFactory(FileReplaceDirectives& Replacements,
                               ImplementsEdges& ImplementsEdges,
                               class SymbolTableDump& SymbolTableDumper)
   : Replacements(Replacements)
   , Implementses(ImplementsEdges)
   , SymbolTableDumper(SymbolTableDumper)
{
    auto InlineFunctionInMainFile = functionDecl(
        isInline(), isExpansionInMainFile());

    // Create matchers for named declarations which are to be renamed.
    {
        auto ProblematicNamedDeclarations = {
            // Basically every name-able "top-level" thing.
            functionDecl(TUInternalTraits),
            varDecl(TUInternalTraits),
            recordDecl(TUInternalTraits),
            typedefNameDecl(TUInternalTraits)
        };
        for (auto Matcher : ProblematicNamedDeclarations)
            AddIDBoundMatcher<HandleDeclarations>(Matcher);

        AddIDBoundMatcher<HandleDeclarations>(
            "inline", InlineFunctionInMainFile);
    }

    // Add a matchers that will report the usage of such a named declaration.
    {
        // Match type locations that are in the main file.
        // (This will match, e.g. for a "const T*&", the outer type
        // const&, the inner type T*, and the innermost type T. In case this
        // T is a problematic symbol, a match will eventually take care of
        // it.
        AddIDBoundMatcher<HandleUsagePoints>("typeLoc",
            typeLoc(isExpansionInMainFile()));
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

        AddIDBoundMatcher<HandleUsagePoints>(
            "declRefExpr-toInline", declRefExpr(to(InlineFunctionInMainFile)));
    }

    // Add the matcher handle responsible for collecting what the current main
    // file implements.
    {
        auto ImplementingDecls = {
            functionDecl(TUVisibleTraits),
            varDecl(TUVisibleTraits)
        };
        for (auto Matcher : ImplementingDecls)
            AddIDBoundMatcher<HandleFindingImplementsRelation>(Matcher);
    }

    // Adds matchers that help spanning the more subtle dependency relations
    // between TUs.
    {
        // Forward declarations must be respected across module boundaries,
        // because a forward declaration in module A cannot be used in a
        // module B, as it will result in a conflict.
        auto ForwardDecls = {
            functionDecl(InSomeGlobalishScope,
                         unless(isDefinition())),
            varDecl(InSomeGlobalishScope,
                    unless(isDefinition())),
            cxxRecordDecl(InSomeGlobalishScope,
                          unless(hasDefinition()))
        };
        for (auto Matcher : ForwardDecls)
            AddIDBoundMatcher<HandleSymbolTableRelation>("forward", Matcher);

        // Also fill the "symbol table" with the actual definitions of these
        // symbols.
        auto DefiningDecls = {
            functionDecl(InSomeGlobalishScope,
                         hasExternalFormalLinkage(),
                         isDefinition()),
            varDecl(InSomeGlobalishScope,
                    hasExternalFormalLinkage(),
                    isDefinition()),
            cxxRecordDecl(InSomeGlobalishScope,
                          hasExternalFormalLinkage(),
                          hasDefinition())
        };
        for (auto Matcher : DefiningDecls)
            AddIDBoundMatcher<HandleSymbolTableRelation>("define", Matcher);
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
    Callbacks.push_back(new Handler{this->Replacements,
                                    this->Implementses,
                                    this->SymbolTableDumper});
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

} // namespace SymbolAnalyser
