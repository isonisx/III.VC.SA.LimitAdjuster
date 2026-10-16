--[[
    OpenLA Build Script
    Use 'premake5 --help' for help
--]]

-- macOS host, 32-bit Windows target for the classic GTA games.
if os.host() ~= "macosx" then
    error("This build requires macOS and the i686-w64-mingw32 toolchain.")
end
if _ACTION and _ACTION ~= "gmake" and _ACTION ~= "gmake2" then
    error("Use premake5 gmake to generate the local cross-build.")
end
_OPTIONS["os"] = "windows"

--[[
    Options and Actions
--]]

newoption {
    trigger     = "outdir",
    value       = "path",
    description = "Output directory for the build files"
}
if not _OPTIONS["outdir"] then
    _OPTIONS["outdir"] = "build"
end

newoption {
    trigger     = "with-version",
    value       = "STRING",
    description = "Current version"
}


--[[
    The Solution
--]]
-- Put version strings in the generated resource instead of passing them through
-- both make's shell and windres's preprocessor shell (which strips their quotes).
local resourceDefines = {}
local function versionDefines(values)
    for _, value in ipairs(values) do
        local name, definition = value:match("^([^=]+)=(.*)$")
        table.insert(resourceDefines, "#define " .. name .. " " .. definition .. "\n")
    end
end

solution "OpenLA"

    configurations { "Release", "Debug" }
    system "windows"
    architecture "x86"
    toolset "gcc"
    gccprefix "i686-w64-mingw32-"
    cppdialect "C++17"
    -- Hooks use Intel-syntax x86 assembly and the games' four-byte stack alignment.
    buildoptions { "-fms-extensions", "-fpermissive", "-masm=intel", "-mno-sse", "-mno-sse2", "-mpreferred-stack-boundary=2", "-mincoming-stack-boundary=2" }
    linkoptions {
        "-static-libgcc", "-static-libstdc++",
        "-Wl,-Bstatic,--whole-archive", "-lwinpthread",
        "-Wl,-Bdynamic,--no-whole-archive"
    }

    location( _OPTIONS["outdir"] )
    targetprefix "" -- no 'lib' prefix on gcc
    targetdir "bin/%{cfg.buildcfg}"
    objdir "%{_OPTIONS.outdir}/obj/%{cfg.buildcfg}"
    
    versionDefines { "rsc_CompanyName=\"LimitAdjuster\"" }
    versionDefines { "rsc_LegalCopyright=\"MIT License\""}
    versionDefines { "rsc_InternalName=\"III.VC.SA.LimitAdjuster\"", "rsc_ProductName=\"III.VC.SA.LimitAdjuster\"", "rsc_OriginalFilename=\"III.VC.SA.LimitAdjuster.asi\"" }
    versionDefines { "rsc_FileDescription=\"This is a open source limit adjuster for Grand Theft Auto III, Vice City and San Andreas\"" }
    versionDefines { "rsc_UpdateUrl=\"https://github.com/ThirteenAG/III.VC.SA.LimitAdjuster\"" }

    local major = os.date("%d")
    local minor = os.date("%m")
    local build = os.date("%Y")
    local revision = os.date("%H") .. os.date("%M")

    if _OPTIONS["with-version"] then
        local t = {}
        for i in _OPTIONS["with-version"]:gmatch("([^.]+)") do
            t[#t + 1], _ = i:gsub("%D+", "")
        end
        while #t < 4 do t[#t + 1] = 0 end
        major    = math.min(tonumber(t[1]), 255)
        minor    = math.min(tonumber(t[2]), 255)
        build    = math.min(tonumber(t[3]), 65535)
        revision = math.min(tonumber(t[4]), 65535)
    end

    local githash = ""
    local f = io.popen("git rev-parse --short HEAD")
    if f then
        githash = f:read("*a"):gsub("%s+", "")
        f:close()
    end

    local productVersion = major .. "." .. minor .. "." .. build .. "." .. revision
    if githash ~= "" then
        productVersion = productVersion .. "-" .. githash
    end

    versionDefines { "rsc_FileVersion_MAJOR=" .. major }
    versionDefines { "rsc_FileVersion_MINOR=" .. minor }
    versionDefines { "rsc_FileVersion_BUILD=" .. build }
    versionDefines { "rsc_FileVersion_REVISION=" .. revision }
    versionDefines { "rsc_FileVersion=\"" .. major .. "." .. minor .. "." .. build .. "\"" }
    versionDefines { "rsc_ProductVersion=\"" .. productVersion .. "\"" }
    versionDefines { "rsc_GitSHA1=\"" .. githash .. "\"" }
    versionDefines { "rsc_GitSHA1W=L\"" .. githash .. "\"" }

    staticruntime "On"
    rtti "Off"
    useimportlib "Off"
    buffersecuritycheck "Off"

    defines {
        "INJECTOR_GVM_HAS_TRANSLATOR",
        'INJECTOR_GVM_PLUGIN_NAME=\"Open Limit Adjuster\"'    -- (additional quotes needed for gmake)
    }

    defines {
        "_CRT_SECURE_NO_WARNINGS",
        "_SCL_SECURE_NO_WARNINGS"
    }

    includedirs {
        "src",
        "src/shared",
        "src/shared/cpatch",
        "src/shared/structs",
    }

    filter "configurations:Debug*"
        symbols "On"
        defines { "DEBUG", "_DEBUG" }

    filter "configurations:Release*"
        defines { "NDEBUG" }
        optimize "Speed"

    filter {}

    project "III.VC.SA.LimitAdjuster"
        language "C++"
        kind "SharedLib"
        targetname "III.VC.SA.LimitAdjuster"
        targetextension ".asi"
        
        enablepch "Off"
        
        files {
            "src/**.cpp",
            "src/**.hpp",
            "src/**.h",
            "doc/**"
        }
        -- windres requires UTF-8 input; convert the resource and its header.
        local resource = path.join(_OPTIONS["outdir"], "Versioninfo.rc")
        if _ACTION then
            os.mkdir(_OPTIONS["outdir"])
            for _, name in ipairs { "Versioninfo.rc", "VersionInfo.h" } do
                local result = os.execute('iconv -f UTF-16 -t UTF-8 "src/resources/' .. name .. '" > "' .. path.join(_OPTIONS["outdir"], name) .. '"')
                if result ~= true and result ~= 0 then
                    error("Failed to convert " .. name .. " to UTF-8")
                end
            end
            local input = assert(io.open(resource, "rb"))
            local contents = input:read("*a")
            input:close()
            local output = assert(io.open(resource, "wb"))
            output:write(table.concat(resourceDefines), contents)
            output:close()
        end
        files { resource }
        resincludedirs { "src/resources" }
        removefiles { "src/sample/**" }
        
        
