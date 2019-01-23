#include "Test.h"

TEST(FindImplementsRelation, EmptyFile)
{
    FileMap map = {
        {"/main.cpp", ""}
    };

    auto IE = getImplementsRelationForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    ASSERT_EQ(IE->getImplementationMap().size(), 0);
}

TEST(FindImplementsRelation, SingleImplementedHeader)
{
    FileMap map = {
        {"/header.h", "void f();"},
        {"/main.cpp", R"FILE(
#include "/header.h"

void f() { return; }
)FILE"}
    };

    auto IE = getImplementsRelationForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    auto& I = IE->getImplementationMap();
    ASSERT_EQ(I.size(), 1);
    ASSERT_EQ(I.count("/header.h"), 1);
    ASSERT_EQ(I.at("/header.h").size(), 1);
    ASSERT_EQ(I.at("/header.h").count("f"), 1);
}

TEST(FindImplementsRelation, MultipleHeadersSomeNotImplemented)
{
    FileMap map = {
        {"/header.h", "void f();"},
        {"/header2.h", "void g();"},
        {"/main.cpp", R"FILE(
#include "/header.h"
#include "/header2.h"

void f() { return; }
)FILE"}
    };

    auto IE = getImplementsRelationForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    auto& I = IE->getImplementationMap();
    ASSERT_EQ(I.size(), 1);
    ASSERT_EQ(I.count("/header.h"), 1);
    ASSERT_EQ(I.count("/header2.h"), 0);
    ASSERT_EQ(I.at("/header.h").size(), 1);
    ASSERT_EQ(I.at("/header.h").count("f"), 1);
}

TEST(FindImplementsRelation, MultipleHeaders)
{
    FileMap map = {
        {"/header.h", "void f();"},
        {"/header2.h", "void g();"},
        {"/main.cpp", R"FILE(
#include "/header.h"
#include "/header2.h"

void f() { return; }

void g() { return; }
)FILE"}
    };

    auto IE = getImplementsRelationForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    auto& I = IE->getImplementationMap();
    ASSERT_EQ(I.size(), 2);
    ASSERT_EQ(I.count("/header.h"), 1);
    ASSERT_EQ(I.count("/header2.h"), 1);
    ASSERT_EQ(I.at("/header.h").size(), 1);
    ASSERT_EQ(I.at("/header.h").count("f"), 1);
    ASSERT_EQ(I.at("/header2.h").size(), 1);
    ASSERT_EQ(I.at("/header2.h").count("g"), 1);
}

TEST(FindImplementsRelation, TransitiveHeaderUsage)
{
    FileMap map = {
        {"/a.h", "void f();"},
        {"/b.h", "#include \"/a.h\""},
        {"/main.cpp", R"FILE(
#include "/b.h"

void f() { return; }
)FILE"}
    };

    auto IE = getImplementsRelationForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    auto& I = IE->getImplementationMap();
    ASSERT_EQ(I.size(), 1);
    ASSERT_EQ(I.count("/a.h"), 1);
    ASSERT_EQ(I.at("/a.h").size(), 1);
    ASSERT_EQ(I.at("/a.h").count("f"), 1);
}

TEST(FindImplementsRelation, ClassMethod)
{
    FileMap map = {
        {"/X.h", R"FILE(
class X
{
public:
  void f();
};
)FILE"},
        {"/main.cpp", R"FILE(
#include "/X.h"

void X::f() { return; }
)FILE"}
    };

    auto IE = getImplementsRelationForCompilation(
        map, "/main.cpp", TrivialCompileCommand);
    auto& I = IE->getImplementationMap();
    ASSERT_EQ(I.size(), 1);
    ASSERT_EQ(I.count("/X.h"), 1);
    ASSERT_EQ(I.at("/X.h").size(), 1);
    ASSERT_EQ(I.at("/X.h").count("f"), 1);
}
