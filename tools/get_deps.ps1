# Baixa as dependências de build do plugin para C:\Users\TheoH\violino\deps (cada uma em sua pasta).
$ErrorActionPreference = "Stop"
$deps = "C:\Users\TheoH\violino\deps"
New-Item -ItemType Directory -Force $deps | Out-Null
$ProgressPreference = "SilentlyContinue"

if (-not (Test-Path "$deps\cmake\bin\cmake.exe")) {
    "cmake..."
    $zip = "$deps\cmake.zip"
    Invoke-WebRequest "https://github.com/Kitware/CMake/releases/download/v3.31.6/cmake-3.31.6-windows-x86_64.zip" -OutFile $zip
    Expand-Archive $zip "$deps\cmake_tmp" -Force
    Move-Item "$deps\cmake_tmp\cmake-3.31.6-windows-x86_64" "$deps\cmake"
    Remove-Item $zip, "$deps\cmake_tmp" -Recurse -Force
}

if (-not (Test-Path "$deps\JUCE\CMakeLists.txt")) {
    "juce..."
    git clone --depth 1 --branch 8.0.8 https://github.com/juce-framework/JUCE.git "$deps\JUCE"
}

if (-not (Test-Path "$deps\webview2\build")) {
    "webview2..."
    $pkg = "$deps\webview2.zip"
    Invoke-WebRequest "https://www.nuget.org/api/v2/package/Microsoft.Web.WebView2" -OutFile $pkg
    Expand-Archive $pkg "$deps\webview2" -Force
    Remove-Item $pkg
}

if (-not (Test-Path "$deps\VSCO-2-CE\.git")) {
    "vsco (sparse)..."
    git clone --depth 1 --filter=blob:none --sparse https://github.com/sgossner/VSCO-2-CE.git "$deps\VSCO-2-CE"
}
git -C "$deps\VSCO-2-CE" ls-tree -d --name-only HEAD
git -C "$deps\VSCO-2-CE" ls-tree -d --name-only HEAD:Strings
"done"
