#include "LockedFile.h"

#include <iostream>

namespace whisperity
{

LockedFile::LockedFile(std::string Path,
                       std::ios_base::openmode Mode,
                       std::ios_base::openmode ReopenMode)
    : Filepath(std::move(Path))
    , ReopenMode(ReopenMode)
    , MutexHeld(false)
    , AccessQueue(0)
{
    Stream.open(Filepath, Mode);
}

LockedFile::~LockedFile()
{
    Stream.close();
}

void LockedFile::open()
{
    if (Stream.is_open())
        return;

    std::lock_guard<std::mutex> Lock{StreamAccess};
    Stream.open(Filepath, ReopenMode);
}

void LockedFile::close()
{
    if (!Stream.is_open())
        return;

    std::lock_guard<std::mutex> Lock{StreamAccess};
    Stream.close();
}

SynchronisedFiles::SynchronisedFile
SynchronisedFiles::open(
    const std::string& Path,
    std::ios_base::openmode Mode,
    std::ios_base::openmode ReopenMode)
{
    std::lock_guard<std::mutex> Lock{MapAccess};
    auto It = FileMap.find(Path);
    if (It == FileMap.end())
        It = FileMap.try_emplace(Path, Path, Mode, ReopenMode).first;

    return SynchronisedFile(It->second);
}

SynchronisedFiles::SynchronisedFile::SynchronisedFile(LockedFile& FileEntry)
    : File(&FileEntry)
{
    // Opening a reference wrapper to the file means we want to access it.
    ++File->AccessQueue;
    File->open();
}

SynchronisedFiles::SynchronisedFile::~SynchronisedFile()
{
    if (!File)
        // If moved from, don't do anything.
        return;

    if (File->MutexHeld)
    {
        File->Stream.flush();
        File->MutexHeld = false;
        File->StreamAccess.unlock();
    }

    --File->AccessQueue;
    if (File->AccessQueue == 0)
        // Close the handle resource behind the file if no one wants access.
        File->close();

    File = nullptr;
}

SynchronisedFiles::SynchronisedFile::SynchronisedFile(
    SynchronisedFiles::SynchronisedFile&& RHS) noexcept
{
    File = RHS.File;
    RHS.File = nullptr;
}

SynchronisedFiles::SynchronisedFile&
SynchronisedFiles::SynchronisedFile::operator=(
    SynchronisedFiles::SynchronisedFile&& RHS) noexcept
{
    File = RHS.File;
    RHS.File = nullptr;
    return *this;
}

std::iostream& SynchronisedFiles::SynchronisedFile::operator()()
{
    // Acquire the file's resource lock. (The handle itself has opened by ctor.)
    File->StreamAccess.lock(); // Blocking call!
    File->MutexHeld = true;

    return File->Stream;
}

} // namespace whisperity
