To start the build with `distcc`, simply run builds like: `distcc g++ ...`, or
`CC="distcc" CXX="distcc" make ...`. With CMake, you can also set up the usage
of `distcc` with `-DCMAKE_<compiler>_COMPILER_LAUNCHER="distcc"` when
generating the build -- here, `<compiler>` is usually `C` or `CXX`.

`distcc-pump` mode has automatically been configured in the started shell.
