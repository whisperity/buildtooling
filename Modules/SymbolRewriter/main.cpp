#include <iostream>
#include <memory>
#include <string>

#include <clang/Frontend/FrontendActions.h>
#include <clang/Tooling/CompilationDatabase.h>
#include <clang/Tooling/Tooling.h>

#include <llvm/Support/FileSystem.h>

using namespace clang;
using namespace clang::tooling;
using namespace llvm::sys::fs;

int main(int argc, const char** argv)
{
    if (argc < 2 || argc > 3)
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
    std::string OutputPath;
    if (!is_directory(BuildFolder))
    {
        std::cerr << "ERROR! Specified build folder '" << BuildFolder.data() <<
                  "' is not a directory!" << std::endl;
        return 1;
    }

    if (argc == 2)
        OutputPath = BuildFolder.str() + "/implements.dat";
    else
        OutputPath = argv[2];

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

    // ----------------------- Execute the FrontendAction ----------------------
    ClangTool Tool(*CompDb, CompDb->getAllFiles());
    return Tool.run(newFrontendActionFactory<DeclContextPrintAction>().get());
}
