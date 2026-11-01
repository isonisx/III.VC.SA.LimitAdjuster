# macOS host, 32-bit Windows target; Homebrew mingw-w64 (GCC 16).
HERE := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
ROOT := $(abspath $(HERE)/..)
CXX := i686-w64-mingw32-g++
CC := i686-w64-mingw32-gcc
RC := i686-w64-mingw32-windres
CONFIG ?= release
ifeq ($(CONFIG),debug)
CFG_FLAGS := -O0 -g -DDEBUG -D_DEBUG
RC_FLAGS := -D_DEBUG
else ifeq ($(CONFIG),release)
CFG_FLAGS := -O2 -g0 -DNDEBUG
else
$(error CONFIG must be release or debug)
endif
OUT := $(ROOT)/build/mingw/$(CONFIG)
GEN := $(ROOT)/build/mingw/gen
ASI := $(OUT)/III.VC.SA.LimitAdjuster.asi
INCLUDES := -I$(GEN)/source -I$(GEN)/compat \
 -I$(ROOT)/external/FusionFixUtils/include -I$(ROOT)/external/hooking \
 -I$(ROOT)/external/injector/include -I$(ROOT)/external/injector/safetyhook/include \
 -I$(ROOT)/external/injector/zydis
# Use 32-bit SSE arithmetic rather than x87 excess precision, as in the MSVC build.
CXXFLAGS := -std=c++23 -msse2 -mfpmath=sse -fms-extensions -Wno-unknown-pragmas \
 -D_CRT_SECURE_NO_WARNINGS -DNOMINMAX -DUNICODE -D_UNICODE $(CFG_FLAGS) $(INCLUDES)
CFLAGS := -msse2 -mfpmath=sse $(CFG_FLAGS) $(INCLUDES)
SOURCES := $(wildcard $(ROOT)/source/*.cpp)
SAFETYHOOK := $(wildcard $(ROOT)/external/injector/safetyhook/src/*.cpp)
OBJS := $(patsubst $(ROOT)/source/%.cpp,$(OUT)/source/%.o,$(SOURCES)) \
 $(patsubst $(ROOT)/external/injector/safetyhook/src/%.cpp,$(OUT)/safetyhook/%.o,$(SAFETYHOOK)) \
 $(OUT)/Hooking.Patterns.o $(OUT)/Zydis.o

.PHONY: all prepare build clangd clean
all: prepare
	$(MAKE) build CONFIG=$(CONFIG)
prepare:
	python3 $(HERE)/prepare.py
build: $(ASI)
clangd: prepare
	python3 $(HERE)/clangd.py

$(ASI): $(OBJS) $(OUT)/VersionInfo.res $(HERE)/Makefile
	$(CXX) -shared -static -static-libgcc -static-libstdc++ -Wl,--kill-at -Wl,--subsystem,windows -o $@ $(OBJS) $(OUT)/VersionInfo.res -lpsapi -lshell32 -lole32 -luuid -lshlwapi -luser32
ifeq ($(CONFIG),release)
	i686-w64-mingw32-strip --strip-debug $@
endif

$(OUT)/source/%.o: $(GEN)/source/%.cpp $(HERE)/Makefile
	@mkdir -p $(@D)
	$(CXX) $(CXXFLAGS) -MMD -MP -c $< -o $@
$(OUT)/safetyhook/%.o: $(ROOT)/external/injector/safetyhook/src/%.cpp $(HERE)/Makefile
	@mkdir -p $(@D)
	$(CXX) $(CXXFLAGS) -MMD -MP -c $< -o $@
$(OUT)/Hooking.Patterns.o: $(GEN)/Hooking.Patterns.cpp $(HERE)/Makefile
	@mkdir -p $(@D)
	$(CXX) $(CXXFLAGS) -MMD -MP -c $< -o $@
$(OUT)/Zydis.o: $(ROOT)/external/injector/zydis/Zydis.c $(HERE)/Makefile
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@
$(OUT)/VersionInfo.res: $(GEN)/rc/OpenLA.rc $(GEN)/rc/VersionInfo.rc $(GEN)/rc/VersionInfo.h $(HERE)/Makefile
	@mkdir -p $(@D)
	$(RC) $(RC_FLAGS) -I$(GEN)/rc -O coff -o $@ $<

-include $(OBJS:.o=.d)
clean:
	rm -rf $(ROOT)/build/mingw $(ROOT)/build/clangd
