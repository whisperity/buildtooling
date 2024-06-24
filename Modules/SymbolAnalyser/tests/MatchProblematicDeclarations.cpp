#include "Test.h"

TEST(MatchProblematicDeclarations, OnEmptyFile)
{
    FileMap map = {
        {"/main.cpp", ""}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    ASSERT_EQ(FRD->getReplacementPositions().size(), 0);
}

TEST(MatchProblematicDeclarations, InAnonymousNSSingleTypedef)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
namespace
{
    typedef int MyIntType;
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyIntType", 4, 17));
}

TEST(MatchProblematicDeclarations, InAnonymousNSSingleRecord)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
namespace
{
    struct S {};
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_TRUE(nameMatchedAtPosition(R, "S", 4, 12));
}

TEST(MatchProblematicDeclarations, InAnonymousNSSingleGlobalVar)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
namespace
{
    int i;
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_TRUE(nameMatchedAtPosition(R, "i", 4, 9));
}

TEST(MatchProblematicDeclarations, InAnonymousNSSingleFunction)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
namespace
{
    void f() {}
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_TRUE(nameMatchedAtPosition(R, "f", 4, 10));
}

TEST(MatchProblematicDeclarations, StaticGlobalVar)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
static int i;
extern int i2; // This should not match as the global name 'i2' has linkage.
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_TRUE(nameMatchedAtPosition(R, "i", 2, 12));
    EXPECT_FALSE(nameMatched(R, "i2"));
}

TEST(MatchProblematicDeclarations, StaticFunction)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
static void f() {}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_TRUE(nameMatchedAtPosition(R, "f", 2, 13));
}

TEST(MatchProblematicDeclarations, MultiSymbolOneMatches)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
namespace X
{
    typedef int T;
    void f() {}    // This function shouldn't match, external linkage X::f()!
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_TRUE(nameMatchedAtPosition(R, "T", 4, 17));
    EXPECT_FALSE(nameMatched(R, "f"));
}

