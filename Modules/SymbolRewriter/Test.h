#ifndef SYMBOLREWRITER_TEST_H
#define SYMBOLREWRITER_TEST_H

#include <string>
#include <vector>

#include <gtest/gtest.h>

#include "Executor.h"
#include "Replacement.h"

using namespace SymbolRewriter;

extern std::vector<std::string> TrivialCompileCommand;

typedef std::unique_ptr<FileReplaceDirectives> UsableResult;

/**
 * Helper function that fetches the actual result from the variant returned
 * by ExecuteTool(). The function test-asserts that the Tool run properly.
 */
UsableResult getReplacementsForCompilation(
    const FileMap& FileMap,
    const std::string& Filename,
    const std::vector<std::string>& CompileCommand);

bool inPositionVector(
    const std::vector<FileReplaceDirectives::Position>& PVec,
    size_t Line,
    size_t Col);

#endif // SYMBOLREWRITER_TEST_H
