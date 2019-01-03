#include <fstream>
#include <iostream>
#include <memory>
#include <string>

#include <clang/Tooling/CompilationDatabase.h>
#include <llvm/Support/FileSystem.h>

#include "Executor.h"
#include "ImplementsEdges.h"
#include "Replacement.h"
#include "threadpool.h"

using namespace clang;
using namespace clang::tooling;
using namespace llvm::sys::fs;
using namespace SymbolRewriter;
using namespace whisperity;

/**
 * TODO: Document the whole tool.
 */
int main(int argc, const char** argv)
{
    if (argc < 2 || argc > 3)
    {
        std::cerr << "usage: " << argv[0] <<
                  " <build folder> [thread count]" <<
                  std::endl;
        std::cerr << "\t'thread-count' will be 1 by default." << std::endl;
        return 2;
    }

    if (argc >= 2 && strncmp(argv[1], "--version", 10) == 0)
    {
        std::cerr << "SymbolRewriter vX.Y.Z" << std::endl;
        return 0;
    }

    // ------------------- Configure the arguments' defaults -------------------
    const StringRef BuildFolder = argv[1];

    if (!is_directory(BuildFolder))
    {
        std::cerr << "ERROR! Specified build folder '" << BuildFolder.data() <<
                  "' is not a directory!" << std::endl;
        return 1;
    }

    size_t ThreadCount = 1;
    if (argc >= 3)
        ThreadCount = std::stoull(argv[2]);

    // ------------------------- Initialise the system -------------------------
    std::unique_ptr<CompilationDatabase> CompDb;
    {
        std::string LoadError;
        CompDb = CompilationDatabase::loadFromDirectory(BuildFolder, LoadError);
        if (!CompDb)
        {
            std::cerr << "Couldn't read compilation database, because:" <<
                      std::endl;
            std::cerr << '\t' << LoadError << std::endl;
            return 1;
        }
    }

    std::cout << "Using " << ThreadCount << " threads..." << std::endl;
    auto Threading = make_thread_pool<ToolExecution>(ThreadCount,
        [](auto& Execution)
        {
            ToolResult ToolResult = Execution();
            if (auto* RetCode = std::get_if<int>(&ToolResult))
            {
                std::cerr << "Error! Non-zero return code from Clang on file "
                          << Execution.filename() << ": " << *RetCode
                          << std::endl;
                return;
            }
            auto Results = std::get<UsefulResultType>(std::move(ToolResult));

            // Write the results.
            {
                std::string OutputFile =
                    Execution.filepathWithoutExtension()
                    .append(Execution.extension())
                    .append("-symbols.txt");
                std::ofstream OutputBuffer{OutputFile};
                if (OutputBuffer.fail())
                    std::cerr << "Can't write output for '"
                              << Execution.filepath()
                              << "' to file '" << OutputFile
                              << "' because the file never opened."
                              << std::endl;
                else
                    writeReplacementOutput(OutputBuffer, *Results.first);
            }

            {
                std::string OutputFile =
                    Execution.filepathWithoutExtension()
                        .append(Execution.extension())
                        .append("-implements.txt");
                std::ofstream OutputBuffer{OutputFile};
                if (OutputBuffer.fail())
                    std::cerr << "Can't write output for '"
                              << Execution.filepath()
                              << "' to file '" << OutputFile
                              << "' because the file never opened."
                              << std::endl;
                else
                    writeImplementsOutput(OutputBuffer, *Results.second);
            }
        });

    // ---------------------- Execute the FrontendActions ----------------------
    for (const std::string& File : CompDb->getAllFiles())
        Threading->enqueue(ToolExecution(*CompDb, File));

    // Wait the main thread until the processing is done.
    Threading->wait();
}
