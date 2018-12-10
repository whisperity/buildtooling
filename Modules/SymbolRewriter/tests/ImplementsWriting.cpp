#include <gtest/gtest.h>

#include <string>
#include <sstream>

#include "ImplementsEdges.h"

using namespace SymbolRewriter;

/**
 * Get a dummy implements edge wrapper for a "/main.cpp" file.
 */
ImplementsEdges getIE()
{
    return ImplementsEdges{"/main.cpp"};
}

std::string getEdgesAsString(const ImplementsEdges& IE)
{
    std::ostringstream OSS;
    writeImplementsOutput(OSS, IE);
    return OSS.str();
}

TEST(ImplementsEdgeWriting, Empty)
{
    ASSERT_EQ(getEdgesAsString(getIE()), "");
}

TEST(ImplementsEdgeWriting, Single)
{
    auto IE = getIE();
    IE.AddImplemented("/header.h", "?");

    ASSERT_EQ(getEdgesAsString(IE),
              "/main.cpp##/header.h##?\n");
}

TEST(ImplementsEdgeWriting, Multiple)
{
    auto IE = getIE();
    IE.AddImplemented("/header.h", "X");
    IE.AddImplemented("/usr/include/foo.h", "foo::bar");

    std::string Expected = R"BUF(/main.cpp##/header.h##X
/main.cpp##/usr/include/foo.h##foo::bar
)BUF";

    ASSERT_EQ(getEdgesAsString(IE), Expected);
}
