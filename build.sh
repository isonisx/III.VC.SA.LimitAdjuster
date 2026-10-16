#!/bin/bash
set -euo pipefail

LC_ALL=C make -C build config=debug -Bnw | bear parse-sh
make -C build config=release III.VC.SA.LimitAdjuster -j$(sysctl -n hw.logicalcpu)
