#!/usr/bin/env python3
"""
"""

import argparse
import atexit
import json
import os
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

# ----------------------------------------------------------------------------
#     Function definitions.
# ----------------------------------------------------------------------------

def has_progress():
  """
  """
  return CURRENT_PROGRESS > -1 and TOTAL_PROGRESS > -1 and \
         CURRENT_PROGRESS <= TOTAL_PROGRESS


def console_width():
  """
  """

  _, length = os.popen('stty size', 'r').read().split()
  return int(length)


def printProgressBar(iteration, total, prefix = '', suffix = '',
                     decimals = 1, length = -1, fill = '█'):
    # (via https://stackoverflow.com/a/34325723/1428773)
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """

    percent = ("{0:." + str(decimals) + "f}"). \
              format(100 * (iteration / float(total)))

    if not length or length == -1:
      # Get the width of the console automatically.
      # (via https://stackoverflow.com/a/943921/1428773)
      length = console_width()

      # Subtract some letters so that the left and right end of the bar and the
      # progress percentage can be shown without overflow.
      # (4 = 2 * 2: The "padding" on left and right end of the bar)
      # (2: the % symbol and space at the end of the bar)
      boilerplate_length = len(prefix) + len(suffix) + 4 + len(percent) + 2
      length = length - boilerplate_length  # "actual length" of the bar itself

      # Make sure a 10% interval and the boilerplate is always visible even
      # if it looks ugly.
      length = max(length, boilerplate_length + 10)

    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = '\r')
    # Print New Line on Complete.
    if iteration == total:
        print()


def __atexit_keep_last_progress_bar():
  """
  Make sure the progress bar is not overwritten by the prompt after exit even
  if the progress has not concluded.
  """
  if has_progress():
    print()


atexit.register(__atexit_keep_last_progress_bar)


def print_message(msg = ''):
  """
  """
  if not has_progress():
    # If there isn't a progress yet, just print the message.
    print(msg)
  else:
    # Clear the progress bar and print the message in its place, then print
    # the progress so that it appears as if messages were coming up above the
    # progress bar.
    print('\r'.ljust(console_width()), end = '\r')
    print(msg)

    printProgressBar(CURRENT_PROGRESS, TOTAL_PROGRESS)


# ----------------------------------------------------------------------------
#     Entry point.
# ----------------------------------------------------------------------------

try:
  with open(args.build_json, 'r') as handle:
    compilations = json.load(handle)
except OSError as e:
  print("Error! Cannot open file '%s': %s." % (args.build_json, str(e)),
        file=sys.stderr)
  sys.exit(1)

print("Running through %d entries in the compilation database."
      % (len(compilations)))

from time import sleep

TOTAL_PROGRESS = len(compilations)

sleep(2)
print_message("Foo")
sleep(2)
print_message("Bar")
sleep(2)
CURRENT_PROGRESS = 2
print_message("Bazqux")
sleep(2)
CURRENT_PROGRESS = 4
print_message("42")

# Make sure the final progress bar is not overwritten at all 
