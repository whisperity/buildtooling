#include <gtest/gtest.h>

#include <string>
#include <sstream>

#include "Replacement.h"

using namespace SymbolRewriter;

#define ADDR(x) reinterpret_cast<const void *>(x)

/**
 * Get a dummy replacer for a "main.cpp" file.
 */
FileReplaceDirectives getFRD()
{
    return FileReplaceDirectives{"main.cpp", "main"};
}

std::string getReplacementsAsString(const FileReplaceDirectives& FRD)
{
    std::ostringstream OSS;
    writeReplacementOutput(OSS, FRD);
    return OSS.str();
}

TEST(RenameWriting, Empty)
{
    ASSERT_EQ(getReplacementsAsString(getFRD()), "");
}

TEST(RenameWriting, Single)
{
    auto FRD = getFRD();
    FRD.SetReplacementBinding("Foo", nullptr);
    FRD.AddReplacementPosition(1, 1, "Foo", nullptr);

    ASSERT_EQ(getReplacementsAsString(FRD),
              "main.cpp##1:1##Foo##main_Foo\n");
}

TEST(RenameWriting, Multiple)
{
    auto FRD = getFRD();
    FRD.SetReplacementBinding("Foo", ADDR(1));
    FRD.SetReplacementBinding("Bar", ADDR(2));
    FRD.AddReplacementPosition(1, 1, "Foo", ADDR(1));
    FRD.AddReplacementPosition(2, 1, "Foo", ADDR(1));
    FRD.AddReplacementPosition(4, 1, "Bar", ADDR(2));

    // Replacing something to a different binding IS valid for the replacer,
    // but not a usual case.
    FRD.AddReplacementPosition(8, 20, "Foo", ADDR(2));

    std::string Expected = R"BUF(main.cpp##1:1##Foo##main_Foo
main.cpp##2:1##Foo##main_Foo
main.cpp##4:1##Bar##main_Bar
main.cpp##8:20##Foo##main_Bar
)BUF";

    ASSERT_EQ(getReplacementsAsString(FRD), Expected);
}
