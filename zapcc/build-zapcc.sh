#!/bin/bash

echo "Start building Zap-CC..."

# It appears that one `make` invocation isn't enough to build...
make -k -j$(nproc) || echo "First 'make' attempt failed." >&2
make -k -j$(nproc) || echo "Second 'make' attempt failed." >&2
make -k -j$(nproc)

echo "Installing to system..."

make install

echo "Done."
