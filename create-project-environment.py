#!/usr/bin/env python3
"""
"""

import argparse
import codecs
import os
import re
import shlex
import subprocess
import sys
import tempfile

if __name__ != '__main__':
  raise NotImplementedError("This module is meant to be used as an entry point"
                            " application, not via imports.")

# ----------------------------------------------------------------------------
#     Preparation phase to set up argument choices.
# ----------------------------------------------------------------------------
# Read the available data structure of the project to see what projects,
# compilers and configurations are allowed.
COMPILERS = []
BUILD_TOOLS = []
PROJECTS = []
PROJECT_CONFIGURATIONS = {}

for name in os.listdir("Dockerfile-Templates"):
  if name == "basics":
    # The default package can and should always be used.
    continue

  if name.startswith("UseCompiler-"):
    COMPILERS.append(name.replace("UseCompiler-", ""))
  elif name.startswith("Tooling-"):
    BUILD_TOOLS.append(name.replace("Tooling-", ""))
  elif name.startswith("Project-"):
    PROJECTS.append(name.replace("Project-", ""))

# ----------------------------------------------------------------------------
#     Arguments
# ----------------------------------------------------------------------------
parser = argparse.ArgumentParser(
  description="Creates a Docker image to test compiler toolings on projects.")

parser.add_argument('-c', '--compiler',
  dest="compiler",
  type=str,
  choices=COMPILERS,
  required=True,
  help="The compiler to use for compiling the project.")

parser.add_argument('-b', '-t', '--tool',
  dest="tool",
  type=str,
  choices=BUILD_TOOLS,
  default=None,
  help="The additional build tool to use aimed to enhance compilation "
       "experience.")

parser.add_argument('project',
  type=str,
  choices=PROJECTS,
  help="The project to build the test image for.")

conf_group = parser.add_mutually_exclusive_group()

conf_group.add_argument('-x', '--configuration',
  dest="configuration",
  type=str,
  default="default",
  help="The configuration (\"subproject\") to use with the given project. "
       "Every project can define their own list of possible configurations.")

conf_group.add_argument('-xs', '--list-configurations',
  dest="list_configurations",
  action='store_true',
  help="Instead of creating the environment, list the available "
       "configurations for the given compiler + project combination.")


# ----------------------------------------------------------------------------
#     Module state.
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
#     Function definitions.
# ----------------------------------------------------------------------------


def console_width():
  """
  """

  _, length = os.popen('stty size', 'r').read().split()
  return int(length)


def call_command(command, input_data=None, env=None, cwd=None):
  """
  Call an external command (binary) and return with (output, return_code).
  Optionally, send input_data in the process' STDIN.
  """
  try:
    proc = subprocess.Popen(command,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            bufsize=-1,
                            cwd=cwd,
                            env=env)
    out, _ = proc.communicate(input_data)
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


def execute(command, cwd=None):
  """
  Call an external comamnd and dump its output to the current output while it
  is running.
  """
  popen = subprocess.Popen(command,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT,
                           cwd=cwd,
                           universal_newlines=True)
  for stdout_line in iter(popen.stdout.readline, ""):
      yield stdout_line
  popen.stdout.close()

  return_code = popen.wait()
  if return_code:
      raise subprocess.CalledProcessError(return_code, command)


def preprocess_dockerfile(template_path, output_path, defines=None):
  """
  Preprocess the given Dockerfile at 'template_path' by executing the
  preprocessor as if the 'defines' dict's elements were defined.
  """
  defines = defines if defines else {}
  if type(defines) != dict:
    raise AttributeError("The 'defines' must be a dictionary.")

  define_args = []
  for key, value in defines.items():
    if value is True:
      define_args.append('-D' + key)
    elif value is False:
      define_args.append('-U' + key)
    else:
      define_args.append('-D' + key + '=' + shlex.quote(value))

  try:
    with open(template_path, 'r') as infile:
      contents = infile.read()

      # Dockerfiles can contain comments beginning with '#' which is also the
      # directive character for CPP. They need to be escaped first into
      # "C++-like" comments.
      contents = re.sub(r'#', r'//#', contents)

      # The C PreProcessor eliminates comments beginning with // which are
      # often found as links in the code.
      contents = contents.replace(r'//', r'\/\/')

      # We also need to "escape" line-ending \s as they would act as string
      # joining which mess up multi-line commands in Dockerfiles.
      # We insert a "^$" before the line break.
      contents = re.sub(r'\\\n', r'\^$\n', contents)

    output, _ = call_command(['cpp'] + define_args,
                               codecs.encode(contents, 'utf-8'))
    output = codecs.decode(output, 'utf-8', 'replace')

    # Now, turn the output back using the previous transformations.
    output = output.replace(r'\/\/', r'//')
    output = re.sub(r'\\\^\$\n', r'\\\n', output)
    output = re.sub(r'//#', r'#', output)

    with open(output_path, 'w') as handle:
      print('\n'.join([line for line in output.split('\n')
                       if not line.startswith('#')]),
            file=handle)
  except:
    print("Couldn't preprocess the Dockerfile template: %s" % template_path,
          file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)


