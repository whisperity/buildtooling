#ifndef WHISPERITY_LOCKEDFILE_H
#define WHISPERITY_LOCKEDFILE_H

#include <atomic>
#include <fstream>
#include <map>
#include <mutex>

namespace whisperity
{

class SynchronisedFiles;

/**
 * Represents a wrapper over a file stream for managed thread-safe access.
 */
class LockedFile
{
public:
    /**
     * Creates a new LockedFile handle wrapper for the given file path and
     * original modes, and with the optional reopen mode...
     *
     * @param ReopenMode The file might be closed and later opened as access
     * to it is requested by client code. In that case, ReopenMode will be
     * used.
     */
    LockedFile(std::string Path,
               std::ios_base::openmode Mode,
               std::ios_base::openmode ReopenMode);
    ~LockedFile();

private:
    /**
     * (Re)opens the actual file stream.
     */
    void open();
    /**
     * Closes the actual file stream.
     */
    void close();

    friend class SynchronisedFiles;

    const std::string Filepath;
    std::ios_base::openmode ReopenMode;

    std::fstream Stream;
    std::atomic_bool MutexHeld;
    std::mutex StreamAccess;

    std::atomic_int AccessQueue;
};

class SynchronisedFiles
{
public:
    /**
     * A wrapper class over LockedFile which ties it to the synchroniser and
     * provides RAII-like operation to the client code.
     */
    class SynchronisedFile
    {
    public:
        /**
         * The class cannot be constructed arbitrarily.
         */
        SynchronisedFile() = delete;
        SynchronisedFile(const SynchronisedFile&) = delete;
        SynchronisedFile(SynchronisedFile&& RHS) noexcept;
        SynchronisedFile& operator=(const SynchronisedFile&) = delete;
        SynchronisedFile& operator=(SynchronisedFile&& RHS) noexcept;

        ~SynchronisedFile();

        /**
         * @return The actual file stream usable for I/O operations.
         * @note This stream MUST NOT be closed by external code! This operation
         * may block.
         */
        std::iostream& operator()();
    private:
        LockedFile* File;

        friend class SynchronisedFiles;
        SynchronisedFile(LockedFile& FileEntry);
    };

    SynchronisedFile open(const std::string& Path,
                          std::ios_base::openmode Mode = std::ios_base::in |
                                                         std::ios_base::out |
                                                         std::ios_base::trunc,
                          std::ios_base::openmode ReopenMode =
                              std::ios_base::in |
                              std::ios_base::out |
                              std::ios_base::app);

private:

    std::map<const std::string, LockedFile> FileMap;
    std::mutex MapAccess;
};

} // namespace whisperity

#endif // WHISPERITY_LOCKEDFILE_H
