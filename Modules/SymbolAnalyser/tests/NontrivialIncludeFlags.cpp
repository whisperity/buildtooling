#include "Test.h"

TEST(NontrivialIncludeFlags, Test)
{
  FileMap map = {
      {"/include/root/myfunction.h", "void f();"},
      {"/main.cpp", R"FILE(
/* This #include is resolved from the compile command to /incldue/root! */
#include "myfunction.h"

void f() { return; }
)FILE"}
  };

  auto IE = getImplementsRelationForCompilation(
      map, "/main.cpp", NontrivialCompileCommand);
  ASSERT_NE(IE, nullptr);
  auto& I = IE->getImplementationMap();
  ASSERT_EQ(I.size(), 1);
  ASSERT_EQ(I.count("/include/root/myfunction.h"), 1);
  ASSERT_EQ(I.at("/include/root/myfunction.h").size(), 1);
  ASSERT_EQ(I.at("/include/root/myfunction.h").count("f"), 1);
}
