# add_feeds_cmd.py — adds `feeds list` and `feeds add` to satyagrah/cli.py
import pathlib, re

cli_path = pathlib.Path("satyagrah/cli.py")
text = cli_path.read_text(encoding="utf-8")
orig = text

# --- functions to insert ---
fn_block = r'''
def cmd_feeds_list(args):
    feeds = load_feeds_yaml().get("rss", []) or []
    if not feeds:
        print("No feeds configured. Edit configs/feeds.yaml or run: python -m satyagrah feeds add <url>")
        return 0
    for i, u in enumerate(feeds, 1):
        print(f"{i:2d}. {u}")
    return 0

def cmd_feeds_add(args):
    import yaml
    cfg = ROOT / "configs" / "feeds.yaml"
    urls = [u.strip() for u in getattr(args, "urls", []) if u and u.strip()]
    if not urls:
        print("No URLs supplied."); return 2
    data = {}
    if cfg.exists():
        try:
            data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
    existing = [x.strip() for x in (data.get("rss") or []) if x and str(x).strip()]
    seen_lower = {x.lower() for x in existing}
    added = []
    for u in urls:
        k = u.lower()
        if k not in seen_lower:
            existing.append(u)
            seen_lower.add(k)
            added.append(u)
    data["rss"] = existing
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if added:
        print("Added -> " + " | ".join(added))
    else:
        print("No new URLs (all duplicates).")
    print(f"Feeds file: {cfg}")
    return 0
'''

# insert functions before the main-section marker
if "def cmd_feeds_list(" not in text:
    text = text.replace("# ------------------ main ------------------", fn_block + "\n# ------------------ main ------------------")

# --- parser block to insert inside main() ---
parser_block = r'''
    # feeds manager
    fd = sub.add_parser("feeds", help="Manage configs/feeds.yaml")
    fsp = fd.add_subparsers(dest="feeds_cmd", required=True)

    fd_list = fsp.add_parser("list", help="List RSS feeds from configs/feeds.yaml")
    fd_list.set_defaults(func=cmd_feeds_list)

    fd_add = fsp.add_parser("add", help="Add one or more RSS feed URLs")
    fd_add.add_argument("urls", nargs="+")
    fd_add.set_defaults(func=cmd_feeds_add)
'''

# place the parser block right before "extras" if present; else before args parse
if "register_extra_subcommands(sub)" in text and "fd = sub.add_parser(\"feeds\"" not in text:
    text = text.replace("    # extras\n    register_extra_subcommands(sub)", parser_block + "\n    # extras\n    register_extra_subcommands(sub)")
elif "args = p.parse_args(argv)" in text and "fd = sub.add_parser(\"feeds\"" not in text:
    text = text.replace("    args = p.parse_args(argv)", parser_block + "\n    args = p.parse_args(argv)")

# write back
if text != orig:
    cli_path.write_text(text, encoding="utf-8")
    print("feeds command installed.")
else:
    print("No changes needed.")