TEST(MatchProblematicDeclarations, MultiSymbolManyMatches)
{
    // QUESTION: Shouldn't X::S also be caught if it is never forward declared
    // and only in the current file? (Concatenating two files like this would
    // constitute a TU-redefinition of the struct which is a compile error!)
    FileMap map = {
        {"/main.cpp", R"FILE(
namespace X
{
    typedef int T;
    struct S {};   // This symbol has external linkage as X::S.
    void f() {}    // This function shouldn't match, external linkage X::f()!
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_TRUE(nameMatchedAtPosition(R, "T", 4, 17));
    EXPECT_FALSE(nameMatched(R, "S"));
    EXPECT_FALSE(nameMatched(R, "f"));
}

TEST(MatchProblematicDeclarations_WithHeaders, SingleTypedefInHeader)
{
    FileMap map = {
        {"/header.h", R"FILE(
typedef int T;
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
    EXPECT_FALSE(nameMatched(R, "T"));
}

TEST(MatchProblematicDeclarations_WithHeaders, SingleTypedefInHeaderNS)
{
    FileMap map = {
        {"/header.h", R"FILE(
namespace X
{
    typedef int T;
}
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
    EXPECT_FALSE(nameMatched(R, "T"));
}

TEST(MatchProblematicDeclarations_WithHeaders, SingleVariableInHeader)
{
    FileMap map = {
        {"/header.h", R"FILE(
extern int i;
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
    EXPECT_FALSE(nameMatched(R, "i"));
}

TEST(MatchProblematicDeclarations_WithHeaders, SingleVariableInHeaderNS)
{
    FileMap map = {
        {"/header.h", R"FILE(
namespace X
{
    extern int i;
}
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
    EXPECT_FALSE(nameMatched(R, "i"));
}

TEST(MatchProblematicDeclarations_WithHeaders, SingleVariableInHeader_Alloc)
{
    FileMap map = {
        {"/header.h", R"FILE(
extern int i;
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

int i = 4;
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
    EXPECT_FALSE(nameMatched(R, "i"));
}

TEST(MatchProblematicDeclarations_WithHeaders, SingleVariableInHeaderNS_Alloc)
{
    FileMap map = {
        {"/header.h", R"FILE(
namespace X
{
    extern int i;
}
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

int X::i = 4;
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
    EXPECT_FALSE(nameMatched(R, "i"));
}

TEST(MatchProblematicDeclarations_WithHeaders, SingleFunctionInHeader)
{
    FileMap map = {
        {"/header.h", R"FILE(
void f();
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
    EXPECT_FALSE(nameMatched(R, "f"));
}

TEST(MatchProblematicDeclarations_WithHeaders, SingleFunctionInHeaderNS)
{
    FileMap map = {
        {"/header.h", R"FILE(
namespace X
{
    void f();
}
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
    EXPECT_FALSE(nameMatched(R, "f"));
}

TEST(MatchProblematicDeclarations_WithHeaders, SingleFunctionInHeader_Defined)
{
    FileMap map = {
        {"/header.h", R"FILE(
void f();
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

void f() { return; }
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
    EXPECT_FALSE(nameMatched(R, "f"));
}

TEST(MatchProblematicDeclarations_WithHeaders, SingleFunctionInHeaderNS_Defined)
{
    FileMap map = {
        {"/header.h", R"FILE(
namespace X
{
    void f();
}
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

void X::f() { return; }
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
    EXPECT_FALSE(nameMatched(R, "f"));
}

TEST(MatchProblematicDeclarations_WithHeaders_AndALocal, SingleTypedef)
{
    FileMap map = {
        {"/header.h", R"FILE(
typedef int T;
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

typedef long U;
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_FALSE(nameMatched(R, "T"));
    EXPECT_TRUE(nameMatchedAtPosition(R, "U", 4, 14));
}

TEST(MatchProblematicDeclarations_WithHeaders_AndALocal, SingleTypedefInNS)
{
    FileMap map = {
        {"/header.h", R"FILE(
namespace X
{
    typedef int T;
}
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

typedef X::T U;
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_FALSE(nameMatched(R, "T"));
    EXPECT_TRUE(nameMatchedAtPosition(R, "U", 4, 14));
}

TEST(MatchProblematicDeclarations_WithHeaders_AndALocal, SingleVariable)
{
    FileMap map = {
        {"/header.h", R"FILE(
extern int i;
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

static long l = 8;
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_FALSE(nameMatched(R, "i"));
    EXPECT_TRUE(nameMatchedAtPosition(R, "l", 4, 13));
}

TEST(MatchProblematicDeclarations_WithHeaders_AndALocal, SingleVariableInNS)
{
    FileMap map = {
        {"/header.h", R"FILE(
namespace X
{
    extern int i;
}
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

static long l = 8;
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_FALSE(nameMatched(R, "i"));
    EXPECT_TRUE(nameMatchedAtPosition(R, "l", 4, 13));
}

TEST(MatchProblematicDeclarations_WithHeaders_AndALocal, SingleVariable_Alloc)
{
    FileMap map = {
        {"/header.h", R"FILE(
extern int i;
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

int i = 4;
static long l = 8;
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_FALSE(nameMatched(R, "i"));
    EXPECT_TRUE(nameMatchedAtPosition(R, "l", 5, 13));
}

TEST(MatchProblematicDeclarations_WithHeaders_AndALocal,
     SingleVariableInNS_Alloc)
{
    FileMap map = {
        {"/header.h", R"FILE(
namespace X
{
    extern int i;
}
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

int X::i = 4;
static long l = 8;
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_FALSE(nameMatched(R, "i"));
    EXPECT_TRUE(nameMatchedAtPosition(R, "l", 5, 13));
}

TEST(MatchProblematicDeclarations_WithHeaders_AndALocal, SingleFunction)
{
    FileMap map = {
        {"/header.h", R"FILE(
void f();
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

static void g();
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_FALSE(nameMatched(R, "f"));
    EXPECT_TRUE(nameMatchedAtPosition(R, "g", 4, 13));
}

TEST(MatchProblematicDeclarations_WithHeaders_AndALocal, SingleFunctionInNS)
{
    FileMap map = {
        {"/header.h", R"FILE(
namespace X
{
    void f();
}
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

static void g();
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_FALSE(nameMatched(R, "f"));
    EXPECT_TRUE(nameMatchedAtPosition(R, "g", 4, 13));
}

TEST(MatchProblematicDeclarations_WithHeaders_AndALocal, SingleFunction_Defined)
{
    FileMap map = {
        {"/header.h", R"FILE(
void f();
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

void f() { return; }

static int g() { return 2; }
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_FALSE(nameMatched(R, "f"));
    EXPECT_TRUE(nameMatchedAtPosition(R, "g", 6, 12));
}

TEST(MatchProblematicDeclarations_WithHeaders_AndALocal,
     SingleFunctionInNS_Defined)
{
    FileMap map = {
        {"/header.h", R"FILE(
namespace X
{
    void f();
}
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

void X::f() { return; }

static int g() { return 4; }
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_FALSE(nameMatched(R, "f"));
    EXPECT_TRUE(nameMatchedAtPosition(R, "g", 6, 12));
}

TEST(MatchProblematicDeclarations_WithHeaders_AndALocal,
     SingleFunction_TypesInNS)
{
    FileMap map = {
        {"/header.h", R"FILE(
namespace X
{
    typedef int I;
    typedef long L;
}
)FILE"},

        {"/main.cpp", R"FILE(
#include "/header.h"

static void d(X::I i, X::L l) {}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 1);
    EXPECT_FALSE(nameMatched(R, "I"));
    EXPECT_FALSE(nameMatched(R, "L"));
    EXPECT_TRUE(nameMatchedAtPosition(R, "d", 4, 13));
}

TEST(MatchProblematicDeclarations_WithForwardDecl, Function)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
namespace
{
    long l();
}

namespace
{
    long l()
    {
        return 4;
    }
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 2);
    EXPECT_TRUE(nameMatchedAtPosition(R, "l", 4, 10));
    EXPECT_TRUE(nameMatchedAtPosition(R, "l", 9, 10));
}

TEST(MatchProblematicDeclarations_InInnerScope, Typedef)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
typedef int I;

int main()
{
    typedef long L;
    I i = 2;
    L l = i * 2;
    return l;
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 2);
    EXPECT_FALSE(nameMatched(R, "L"));
    EXPECT_TRUE(nameMatchedAtPosition(R, "I", 2, 13));
    EXPECT_TRUE(nameMatchedAtPosition(R, "I", 7, 5));
}

TEST(MatchProblematicDeclarations_InInnerScope, Record)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
int main()
{
    struct S { int x; };

    S s;
    s.x = 2;
    return s.x;
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
    EXPECT_FALSE(nameMatched(R, "s"));
    EXPECT_FALSE(nameMatched(R, "x"));
}

TEST(MatchProblematicDeclarations_InnerScope, Lambda)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
int main()
{
    auto lambda = [](int i) { return 2 + i; };

    return lambda(4);
}
)FILE"}
    };

    // The lambda's type and implementation does not have a visible name so
    // it should not be renamed, neither the lambda ()'s variable.
    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
}

TEST(MatchProblematicDeclarations_InnerScope, GenericLambda)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
int main()
{
    auto lambda = [](auto&& i) { return 2 + i; };

    return lambda(4);
}
)FILE"}
    };

    // The lambda's type and implementation does not have a visible name so
    // it should not be renamed, neither the lambda ()'s variable.
    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
}

TEST(MatchProblematicDeclarations, LocalInlineMethod)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
inline int f();

int main()
{
    return f();
}

inline int f()
{
    return 1;
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 3);
    EXPECT_TRUE(nameMatchedAtPosition(R, "f", 2, 12));
    EXPECT_TRUE(nameMatchedAtPosition(R, "f", 6, 12));
    EXPECT_TRUE(nameMatchedAtPosition(R, "f", 9, 12));

}

TEST(MatchProblematicDeclarations, ClassInlineMethod)
{
    FileMap map = {
        {"/header.h", R"FILE(
class X
{
  public:
    inline int x() { return 1; }
};
)FILE"},
        {"/main.cpp", R"FILE(
#include "/header.h"

int main()
{
    return X{}.x();
}

)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
}

TEST(MatchProblematicDeclarations, ClassInlineMethodDefinedInImplFile)
{
    // This example is taken from a live project... I suppose the original
    // intention was to make sure a member function can only be called from the
    // (otherwise non-template-) class' implmentation file.

    FileMap map = {
        {"/header.h", R"FILE(
class X
{
  public:
    inline int x();
};
)FILE"},
        {"/main.cpp", R"FILE(
#include "/header.h"

inline int X::x()
{
    return 1;
}

int main()
{
    return X{}.x();
}

)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 0);
}

TEST(MatchProblematicDeclarations, AnonymousClassSpecialMemberFunctionInline)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
namespace
{
    class MyClass
    {
    private:
        int M;
    public:
        MyClass(int I) : M(I) {}
        MyClass(const MyClass&) = default;
        MyClass& operator=(const MyClass&) = default;
        ~MyClass() {}

        int foo() const { return M; }
    };
}

int main()
{
    return MyClass{42}.foo();
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 8);
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 4, 11));  // class MyClass
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 9, 9));   // MyClass(int)
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 10, 9));  // MyClass(const)
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 10, 23)); // const MyClass&
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 11, 9));  // MyClass&
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 11, 34)); // =(const MyClass)
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 12, 10)); // ~MyClass
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 20, 12)); // MyClass{42}
}

TEST(MatchProblematicDeclarations, AnonymousClassSpecialMemberFunctionOutOfLine)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
namespace
{
    class MyClass
    {
    private:
        int M;
    public:
        MyClass(int I);
        MyClass(const MyClass&);
        MyClass& operator=(const MyClass&);
        ~MyClass();

        int foo() const { return M; }
    };

    MyClass::MyClass(int I) : M(I) {}
    MyClass::MyClass(const MyClass&) = default;
    MyClass& MyClass::operator=(const MyClass&) = default;
    MyClass::~MyClass() {}
}

int main()
{
    return MyClass{42}.foo();
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 18);
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 4, 11));  // class MyClass
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 9, 9));   // MyClass(int)
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 10, 9));  // MyClass(const)
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 10, 23)); // const MyClass&
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 11, 9));  // MyClass&
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 11, 34)); // =(const MyClass)
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 12, 10)); // ~MyClass
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 17, 5));  // MyClass::
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 17, 14)); // ::MyClass(int)
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 18, 5));  // MyClass::
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 18, 14)); // ::MyClass(const)
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 18, 28)); // const MyClass&
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 19, 5));  // MyClass&
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 19, 14)); // MyClass::operator
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 19, 39)); // =(const MyClass)
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 20, 5));  // MyClass::
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 20, 15)); // ::~MyClass
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 25, 12)); // MyClass{42}
}

TEST(MatchProblematicDeclarations, AnonymousClassMemberOutsideAnonymousNS)
{
    FileMap map = {
        {"/main.cpp", R"FILE(
namespace
{
    class MyClass
    {
    private:
        int M;
    public:
        MyClass(int I);

        int foo() const;
    };
}

MyClass::MyClass(int I) : M(I) {}

int MyClass::foo() const { return M; }

int main()
{
    return MyClass{42}.foo();
}
)FILE"}
    };

    auto FRD = getReplacementsForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_NE(FRD, nullptr);
    auto R = FRD->getReplacements();

    EXPECT_EQ(R.size(), 6);
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 4, 11));  // class MyClass
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 9, 9));   // MyClass(int)
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 15, 1));  // MyClass::
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 15, 10)); // MyClass(int)
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 17, 5));  // MyClass::foo()
    EXPECT_TRUE(nameMatchedAtPosition(R, "MyClass", 21, 12)); // MyClass{42}

    EXPECT_FALSE(nameMatchedAtPosition(R, "MyClass", 17, 14)); // ::foo()
    EXPECT_FALSE(nameMatchedAtPosition(R, "MyClass", 21, 24)); // .foo()
}
