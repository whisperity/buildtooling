#!/usr/bin/env python3
"""
"""

import argparse
import atexit
import codecs
import itertools
import json
import os
import shlex
import subprocess
import sys

if __name__ != '__main__':
  raise NotImplementedError("This module is meant to be used as an entry point"
                            " application, not via imports.")

# ----------------------------------------------------------------------------
#     Arguments
# ----------------------------------------------------------------------------
parser = argparse.ArgumentParser()

parser.add_argument(
  "build_json",
  type=str,
  help="Path to the compilation database to use.")

args = parser.parse_args()

# ----------------------------------------------------------------------------
#     Module state.
# ----------------------------------------------------------------------------
# Stores the execution's progress so that it can always be output on the
# command-line.
CURRENT_PROGRESS = -1

# The total amount of progress "ticks" the code will take when executing.
TOTAL_PROGRESS = -1

# A rolling number that helps creating a visual ticker on the progress bar.
PROGRESS_TICKER_COUNT = 0

# ----------------------------------------------------------------------------
#     Function definitions.
# ----------------------------------------------------------------------------


TICKER = itertools.cycle(['-', '/', '|', '\\'])


def console_width():
  """
  """

  _, length = os.popen('stty size', 'r').read().split()
  return int(length)


def set_progress(total, current = 0):
  """
  Set the progress bar progress value to be the total, and optionally the given
  current. This function does not draw the bar again!
  """
  global CURRENT_PROGRESS, TOTAL_PROGRESS
  CURRENT_PROGRESS = max(0, min(current, total))
  TOTAL_PROGRESS = total


def step_progress(inc = 1):
  """
  Increases the progress bar's progress value (does not draw a bar) by the
  given amount.
  """
  global CURRENT_PROGRESS
  CURRENT_PROGRESS = max(0, min(CURRENT_PROGRESS + inc, TOTAL_PROGRESS))


def has_progress():
  """
  Returns whether the current state has an ongoing progress set.
  """
  return CURRENT_PROGRESS > -1 and TOTAL_PROGRESS > -1 and \
         CURRENT_PROGRESS <= TOTAL_PROGRESS


def reset_progress():
  """
  """
  global CURRENT_PROGRESS, TOTAL_PROGRESS
  CURRENT_PROGRESS = -1
  TOTAL_PROGRESS = -1


def clear_progress_bar():
  """
  Clears the progress bar from the screen.
  """
  print('\r'.ljust(console_width()), end = '\r')


