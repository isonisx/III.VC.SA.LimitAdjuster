#!/usr/bin/env python3
"""Editor database for original files, with the build's compatibility copies overlaid."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "build/mingw/gen"
OUT = ROOT / "build/clangd"


def main():
    compiler = shutil.which("i686-w64-mingw32-g++")
    if not compiler:
        raise SystemExit("i686-w64-mingw32-g++ is not on PATH")
    OUT.mkdir(parents=True, exist_ok=True)
    mappings = [(ROOT / "source" / p.name, p) for p in sorted((GEN / "source").iterdir())]
    mappings += [(ROOT / "external/FusionFixUtils/include" / p.name, p)
                 for p in sorted((GEN / "compat").iterdir())]
    mappings.append((ROOT / "external/hooking/Hooking.Patterns.cpp", GEN / "Hooking.Patterns.cpp"))
    overlay = OUT / "headers.json"
    overlay.write_text(json.dumps({
        "version": 0,
        "use-external-names": False,
        "roots": [{"type": "file", "name": str(original), "external-contents": str(copy)}
                  for original, copy in mappings],
    }, indent=2) + "\n")
    includes = [ROOT / p for p in (
        "source", "external/FusionFixUtils/include", "external/hooking",
        "external/injector/include", "external/injector/safetyhook/include", "external/injector/zydis",
    )]
    flags = [
        "-std=c++23", "-msse2", "-mfpmath=sse", "-fms-extensions", "-Wno-unknown-pragmas",
        "-D_CRT_SECURE_NO_WARNINGS", "-DNOMINMAX", "-DUNICODE", "-D_UNICODE",
        "-O0", "-g", "-DDEBUG", "-D_DEBUG",
        *(f"-I{p}" for p in includes), "-ivfsoverlay", str(overlay),
    ]
    sources = sorted((ROOT / "source").glob("*.cpp"))
    sources += [ROOT / "external/hooking/Hooking.Patterns.cpp"]
    sources += sorted((ROOT / "external/injector/safetyhook/src").glob("*.cpp"))
    entries = [{"directory": str(ROOT), "file": str(p),
                "arguments": [compiler, *flags, "-c", str(p)]} for p in sources]
    zydis = ROOT / "external/injector/zydis/Zydis.c"
    entries.append({"directory": str(ROOT), "file": str(zydis), "arguments": [
        shutil.which("i686-w64-mingw32-gcc"), "-O0", "-g", f"-I{zydis.parent}", "-c", str(zydis),
    ]})
    database = OUT / "compile_commands.json"
    database.write_text(json.dumps(entries, indent=2) + "\n")
    print(f"clangd: {len(entries)} commands → {database}")


if __name__ == "__main__":
    main()
