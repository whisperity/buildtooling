#!/usr/bin/env python3
"""
"""

import argparse
import codecs
import os
import random
import re
import shlex
import shutil
import subprocess
import string
import sys
import tempfile

if __name__ != '__main__':
  raise NotImplementedError("This module is meant to be used as an entry point"
                            " application, not via imports.")

# ----------------------------------------------------------------------------
#     Preparation phase to set up argument choices.
# ----------------------------------------------------------------------------

DOCKERFILES_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                  'Dockerfiles')

# Read the available data structure of the project to see what projects,
# compilers and configurations are allowed.
COMPILERS = []
BUILD_TOOLS = []
PROJECTS = []
PROJECT_CONFIGURATIONS = {}

for name in os.listdir(DOCKERFILES_FOLDER):
  if name == 'basics':
    continue

  folder = os.path.join(DOCKERFILES_FOLDER, name)

  if os.path.isdir(folder) and \
        not os.path.isfile(os.path.join(folder, 'Dockerfile')):
    print("Invalid package in data structure, '%s' contains no Dockerfile."
          % name, file=sys.stderr)
    continue

  if name.startswith("UseCompiler-"):
    COMPILERS.append(name.replace("UseCompiler-", ""))
  elif name.startswith("Tooling-"):
    BUILD_TOOLS.append(name.replace("Tooling-", ""))
  elif name.startswith("Project-"):
    project = name.replace("Project-", '')
    PROJECTS.append(project)
    PROJECT_CONFIGURATIONS[project] = []

    for configuration in os.listdir(os.path.join(DOCKERFILES_FOLDER, name)):
      if configuration == 'Dockerfile':
        continue

      conf_folder = os.path.join(folder, configuration)

      if os.path.isdir(conf_folder):
        if not os.path.isfile(os.path.join(conf_folder, 'Dockerfile')):
          print("Invalid package in data structure, configuration '%s' for "
                "project '%s' contains no Dockerfile."
                % (configuration, name), file=sys.stderr)
          continue

        PROJECT_CONFIGURATIONS[project].append(configuration)

    if not PROJECT_CONFIGURATIONS[project]:
        # Always allow a "none" configuration to exist if the user did not
        # specify anything else. In this case, only the project's root script
        # will be preprocessed.
        PROJECT_CONFIGURATIONS[project] = ['none']


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
       "configurations for the given project.")


# ----------------------------------------------------------------------------
#     Module state.
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
#     Function definitions.
# ----------------------------------------------------------------------------


def replace_randomise(occurrence):
  """
  Handles the '#randomise' preprocessor pseudo-directive that defines the
  argument macro to a random value at preprocessing time.

  :note: This randomisation is NOT cryptographically secure!
  """
  rand = ''.join(random.choice(string.ascii_lowercase + string.digits)
                 for _ in range(16))
  return ''.join(["#define ", occurrence.group(1), " ", rand])


