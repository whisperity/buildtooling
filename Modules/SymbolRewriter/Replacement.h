#ifndef SYMBOLREWRITER_REPLACEMENT_H
#define SYMBOLREWRITER_REPLACEMENT_H

#include <iosfwd>
#include <map>
#include <string>
#include <vector>

namespace SymbolRewriter
{

/**
 * Contains the found and built replacement directives for a particular file.
 */
class FileReplaceDirectives
{
public:
    typedef std::pair<size_t, size_t> Position;
    typedef std::pair<std::string, std::string> ReplacementPair;

    /**
     * Creates a replacement holder for the file. The marked tokens will be
     * renamed to have 'RewritePrefix' in front of their name.
     */
    FileReplaceDirectives(std::string Filename,
                          std::string RewritePrefix);

    /**
     * Create a binding for the given ID that replaces the token From to a
     * generated token that prefixes 'RewritePrefix' in front of the name.
     *
     * @note The BindingID pointer is only used to identify the binding in the
     * internal structure of this type. The pointer is NOT dereferenced!
     */
    void SetReplacementBinding(std::string From,
                               const void* BindingID);

    /**
     * Mark the location 'AtLine:AtCol' in the file to have a replacement. The
     * token 'OfWhat' at the location will be considered a replacement according
     * to the BindingID.
     *
     * @note The BindingID pointer is only used to identify the binding in the
     * internal structure of this type. The pointer is NOT dereferenced!
     */
    void AddReplacementPosition(size_t AtLine,
                                size_t AtCol,
                                std::string OfWhat,
                                const void* BindingID);

    const std::string& getFilepath() const;

    /**
     * Retrieve the positions near where replacements should take place.
     */
    std::vector<Position> getReplacementPositions() const;

    /**
     * Retrieve the locations near where replacements should take place,
     * alongside with the actual strings to replace.
     */
    std::map<Position, ReplacementPair> getReplacements() const;

private:
    /**
     * Detail record that marks a particular position in the file where a given
     * string is to be replaced according to the binding pointed by the node
     * BindingID.
     */
    struct Replacement
    {
        const void* BindingID;
        size_t Line;
        size_t Col;
        std::string What;

        Replacement(size_t Line,
                    size_t Col,
                    std::string What,
                    const void* BindingID);
        Replacement(const Replacement&) = default;
        Replacement(Replacement&&) = default;
        Replacement& operator=(const Replacement&) = default;
        Replacement& operator=(Replacement&&) = default;
    };

    const std::string Filepath;
    const std::string RewritePrefix;
    std::map<const void*, ReplacementPair> Bindings;
    std::vector<Replacement> Replacements;

};

/**
 * Write the replacements formatted to the given output stream. This output
 * can be machine-read.
 */
void writeReplacementOutput(std::ostream& Output,
                            const FileReplaceDirectives& Directives);

} // namespace SymbolRewriter

#endif // SYMBOLREWRITER_REPLACEMENT_H
