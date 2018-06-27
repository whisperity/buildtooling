To build the dummy project with Bazel, `cd` into the project directory, e.g.
`stage3`.

Then execute: `bazel build //main:hello-world`. This will produce a build.

To use a cache and see some minor statistics about it, say:

    bazel build --disk_cache=~/.bazelc //main:hello-world \
      --verbose_failures --sandbox_debug --spawn_strategy=sandboxed