def print_progress_bar(#iteration, total,
                       prefix = '', suffix = '',
                       decimals = 1, length = -1,
                       fill = '█'):
    # (via https://stackoverflow.com/a/34325723/1428773)
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in
                                  percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """

    # Use values from the module state instead of argument.
    iteration = CURRENT_PROGRESS
    total = TOTAL_PROGRESS

    percent = ("{0:." + str(decimals) + "f}"). \
              format(100 * (iteration / float(total)))

    ticker = next(TICKER) if iteration < total else '*'

    if not length or length == -1:
      # Get the width of the console automatically.
      # (via https://stackoverflow.com/a/943921/1428773)
      length = console_width()

      # Subtract some letters so that the left and right end of the bar and the
      # progress percentage can be shown without overflow.
      # (4 = 2 * 2: The "padding" on left and right end of the bar)
      # (4: the ticker, the % symbol and spaces at the end of the bar)
      boilerplate_length = len(prefix) + len(suffix) + 4 + len(percent) + 4
      length = length - boilerplate_length  # "actual length" of the bar itself

      # Make sure a 10% interval and the boilerplate is always visible even
      # if it looks ugly.
      length = max(length, boilerplate_length + 10)

    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)

    print('\r%s |%s| %s %s%% %s' % (prefix, bar, ticker, percent, suffix),
          end = '\r')


@atexit.register
def __atexit_keep_last_progress_bar():
  """
  Make sure the progress bar is not overwritten by the prompt after exit even
  if the progress has not concluded.
  """
  if has_progress():
    clear_progress_bar()
    print_progress_bar()
    print()


def print_message_with_progress(msg = ''):
  """
  """
  if not has_progress():
    # If there isn't a progress yet, just print the message.
    print(msg)
  else:
    if msg:
      # Clear the progress bar and print the message in its place, then print
      # the progress so that it appears as if messages were coming up above the
      # progress bar.
      clear_progress_bar()

      # Only print the message if there is something, otherwise only update
      # progress bar.
      print(msg)

    print_progress_bar()


def call_command(command, env=None, cwd=None):
  """
  Call an external command (binary) and return with (output, return_code).
  """
  try:
    out = subprocess.check_output(command,
                                  bufsize=-1,
                                  env=env,
                                  stderr=subprocess.STDOUT,
                                  cwd=cwd)
    return out, 0
  except subprocess.CalledProcessError as ex:
    print("Running command '%s' failed: %d, %s"
          % (' '.join(command), ex.returncode, ex.output),
          file=sys.stderr)
    return ex.output, ex.returncode
  except OSError as oerr:
    print("Standard error happened when running command '%s': %s."
          % (' '.join(command), str(oerr)),
          file=sys.stderr)
    return oerr.strerror, oerr.errno


# >>>> From CodeChecker's source code:
#      http://github.com/Ericsson/codechecker
#
#      https://github.com/Ericsson/codechecker/blob/master
#             /libcodechecker/analyze/analysis_manager.py
# <<<<
def create_dependencies(command, build_dir):
    """
    Transforms the given original build 'command' to a command that, when
    executed, is able to generate a dependency list (list of headers included
    in the build).
    """

    def __eliminate_argument(arg_vect, opt_string, has_arg=False):
        """
        This call eliminates the parameters matching the given option string,
        along with its argument coming directly after the opt-string if any,
        from the command. The argument can possibly be separated from the flag.
        """
        while True:
            option_index = next(
                (i for i, c in enumerate(arg_vect)
                 if c.startswith(opt_string)), None)

            if option_index:
                separate = 1 if has_arg and \
                    len(arg_vect[option_index]) == len(opt_string) else 0
                arg_vect = arg_vect[0:option_index] + \
                    arg_vect[option_index + separate + 1:]
            else:
                break

        return arg_vect

    if 'CC_LOGGER_GCC_LIKE' not in os.environ:
        os.environ['CC_LOGGER_GCC_LIKE'] = 'gcc:g++:clang:clang++:cc:c++'

    if any(binary_substring in command[0] for binary_substring
           in os.environ['CC_LOGGER_GCC_LIKE'].split(':')):
        # gcc and clang can generate makefile-style dependency list.

        # If an output file is set, the dependency is not written to the
        # standard output but rather into the given file.
        # We need to first eliminate the output from the command.
        command = __eliminate_argument(command, '-o', True)
        command = __eliminate_argument(command, '--output', True)

        # Remove potential dependency-file-generator options from the string
        # too. These arguments found in the logged build command would derail
        # us and generate dependencies, e.g. into the build directory used.
        command = __eliminate_argument(command, '-MM')
        command = __eliminate_argument(command, '-MF', True)
        command = __eliminate_argument(command, '-MP')
        command = __eliminate_argument(command, '-MT', True)
        command = __eliminate_argument(command, '-MQ', True)
        command = __eliminate_argument(command, '-MD')
        command = __eliminate_argument(command, '-MMD')

        # Clang contains some extra options.
        command = __eliminate_argument(command, '-MJ', True)
        command = __eliminate_argument(command, '-MV')

        # Build out custom invocation for dependency generation.
        command = [command[0], '-E', '-M', '-MT', '__dummy'] + command[1:]

        # Remove empty arguments
        command = [i for i in command if i]

        # gcc does not have '--gcc-toolchain' argument it would fail if it is
        # kept there.
        # For clang it does not change the output, the include paths from
        # the gcc-toolchain are not added to the output.
        command = __eliminate_argument(command, '--gcc-toolchain')

        output, rc = call_command(command,
                                  env=os.environ,
                                  cwd=build_dir)
        output = codecs.decode(output, 'utf-8', 'replace')
        if rc == 0:
            # Parse 'Makefile' syntax dependency output.
            dependencies = output.replace('__dummy: ', '') \
                .replace('\\', '') \
                .replace('  ', '') \
                .replace(' ', '\n')

            # The dependency list already contains the source file's path.
            return [dep for dep in dependencies.split('\n') if dep != ""]
        else:
            raise IOError("Failed to generate dependency list for " +
                          ' '.join(command) + "\n\nThe original output was: " +
                          output)
    else:
        raise ValueError("Cannot generate dependency list for build "
                         "command '" + ' '.join(command) + "'")

# ----------------------------------------------------------------------------
#     Entry point.
# ----------------------------------------------------------------------------


def __main():
  """
  The main business logic of the current module.
  """

  try:
    with open(args.build_json, 'r') as handle:
      compilations = json.load(handle)
  except OSError as e:
    print("Error! Cannot open file '%s': %s." % (args.build_json, str(e)),
          file=sys.stderr)
    sys.exit(1)

  print("%d entries in the compilation database." % (len(compilations)))

  header_inclusion_count = {}
  tu_include_count = {}
  tu_compilation_count = {}

  set_progress(len(compilations), 0)

  num_success, num_failure, num_skipped = 0, 0, 0

  for command in compilations:
    f = command['file']

    step_progress()
    print_message_with_progress()

    if f.endswith(('.o', '.so', '.a', '.lib', '.exe', '.dll', '.sys',
                   '.out')):
      print_message_with_progress("Skipping non-compilation input: '%s'"
                                  % f)
      num_skipped = num_skipped + 1
      continue

    try:
      headers_needed = create_dependencies(shlex.split(command['command']),
                                           command['directory'])
    except:
      print_message_with_progress("Couldn't generate dependency list for '%s'"
                                  % f)
      num_failure = num_failure + 1
      continue

    # Subtract the main file from the inclusion list to not skew the statistics.
    headers_included = set([os.path.abspath(h) for h in headers_needed
                            if h != f])

    # Calculate inclusion and compilation counts.
    for h in headers_included:
      header_inclusion_count[h] = \
        header_inclusion_count[h] + 1 if h in header_inclusion_count \
        else 1

    tu_include_count[f] = \
      tu_include_count[f] + len(headers_included) \
      if f in tu_include_count \
      else len(headers_included)

    tu_compilation_count[f] = tu_compilation_count[f] + 1 \
      if f in tu_compilation_count \
      else 1

    num_success = num_success + 1

  reset_progress()
  clear_progress_bar()

  print("    %d total,    %d successfully handled,    %d failed,    %d skipped"
        % (len(compilations), num_success, num_failure, num_skipped))

  print("Calculated source file importancy metrics, writing result JSONs...")
  try:
    set_progress(3, 0)
    print_message_with_progress()

    with open('times-header-included-to-tu.json', 'w') as handle:
      json.dump(header_inclusion_count, handle,
                sort_keys = True, indent = 2)
    step_progress()
    print_message_with_progress()

    with open('headers-tu-includes.json', 'w') as handle:
      json.dump(tu_include_count, handle,
                sort_keys = True, indent = 2)
    step_progress()
    print_message_with_progress()

    with open('times-source-file-compiled.json', 'w') as handle:
      json.dump(tu_compilation_count, handle,
                sort_keys = True, indent = 2)
    step_progress()
    print_message_with_progress()
  except OSError as e:
    print("Error! Cannot open file '%s': %s." % (args.build_json, str(e)),
          file=sys.stderr)
    sys.exit(1)

  reset_progress()
  clear_progress_bar()


if __name__ == '__main__':
  try:
    __main()
  except KeyboardInterrupt:
    # Run the termination function of progress-bar clearing at a signal too.
    __atexit_keep_last_progress_bar()