def docker_build(folder, dockerfile, image_name):
  """
  Executes 'docker build' for the given Dockerfile.
  """

  try:
    for output_line in execute(['docker', 'build',
                                folder,
                                '--file', dockerfile,
                                '--tag', image_name],
                               cwd=folder):
      print(output_line, end='')
  except subprocess.CalledProcessError as ex:
    print("Calling 'docker build' failed!", file=sys.stderr)
    print(ex.output, file=sys.stderr)
    sys.exit(1)

# ----------------------------------------------------------------------------
#     Entry point.
# ----------------------------------------------------------------------------


def __main():
  """
  The main business logic of the current module.
  """

  args = parser.parse_args()
  os.chdir("Dockerfile-Templates")

  # Preprocess all the Dockerfiles in the chain and create the outputs that
  # can be built.
  execution_list = []
  execlist_to_image_name = {}
  collected_defines = {}

  tmp = tempfile.TemporaryDirectory()
  tmpdir = tmp.name

  def tempname(name):
    """
    This function creates the output name for the given 'image name' in the
    temporary folder, where the preprocessed result can be written.
    This value is returned.
    """
    return os.path.join(tmpdir, name) + ".Dockerfile"

  def map_execution(preprocessed_path, image_name):
    """
    Create a mapping between the output preprocessed path and the Docker image
    name (optionally with ":tag" in it).
    """
    execution_list.append(preprocessed_path)
    execlist_to_image_name[preprocessed_path] = image_name

  def execute_preprocess(template_root, image_name):
    """
    Executes the preprocessing of the Dockerfile under template_root and marks
    the image built from it to have the name(:tag) image_name.
    """
    # The "previous image" is the one that will be built directly before
    # the current one.
    collected_defines['PREVIOUS_IMAGE'] = \
      execlist_to_image_name[execution_list[-1]] if len(execution_list) > 0 \
      else False
    print("Preprocessing '%s' on top of image '%s'..."
          % (template_root, collected_defines['PREVIOUS_IMAGE']))

    output_file = tempname(image_name)
    map_execution(output_file, image_name)

    preprocess_dockerfile(os.path.join(template_root, 'Dockerfile'),
                          output_file,
                          collected_defines)

  # Create the image for the compiler first.
  execute_preprocess('basics', 'base-image')

  # Create the image that contains the user's selected compiler.
  execute_preprocess('UseCompiler-' + args.compiler,
                     'compiler-' + args.compiler)
  collected_defines['COMPILER_' + args.compiler] = True

  # Create the image that installs the selected compiler tool.
  execute_preprocess('Tooling-' + args.tool,
                     'tool-' + args.tool)
  collected_defines['TOOL_' + args.tool] = True

  # Create the image that downloads the user's selected project.
  execute_preprocess('Project-' + args.project,
                     'project-' + args.project)

  for dockerfile in execution_list:
    image_name = execlist_to_image_name[dockerfile]
    print("Executing the build of '%s'..." % image_name)

    docker_build(tmpdir, dockerfile, image_name)

  # foo?
  input("You can inspect the temporary folder '%s' now.\nPress to exit! "
        % tmpdir)


if __name__ == '__main__':
  try:
    __main()
  except KeyboardInterrupt:
    # Run the termination function of progress-bar clearing at a signal too.
    __atexit_keep_last_progress_bar()

