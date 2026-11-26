"""Locate or download Microsoft PICT (https://github.com/microsoft/pict).

Prints the path of a usable pict executable on stdout.

Search order:
  1. --pict / PICT_PATH environment variable
  2. `pict` on PATH
  3. cached download next to this skill (../bin/pict.exe)
  4. download pict.exe from the latest GitHub release (Windows only)

On non-Windows systems PICT has no prebuilt binary; build it from source
(git clone https://github.com/microsoft/pict && cd pict && make) and put it on PATH.
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request

RELEASE_API = "https://api.github.com/repos/microsoft/pict/releases/latest"
FALLBACK_URL = "https://github.com/microsoft/pict/releases/download/v3.7.4/pict.exe"
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(SKILL_DIR, "bin", "pict.exe")


def works(path):
    try:
        # pict with no args prints usage and exits non-zero; we only need it to start.
        subprocess.run([path], capture_output=True, timeout=20)
        return True
    except (OSError, subprocess.TimeoutExpired):
        return False


def latest_url():
    try:
        req = urllib.request.Request(RELEASE_API, headers={"User-Agent": "pict-fetch"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        for a in data.get("assets", []):
            if a["name"].lower() == "pict.exe":
                return a["browser_download_url"]
    except Exception as e:  # network / rate limit: use the pinned release
        print(f"[get_pict] release lookup failed ({e}); using pinned v3.7.4", file=sys.stderr)
    return FALLBACK_URL


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pict", help="explicit path to pict executable")
    ap.add_argument("--force", action="store_true", help="re-download even if cached")
    args = ap.parse_args()

    for cand in (args.pict, os.environ.get("PICT_PATH"), shutil.which("pict")):
        if cand and os.path.isfile(cand) and works(cand):
            print(cand)
            return 0

    if os.path.isfile(CACHE) and not args.force and works(CACHE):
        print(CACHE)
        return 0

    if platform.system() != "Windows":
        print("[get_pict] No prebuilt PICT for this OS. Build from source: "
              "git clone https://github.com/microsoft/pict && cd pict && make, then put it on PATH.",
              file=sys.stderr)
        return 1

    url = latest_url()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    print(f"[get_pict] downloading {url}", file=sys.stderr)
    tmp = CACHE + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": "pict-fetch"})
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    os.replace(tmp, CACHE)
    if not works(CACHE):
        print("[get_pict] downloaded file does not run", file=sys.stderr)
        return 1
    print(CACHE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
