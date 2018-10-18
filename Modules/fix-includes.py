#!/usr/bin/env python3

import os
import sys
from itertools import filterfalse, tee


if not os.path.isfile("CMakeLists.txt"):
  print("Error: this script should be run from a source folder.",
        file=sys.stderr)
  sys.exit(2)

sys.argv.extend([
  'xercesc/parsers/AbstractDOMParser.hpp',
  'xercesc/parsers/AbstractDOMParser.cpp'])

if len(sys.argv) != 3:
  print("Please specify a header and a source file!", file=sys.stderr)
  sys.exit(2)

def strip_current_folder(path):
  return os.path.abspath(path) \
         .replace(os.path.abspath(os.getcwd()), '') \
         .lstrip('/')

HEADER = strip_current_folder(sys.argv[1])
SOURCE = strip_current_folder(sys.argv[2])

if not os.path.isfile(HEADER) or not os.path.isfile(SOURCE):
  print("Error: The specified files are not files?", file=sys.stderr)

# First step to do is to concatenate the files, the CPP after the header.

def concatenate_files(files):
  if not files:
    return ""
  if not isinstance(files, list) or len(files) != 2:
    raise ValueError("The file array must be an array of [header, source].")

  content = """
// +*************************************************************************+
//   Begin header file '%s'
// +*************************************************************************+

""" % HEADER

  with open(HEADER, 'r') as hdr:
    content = hdr.read()

  content += """
// +*************************************************************************+
//   End header file '%s'
// +*************************************************************************+


// +*************************************************************************+
//   Begin implementation file '%s'
// +*************************************************************************+

""" % (HEADER, SOURCE)

  with open(SOURCE, 'r') as src:
    content += src.read()

  content += """
// +*************************************************************************+
//   End implementation file '%s'
// +*************************************************************************+

""" % SOURCE

  return content


result = concatenate_files([HEADER, SOURCE])

# Now rearrange the #include statements so all of them are on the top, and for
# easier rewriting to "import", in alphabetical order.

def partition(pred, iterable):
  """Partition an iterable to entries that pass or not pass a predicate."""
  it1, it2 = tee(iterable)
  return filterfalse(pred, it1), filter(pred, it2)


result_includes, result_nonincludes = partition(
  lambda line: not line.startswith("#include"),
  result.splitlines(True))

result_includes = sorted(result_includes)

result = ''.join(result_includes) + "\n\n" + ''.join(result_nonincludes)

print(result)