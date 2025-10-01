# -*- coding: utf-8 -*-
import argparse, secrets
from .service import create_user, reset_password, set_active, list_users

def main():
    ap = argparse.ArgumentParser(description="AISatyagrah auth admin")
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True

    p_new = sub.add_parser("create", help="Create a user")
    p_new.add_argument("--username", required=True)
    p_new.add_argument("--password")
    p_new.add_argument("--role", choices=["admin","editor","viewer"], default=None,
                       help="Default: admin if username=='admin', else editor")

    p_reset = sub.add_parser("reset", help="Reset password")
    p_reset.add_argument("--username", required=True)
    p_reset.add_argument("--password", required=True)

    p_dis = sub.add_parser("disable", help="Disable user")
    p_dis.add_argument("--username", required=True)

    p_en = sub.add_parser("enable", help="Enable user")
    p_en.add_argument("--username", required=True)

    sub.add_parser("list", help="List users")

    args = ap.parse_args()
    if args.cmd == "create":
        pwd = args.password or secrets.token_urlsafe(12)
        create_user(args.username, pwd, role=args.role)
        print(f"User created: {args.username} (role={args.role or ('admin' if args.username.lower()=='admin' else 'editor')})")
        print(f"Password: {pwd}")
    elif args.cmd == "reset":
        reset_password(args.username, args.password); print("Password updated.")
    elif args.cmd == "disable":
        set_active(args.username, False); print("User disabled.")
    elif args.cmd == "enable":
        set_active(args.username, True); print("User enabled.")
    elif args.cmd == "list":
        for u in list_users():
            print(f"- {u['id']:>3}  {u['username']:15}  {u['role']:6}  active={u['is_active']}  created={u['created_at']}")

if __name__ == "__main__":
    main()
