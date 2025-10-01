# -*- coding: utf-8 -*-
import re, pathlib
p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8")
orig = s

# 1) ensure the doctor subparser has --hint (dedupe first to avoid conflicts)
s = re.sub(r"^\s*d\.add_argument\(['\"]--hint['\"][^)]+\)\s*\r?\n", "", s, flags=re.M)
s = re.sub(
    r"(d\.add_argument\(['\"]--host['\"][^)]+\)\s*\r?\n)",
    r"\1    d.add_argument('--strict', action='store_true')\r\n"
    r"    d.add_argument('--fix', action='store_true')\r\n"
    r"    d.add_argument('--hint', action='store_true')\r\n",
    s, count=1
)

# 2) replace cmd_doctor to include the hint logic (small, robust function swap)
s = re.sub(
    r"def\s+cmd_doctor\([^)]*\):[\s\S]*?(?=\ndef\s)",
    r"""def cmd_doctor(args):
    from urllib.parse import urlparse
    s = _settings_defaults()
    host = getattr(args, "host", None) or s.get("host", "http://127.0.0.1:7860")
    rows = doctor_run(host, fix=getattr(args, "fix", False))
    failed = False
    for name, info, ok in rows:
        print(f"[{'OK' if ok else '!!'}] {name}: {info}")
        if not ok:
            failed = True
    # hint block: if SD is down and --hint passed, print the exact mock command
    if getattr(args, "hint", False):
        for name, info, ok in rows:
            if name.startswith("SD API ") and not ok:
                try:
                    u = urlparse(host)
                    h = u.hostname or "127.0.0.1"
                    port = u.port or 7860
                except Exception:
                    h, port = "127.0.0.1", 7860
                print(f"Hint: start mock server -> uvicorn satyagrah.mock_sdapi:app --host {h} --port {port}")
                break
    if getattr(args, "strict", False) and failed:
        return 2
""",
    s, count=1, flags=re.S
)

if s != orig:
    p.write_text(s, encoding="utf-8")
    print("doctor --hint installed.")
else:
    print("No changes needed.")
