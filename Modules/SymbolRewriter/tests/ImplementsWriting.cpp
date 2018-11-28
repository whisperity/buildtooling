#include <gtest/gtest.h>

#include <string>
#include <sstream>

#include "ImplementsEdges.h"

using namespace SymbolRewriter;

/**
 * Get a dummy implements edge wrapper for a "main.cpp" file.
 */
ImplementsEdges getIE()
{
    return ImplementsEdges{"main.cpp"};
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
    IE.AddFileImplemented("header.h");

    ASSERT_EQ(getEdgesAsString(IE),
              "main.cpp##header.h\n");
}

TEST(ImplementsEdgeWriting, Multiple)
{
    auto IE = getIE();
    IE.AddFileImplemented("header.h");
    IE.AddFileImplemented("/usr/include/foo.h");

    ASSERT_EQ(getEdgesAsString(IE),
              R"BUF(main.cpp##/usr/include/foo.h
main.cpp##header.h
)BUF");
}
