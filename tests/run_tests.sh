#!/bin/sh
# Builds ysfx (an open-source JSFX runtime) and runs the E4L JSFX tests without REAPER.
# Requires: git, cmake, g++, freetype/fontconfig dev libs, python3 + numpy.
set -e
cd "$(dirname "$0")"
[ -d build/ysfx ] || git clone --depth 1 --recursive https://github.com/jpcima/ysfx.git build/ysfx
[ -f build/ysfx/build/libysfx.a ] || (cmake -S build/ysfx -B build/ysfx/build -DCMAKE_BUILD_TYPE=Release -DYSFX_PLUGIN=OFF && cmake --build build/ysfx/build -j4)
g++ -O2 -std=c++17 runfx.cpp -Ibuild/ysfx/include build/ysfx/build/libysfx.a -lfreetype -lfontconfig -lpthread -ldl -o build/runfx
python3 test_e4l.py build/runfx
