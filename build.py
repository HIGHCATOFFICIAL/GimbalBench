#!/usr/bin/env python3
"""Build GimbalBench into a standalone executable using PyInstaller.

Usage:
    python build.py          # build for current platform
    python build.py --clean  # clean build artifacts first

Produces:
    dist/GimbalBench         (Linux/macOS executable)
    dist/GimbalBench.exe     (Windows executable)
"""
import subprocess
import shutil
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def clean():
    for d in ["build", "dist"]:
        path = os.path.join(HERE, d)
        if os.path.isdir(path):
            print(f"Removing {d}/")
            shutil.rmtree(path)
    spec = os.path.join(HERE, "GimbalBench.spec")
    if os.path.isfile(spec):
        os.remove(spec)


def build():
    sbgc_path = os.path.join(HERE, "Gimbal")
    if not os.path.isdir(os.path.join(sbgc_path, "sbgc")):
        print("ERROR: Gimbal submodule not found. Run: git submodule update --init")
        sys.exit(1)

    # Collect all sbgc submodules as hidden imports
    hidden = []
    sbgc_pkg = os.path.join(sbgc_path, "sbgc")
    for root, dirs, files in os.walk(sbgc_pkg):
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                rel = os.path.relpath(os.path.join(root, f), sbgc_path)
                module = rel.replace(os.sep, ".").removesuffix(".py")
                hidden.append(module)
        # Also add packages themselves
        if "__init__.py" in files:
            rel = os.path.relpath(root, sbgc_path)
            hidden.append(rel.replace(os.sep, "."))

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "GimbalBench",
        "--onefile",
        "--windowed",
        # Add Gimbal directory to the Python path
        "--paths", sbgc_path,
        # Add sbgc package as data (for any runtime lookups)
        "--add-data", f"{sbgc_pkg}{os.pathsep}sbgc",
    ]

    for mod in hidden:
        cmd += ["--hidden-import", mod]

    # Platform-specific options
    icon_path = os.path.join(HERE, "icon.ico")
    if os.path.isfile(icon_path):
        cmd += ["--icon", icon_path]

    cmd.append(os.path.join(HERE, "main.py"))

    print(f"Running PyInstaller with {len(hidden)} hidden imports...")
    print(f"  Command: {' '.join(cmd[:10])} ... main.py")
    subprocess.run(cmd, check=True)

    if sys.platform == "win32":
        exe = os.path.join(HERE, "dist", "GimbalBench.exe")
    else:
        exe = os.path.join(HERE, "dist", "GimbalBench")

    if os.path.isfile(exe):
        size_mb = os.path.getsize(exe) / (1024 * 1024)
        print(f"\nBuild complete: {exe} ({size_mb:.1f} MB)")
    else:
        print("\nWARNING: Expected executable not found")


if __name__ == "__main__":
    os.chdir(HERE)
    if "--clean" in sys.argv:
        clean()
    build()
