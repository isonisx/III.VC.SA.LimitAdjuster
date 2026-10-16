#!/bin/bash
set -euo pipefail

rm -rf bin
rm -rf build
premake5 gmake --file=premake5.lua

