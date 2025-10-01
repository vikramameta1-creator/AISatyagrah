# -*- coding: utf-8 -*-
import argparse
from pathlib import Path
from .jobfmt import read_result_zip

def main():
    ap = argparse.ArgumentParser(description="Verify a result.zip signature & print summary")
    ap.add_argument("zip_path")
    args = ap.parse_args()
    res = read_result_zip(Path(args.zip_path))
    print("job_id:", res["job_id"])
    print("ok    :", res["ok"])
    print("images:", res["images"])
    if not res["ok"]:
        print("errors:", res["errors"])

if __name__ == "__main__":
    main()
