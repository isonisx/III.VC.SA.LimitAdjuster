#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

rm -rf build
make -C mingw clangd -j"$(sysctl -n hw.logicalcpu)" "$@"
make -C mingw -j"$(sysctl -n hw.logicalcpu)" "$@"
