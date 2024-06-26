#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>

#include <clang/Tooling/CompilationDatabase.h>
#include <llvm/Support/FileSystem.h>

#include <whisperity/ThreadsafeOStream.h>
#include <whisperity/threadpool.h>

#include "Executor.h"
#include "ImplementsEdges.h"
#include "Replacement.h"
#include "SymbolTableDump.h"

using namespace clang;
using namespace clang::tooling;
using namespace llvm::sys::fs;
using namespace SymbolAnalyser;
using namespace whisperity;

int main(int argc, const char** argv)
{
    if (argc < 2 || argc > 3 || std::strcmp(argv[1], "-h") == 0)
    {
        std::cerr << "usage: " << argv[0] << " <build folder> [thread count]"
                  << std::endl;
        std::cerr << "\t'thread-count' will be 1 by default." << std::endl;
        return 2;
    }

    if (argc >= 2 && strncmp(argv[1], "--version", 10) == 0)
    {
        std::cerr << argv[0] << " vX.Y.Z" << std::endl;
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

    SynchronisedFiles ThreadsafeFileAccess;

    std::cout << "Using " << ThreadCount << " threads..." << std::endl;
    auto Threading = make_thread_pool<ToolExecution>(ThreadCount,
        [&ThreadsafeFileAccess](auto& Execution)
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
                std::string OutputFile = std::string(Execution.filepath())
                    .append("-badsymbols.txt");
                std::ofstream OutputBuffer{OutputFile};
                if (OutputBuffer.fail())
                    std::cerr << "Can't write BAD SYMBOLS output for '"
                              << Execution.filepath()
                              << "' to file '" << OutputFile
                              << "' because the file never opened."
                              << std::endl;
                else
                    writeReplacementOutput(OutputBuffer,
                                           *std::get<0>(Results));
            }
            {
                std::string OutputFile = std::string(Execution.filepath())
                    .append("-implements.txt");
                std::ofstream OutputBuffer{OutputFile};
                if (OutputBuffer.fail())
                    std::cerr << "Can't write IMPLEMENTS output for '"
                              << Execution.filepath()
                              << "' to file '" << OutputFile
                              << "' because the file never opened."
                              << std::endl;
                else
                    writeImplementsOutput(OutputBuffer,
                                          *std::get<1>(Results));
            }

            // The symbol table outputs may collide between files and should be
            // accessed threadsafe.
            const SymbolTableDump* STD = std::get<2>(Results).get();
            for (const std::string& Filename : STD->getKnownFiles())
            {
                {
                    std::string OutputFile = std::string(Filename)
                        .append("-definitions.txt");
                    SynchronisedFiles::SynchronisedFile File =
                        ThreadsafeFileAccess.open(OutputFile);
                    std::ostream& OutputBuffer = File();
                    if (OutputBuffer.fail())
                        std::cerr << "Can't write DEFINITION output for '"
                                  << Execution.filepath()
                                  << "' to file '" << OutputFile
                                  << "' because the file never opened."
                                  << std::endl;
                    else
                        writeSymbolDefinitionsOutput(OutputBuffer,
                                                     Filename,
                                                     *std::get<2>(Results));
                }

                {
                    std::string OutputFile = std::string(Filename)
                        .append("-forwarddeclarations.txt");
                    SynchronisedFiles::SynchronisedFile File =
                        ThreadsafeFileAccess.open(OutputFile);
                    std::ostream& OutputBuffer = File();
                    if (OutputBuffer.fail())
                        std::cerr << "Can't write FORWARD DECLARATION output "
                                     "for '"
                                  << Execution.filepath()
                                  << "' to file '" << OutputFile
                                  << "' because the file never opened."
                                  << std::endl;
                    else
                        writeSymbolForwardDeclarationsOutput(
                            OutputBuffer, Filename, *std::get<2>(Results));
                }
            }
        });

    // ---------------------- Execute the FrontendActions ----------------------
    for (const std::string& File : CompDb->getAllFiles())
        Threading->enqueue(ToolExecution(*CompDb, File));

    // Wait the main thread until the processing is done.
    Threading->wait();
}