def call_command(command, input_data=None, env=None, cwd=None):
  """
  Call an external command (binary) and return with (output, return_code).
  Optionally, send input_data in the process' STDIN.
  """
  try:
    proc = subprocess.Popen(command,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            bufsize=-1,
                            cwd=cwd,
                            env=env)
    out, err = proc.communicate(input_data)

    return_code = proc.wait()
    if return_code:
      raise subprocess.CalledProcessError(return_code, command, out, err)

    return out, 0
  except subprocess.CalledProcessError as ex:
    print("Running command '%s' failed: %d"
          % (' '.join(command), ex.returncode),
          file=sys.stderr)
    return ex.stderr, ex.returncode
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
  proc = subprocess.Popen(command,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=cwd,
                          universal_newlines=True)
  for stdout_line in iter(proc.stdout.readline, ""):
      yield stdout_line
  proc.stdout.close()

  return_code = proc.wait()
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

      # If the Dockerfile contains the pseudo-macro `#depends`, it means the
      # file specified in this directive shall be copied to the preprocess
      # folder for 'docker build' to take.
      for dependent in \
          re.finditer(r'^#depends "(.+)"', contents, re.MULTILINE):
        try:
          fname = dependent.group(1)
          source_path = os.path.join(os.path.dirname(template_path), fname)
          destination_folder = os.path.join(os.path.dirname(output_path),
                                            os.path.dirname(fname))

          #os.makedirs(destination_folder, exist_ok=True)
          shutil.copy(source_path, os.path.join(destination_folder, fname))

          print("  > Copied dependent file '%s'." % fname)
        except Exception as e:
          print("Failed to copy dependent file '%s'" % fname, file=sys.stderr)
          print(str(e), file=sys.stderr)
          raise

      # Handles the preprocessor pseudo-directive that defines a given macro
      # to some random value. A line of "#randomise X" equals to the real
      # preprocessor directive "#define X --random--" where the random part
      # is generated at preprocessing time.
      # This is replaced with a random value at every preprocessing of the
      # file, turning off the ability for Docker to cache the build.
      contents = re.sub(r'^#randomise (.*)$', replace_randomise, contents,
                        flags=re.MULTILINE)

      # Cut these pseudo-preprocessor directives to not confuse the real
      # preprocessor.
      contents = re.sub(r'^#depends "(.+)"$', r'', contents,
                        flags=re.MULTILINE)

      # Dockerfiles can contain comments beginning with '#' which is also the
      # directive character for CPP. They need to be escaped first into
      # "C++-like" comments. However, at this point, we rule that "Dockerfile
      # comments" have to have a space after the #, but preprocessor directives
      # must not.
      contents = re.sub(r'# ', r'//# ', contents)

      # The C PreProcessor eliminates comments beginning with // which are
      # often found as links in the code.
      contents = contents.replace(r'//', r'\/\/')

      # We also need to "escape" line-ending \s as they would act as string
      # joining which mess up multi-line commands in Dockerfiles.
      # We insert a "^$" before the line break.
      contents = re.sub(r'\\\n', r'\^$\n', contents)

    output, ret = call_command(['cpp'] + define_args,
                               codecs.encode(contents, 'utf-8'))
    output = codecs.decode(output, 'utf-8', 'replace')
    if ret != 0:
      print("The preprocessing failed, because the preprocessor gave the "
            "error:", file=sys.stderr)
      print("", file=sys.stderr)
      print(output, file=sys.stderr)
      raise Exception("Preprocessor exited with error code %d" % ret)

    # Now, turn the output back using the previous transformations.
    output = output.replace(r'\/\/', r'//')
    output = re.sub(r'\\\^\$\n', r'\\\n', output)
    output = re.sub(r'//# ', r'# ', output)

    with open(output_path, 'w') as handle:
      # Strip wholly empty lines because sometimes the preprocessor cut some
      # conditional continuation from the original source.
      print('\n'.join([line for line in output.split('\n')
                       if line and not line.startswith('#')]),
            file=handle)
  except Exception as e:
    print("Couldn't preprocess the Dockerfile template: %s" % template_path,
          file=sys.stderr)
    print(str(e), file=sys.stderr)
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

  if args.list_configurations:
    print("Please note that the availability of the configuration itself "
          "does not mean that the configuration will successfully execute.\n"
          "Package creators can insert failure points to their configuration "
          "scripts to handle mismatches or incompatibilities!")
    print()
    print("Available configurations for '%s':" % args.project)
    for conf in PROJECT_CONFIGURATIONS[args.project]:
      print("    * %s" % conf)
    sys.exit(0)

  if PROJECT_CONFIGURATIONS[args.project] != ['none'] and \
          args.configuration not in PROJECT_CONFIGURATIONS[args.project]:
    print("Error: configuration '%s' is not available for project '%s'!"
          % (args.configuration, args.project),
          file=sys.stderr)
    print("Please use -xs/--list-configurations to see what is available.",
          file=sys.stderr)
    sys.exit(2)

  os.chdir(DOCKERFILES_FOLDER)

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
  collected_defines['COMPILER'] = args.compiler
  collected_defines['COMPILER_' + args.compiler] = True

  if args.tool:
    # Create the image that installs the selected compiler tool.
    execute_preprocess('Tooling-' + args.tool,
                       'tool-' + args.tool)
    collected_defines['TOOL'] = args.tool
    collected_defines['TOOL_' + args.tool] = True

  # Create the image that downloads the user's selected project.
  execute_preprocess('Project-' + args.project,
                     'project-' + args.project)

  # Now, create the project's configuration based on the user's request.
  if PROJECT_CONFIGURATIONS[args.project] != ['none']:
    execute_preprocess(os.path.join('Project-' + args.project,
                                    args.configuration),
                       args.project + '-' + args.configuration)

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
    sys.exit(130)

