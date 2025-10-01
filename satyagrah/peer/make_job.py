# -*- coding: utf-8 -*-
import argparse, secrets
from pathlib import Path
from .jobfmt import make_job_dict, write_job_zip

def main():
    ap = argparse.ArgumentParser(description="Create signed peer-GPU job zip")
    ap.add_argument("--outbox", default=str(Path("jobs")/"outbox"))
    ap.add_argument("--id", default=None)
    ap.add_argument("--requester", default="host")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--steps", type=int, default=25)
    ap.add_argument("--width", type=int, default=768)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--ttl", type=int, default=24, help="hours until expires")
    args = ap.parse_args()

    outbox = Path(args.outbox); outbox.mkdir(parents=True, exist_ok=True)
    job_id = args.id or secrets.token_hex(6)
    tasks = [{
        "type":"txt2img",
        "prompt": args.prompt,
        "seed": args.seed,
        "steps": args.steps,
        "width": args.width,
        "height": args.height,
        "count": args.count
    }]
    job = make_job_dict(job_id, args.requester, tasks, ttl_hours=args.ttl)
    out_zip = outbox / f"job_{job_id}.zip"
    write_job_zip(job, out_zip)
    print("Wrote:", out_zip)

if __name__ == "__main__":
    main()
