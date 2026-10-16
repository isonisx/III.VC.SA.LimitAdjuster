#!/bin/bash
set -euo pipefail

rm -rf bin build .cache
rm -f compile_commands.json
premake5 gmake --file=premake5.lua
