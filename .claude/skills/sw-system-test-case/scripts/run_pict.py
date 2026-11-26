"""Run PICT on a model file and save the generated combinations as JSON.

Usage:
  python run_pict.py model.txt --out rows.json [--pict PATH] [-- /o:3 ...]

Output JSON:
  {"model": "<model text>", "options": "/o:2", "parameters": [...], "rows": [{"Param": "value", ...}, ...]}
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_pict(explicit):
    cmd = [sys.executable, os.path.join(HERE, "get_pict.py")]
    if explicit:
        cmd += ["--pict", explicit]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        sys.exit("PICT is not available")
    return r.stdout.strip().splitlines()[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pict")
    ap.add_argument("pict_args", nargs="*", help="extra PICT options after --, e.g. /o:3")
    args = ap.parse_args()

    pict = find_pict(args.pict)
    opts = args.pict_args or ["/o:2"]
    model_path = args.model
    with open(model_path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):  # PICT reads a UTF-8 BOM as part of the first line
        model_path = args.out + ".model.txt"
        with open(model_path, "wb") as f:
            f.write(raw[3:])
    r = subprocess.run([pict, model_path, *opts], capture_output=True)
    out = r.stdout.decode("utf-8", errors="replace")
    err = r.stderr.decode("utf-8", errors="replace")
    if r.returncode != 0 or not out.strip():
        sys.stderr.write(err or out)
        sys.exit(f"pict failed (exit {r.returncode})")
    if err.strip():
        sys.stderr.write(err)  # PICT warnings (e.g. constraint issues) are worth reading

    lines = [l for l in out.splitlines() if l.strip()]
    header = lines[0].split("\t")
    rows = [dict(zip(header, l.split("\t"))) for l in lines[1:]]

    with open(args.model, encoding="utf-8-sig") as f:
        model_text = f.read()
    result = {"model": model_text, "options": " ".join(opts), "parameters": header, "rows": rows}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"{len(rows)} combinations, {len(header)} parameters -> {args.out}")


if __name__ == "__main__":
    main()
