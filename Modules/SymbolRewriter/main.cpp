#include <iostream>
#include <memory>
#include <string>

#include <clang/Tooling/CompilationDatabase.h>
#include <llvm/Support/FileSystem.h>

#include "Executor.h"
#include "Replacement.h"
#include "threadpool.h"

using namespace clang;
using namespace clang::tooling;
using namespace llvm::sys::fs;
using namespace SymbolRewriter;
using namespace whisperity;

int main(int argc, const char** argv)
{
    if (argc < 2 || argc > 4)
    {
        std::cerr << "usage: " << argv[0] <<
                  " <build folder> [output for 'implements' relation]" <<
                  std::endl;
        std::cerr << "\t'implements' relation output will be written in the "
                     "build folder by default." << std::endl;
        return 2;
    }

    // ------------------- Configure the arguments' defaults -------------------
    const StringRef BuildFolder = argv[1];

    if (!is_directory(BuildFolder))
    {
        std::cerr << "ERROR! Specified build folder '" << BuildFolder.data() <<
                  "' is not a directory!" << std::endl;
        return 1;
    }

    std::string OutputPath = BuildFolder.str() + "/implements.dat";
    size_t ThreadCount = 1;

    if (argc >= 3)
        OutputPath = argv[2];

    if (argc >= 4)
        ThreadCount = std::stoull(argv[3]);

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
            auto ToolResult = Execution.Execute();
            if (int* RetCode = std::get_if<int>(&ToolResult))
            {
                std::cerr << "Error! Non-zero return code from Clang on file "
                          << Execution.filename() << ": " << *RetCode
                          << std::endl;
                return;
            }

            auto Results = std::move(
                std::get<std::unique_ptr<FileReplaceDirectives>>(ToolResult));

            // TODO: Save these somewhere, somehow...
            Results->getReplacements();
        });

    // ----------------------- Execute the FrontendAction ----------------------
    for (const std::string& File : CompDb->getAllFiles())
        Threading->enqueue(ToolExecution(*CompDb, File));

    // Wait the main thread until the processing is done.
    Threading->wait();
}
