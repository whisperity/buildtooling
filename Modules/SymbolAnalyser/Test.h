#ifndef SYMBOLANALYSER_TEST_H
#define SYMBOLANALYSER_TEST_H

#include <string>
#include <vector>

#include <gtest/gtest.h>

#include "Executor.h"
#include "ImplementsEdges.h"
#include "Replacement.h"

using namespace SymbolAnalyser;

extern std::vector<std::string> TrivialCompileCommand;

/**
 * Helper function that fetches the actual result of rewrites/replacements
 * from the variant returned by ExecuteTool().
 */
std::unique_ptr<FileReplaceDirectives> getReplacementsForCompilation(
    const FileMap& FileMap,
    const std::string& Filename,
    const std::vector<std::string>& CompileCommand);

std::unique_ptr<ImplementsEdges> getImplementsRelationForCompilation(
    const FileMap& FileMap,
    const std::string& Filename,
    const std::vector<std::string>& CompileCommand);

bool positionFound(
    const std::vector<FileReplaceDirectives::Position>& PVec,
    size_t Line,
    size_t Col);

bool positionFound(
    const std::map<FileReplaceDirectives::Position,
                   FileReplaceDirectives::ReplacementPair>& RMap,
    size_t Line,
    size_t Col);

bool nameMatched(
    const std::map<FileReplaceDirectives::Position,
                   FileReplaceDirectives::ReplacementPair>& RMap,
    std::string Name);

bool nameMatchedAtPosition(
    const std::map<FileReplaceDirectives::Position,
                   FileReplaceDirectives::ReplacementPair>& RMap,
    std::string Name,
    size_t Line,
    size_t Col);

std::string getReplacementAt(
    const std::map<FileReplaceDirectives::Position,
                   FileReplaceDirectives::ReplacementPair>& RMap,
    size_t Line,
    size_t Col);

#endif // SYMBOLANALYSER_TEST_H
