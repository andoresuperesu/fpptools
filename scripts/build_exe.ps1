# Build standalone exes in dist_exe\ (no Python needed on the target PC). dist\ is left for the PyPI
# wheel/sdist (uv build / uv publish), which uploads everything in dist\.
#   fpptools.exe              full command line
#   fpptools_estructuras.exe  double-click: estructuras.xlsx next to the exe
# Run from the repo root:  .\scripts\build_exe.ps1
$ErrorActionPreference = "Stop"
uv sync --group build
foreach ($exe in @(@("fpptools", "scripts\exe_fpptools.py"), @("fpptools_estructuras", "scripts\exe_estructuras.py"))) {
    uv run --group build pyinstaller --onefile --console --name $exe[0] --paths . --distpath dist_exe --clean --noconfirm $exe[1]
}
Write-Host "Built dist_exe\fpptools.exe and dist_exe\fpptools_estructuras.exe"
