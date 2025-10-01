# satyagrah/creds_cli.py
from __future__ import annotations
import argparse, sys
from .secrets import set_secret, get_secret, delete_secret, list_keys, clear_service, INDEX_PATH

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m satyagrah.creds_cli", description="Manage Satyagrah credentials")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_set = sub.add_parser("set", help="Store/overwrite a secret")
    p_set.add_argument("--service", required=True, help="e.g., telegram, x, youtube")
    p_set.add_argument("--key", required=True, help="e.g., bot_token, api_key")
    p_set.add_argument("--value", required=True, help="secret value")

    p_get = sub.add_parser("get", help="Retrieve a secret (prints to stdout)")
    p_get.add_argument("--service", required=True)
    p_get.add_argument("--key", required=True)

    p_list = sub.add_parser("list", help="List key names stored for a service")
    p_list.add_argument("--service", required=True)

    p_del = sub.add_parser("delete", help="Delete a secret")
    p_del.add_argument("--service", required=True)
    p_del.add_argument("--key", required=True)

    p_clr = sub.add_parser("clear-service", help="Delete all secrets for a service")
    p_clr.add_argument("--service", required=True)

    p_idx = sub.add_parser("index-path", help="Show the path to the (non-secret) key index")

    args = p.parse_args(argv)

    if args.cmd == "set":
        set_secret(args.service, args.key, args.value)
        print(f"Saved: {args.service}.{args.key}")
        return 0
    if args.cmd == "get":
        val = get_secret(args.service, args.key)
        if val is None:
            print("(not found)", file=sys.stderr)
            return 1
        print(val)
        return 0
    if args.cmd == "list":
        keys = list_keys(args.service)
        if not keys:
            print("(no keys)")
        else:
            for k in keys:
                print(k)
        return 0
    if args.cmd == "delete":
        ok = delete_secret(args.service, args.key)
        print("deleted" if ok else "not found")
        return 0 if ok else 1
    if args.cmd == "clear-service":
        n = clear_service(args.service)
        print(f"deleted {n} entr{'y' if n==1 else 'ies'}")
        return 0
    if args.cmd == "index-path":
        print(str(INDEX_PATH))
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
