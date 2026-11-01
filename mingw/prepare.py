#!/usr/bin/env python3
"""Generate MinGW compatibility copies; leave game and vendored sources intact."""
import re
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "build/mingw/gen"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != text:
        path.write_text(text)


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise SystemExit(f"Compatibility patch no longer matches: {old!r}")
    return text.replace(old, new)


def normalize(text):
    return re.sub(r'(#\s*include\s*["<])([^">]+)([">])',
                  lambda m: m[1] + m[2].replace('\\', '/') + m[3], text)


def sources():
    for path in sorted((ROOT / "source").iterdir()):
        if path.suffix not in (".cpp", ".h", ".inl"):
            continue
        text = normalize(path.read_text(encoding="utf-8-sig"))
        if path.name == "Pools.cpp":
            # Naked replay gates preserve all registers/flags and tail-jump to the
            # original function. Immediate operands let GCC resolve C++ symbols.
            for kind, target in (("Update", "replayUpdate"), ("Trigger", "replayTrigger")):
                pattern = rf'    __declspec\(naked\) void {kind}ReplayBridge\(\)\s*\{{\s*__asm\s*\{{.*?\n        \}}\n    \}}'
                bridge = f'''    __attribute__((naked)) void {kind}ReplayBridge()
    {{
        __asm__ volatile (
            "pushfl\\n\\t"
            "pushal\\n\\t"
            "call %c0\\n\\t"
            "testb %%al, %%al\\n\\t"
            "jz 1f\\n\\t"
            "popal\\n\\t"
            "popfl\\n\\t"
            "movl $0, %%eax\\n\\t"
            "ret\\n\\t"
            "1: popal\\n\\t"
            "popfl\\n\\t"
            "jmp *%c1\\n\\t"
            : : "i" (&SkipReplay), "i" (&{target}));
    }}'''
                text, count = re.subn(pattern, lambda _: bridge, text, flags=re.S)
                if count != 1:
                    raise SystemExit(f"Replay bridge patch no longer matches: {kind}")
        write(GEN / "source" / path.name, text)


def headers():
    base = ROOT / "external/FusionFixUtils/include"
    write(GEN / "compat/gameref.hpp", normalize((base / "gameref.hpp").read_text()))
    text = (base / "callbacks.h").read_text()
    for name, result in {
        "GetOnModuleLoadCallbackList": "std::map<std::wstring, std::function<void()>, Comparator>&",
        "GetOnModuleUnloadCallbackList": "std::map<std::wstring, std::function<void()>, Comparator>&",
        "GetOnAnyModuleLoadCallbackList": "std::vector<std::function<void(HMODULE)>>&",
        "GetOnAnyModuleUnloadCallbackList": "std::vector<std::function<void(std::wstring_view)>>&",
        "GetCallbackParamsList": "std::vector<ThreadParams>&",
        "GetCallbackParamsMutex": "std::recursive_mutex&",
    }.items():
        text = replace(text, f"static inline auto& {name}()", f"static inline {result} {name}()")
    text = replace(text, "LdrRegisterDllNotification(0, LdrDllNotification,",
                   "LdrRegisterDllNotification(0, reinterpret_cast<PVOID>(LdrDllNotification),")
    write(GEN / "compat/callbacks.h", normalize(text))


def patterns():
    text = (ROOT / "external/hooking/Hooking.Patterns.cpp").read_text()
    helper = '''#include <cstdint>
#include <limits>
// MinGW lacks MSVC SEH syntax. Stop at an unreadable page instead.
static bool PatternMemoryReadable(uintptr_t address, size_t size, uintptr_t& readableEnd)
{
    if (size > std::numeric_limits<uintptr_t>::max() - address)
        return false;
    const auto end = address + size;
    while (end > readableEnd)
    {
        MEMORY_BASIC_INFORMATION info{};
        const auto probe = address > readableEnd ? address : readableEnd;
        if (!VirtualQuery(reinterpret_cast<void*>(probe), &info, sizeof(info)) ||
            info.State != MEM_COMMIT || (info.Protect & (PAGE_GUARD | PAGE_NOACCESS)) ||
            !(info.Protect & (PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY |
                              PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY)))
            return false;
        const auto next = reinterpret_cast<uintptr_t>(info.BaseAddress) + info.RegionSize;
        if (next <= probe)
            return false;
        readableEnd = next;
    }
    return true;
}
'''
    text = replace(text, "#include <Windows.h>\n", "#include <Windows.h>\n" + helper)
    text = replace(text, '''\t__try
\t{
\t\tfor (uintptr_t i = executable.begin(), end = executable.end() - maskSize; i <= end;)
\t\t{
\t\t\tuint8_t* ptr = reinterpret_cast<uint8_t*>(i);''', '''\t\tuintptr_t readableEnd = 0;
\t\tfor (uintptr_t i = executable.begin(), end = executable.end() - maskSize; i <= end;)
\t\t{
\t\t\tif (!PatternMemoryReadable(i, maskSize, readableEnd)) break;
\t\t\tuint8_t* ptr = reinterpret_cast<uint8_t*>(i);''')
    text = replace(text, '''\t\t}
\t}
\t__except ((GetExceptionCode() == EXCEPTION_ACCESS_VIOLATION) ? EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH)
\t{
\t}
''', '\t\t}\n')
    write(GEN / "Hooking.Patterns.cpp", text)


def resources():
    for name in ("VersionInfo.rc", "VersionInfo.h"):
        write(GEN / "rc" / name, (ROOT / "resources" / name).read_text(encoding="utf-16"))
    now = datetime.now()
    sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    version = f"{now.day}.{now.month}.{now.year}"
    defines = {
        "rsc_CompanyName": '"ThirteenAG"',
        "rsc_LegalCopyright": '"MIT License"',
        "rsc_InternalName": '"III.VC.SA.LimitAdjuster"',
        "rsc_ProductName": '"III.VC.SA.LimitAdjuster"',
        "rsc_OriginalFilename": '"III.VC.SA.LimitAdjuster.asi"',
        "rsc_FileDescription": '"Open Limit Adjuster for GTA III, Vice City and San Andreas"',
        "rsc_UpdateUrl": '"https://github.com/GTAmodding/III.VC.SA.LimitAdjuster"',
        "rsc_FileVersion_MAJOR": str(now.day),
        "rsc_FileVersion_MINOR": str(now.month),
        "rsc_FileVersion_BUILD": str(now.year),
        "rsc_FileVersion_REVISION": str(now.hour * 100 + now.minute),
        "rsc_FileVersion": f'"{version}"',
        "rsc_ProductVersion": f'"{version}.{now.hour * 100 + now.minute}-{sha}"',
        "rsc_GitSHA1": f'"{sha}"',
        "rsc_GitSHA1W": f'L"{sha}"',
    }
    write(GEN / "rc/OpenLA.rc", '\n'.join(f'#define {k} {v}' for k, v in defines.items()) + '\n#include "VersionInfo.rc"\n')


if __name__ == "__main__":
    sources()
    headers()
    patterns()
    resources()
