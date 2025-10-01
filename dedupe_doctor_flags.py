# -*- coding: utf-8 -*-
import re, pathlib
p = pathlib.Path("satyagrah/cli.py")
s = p.read_text(encoding="utf-8")

# Remove ANY prior --strict/--fix lines for doctor
s = re.sub(r"\n\s*d\.add_argument\(['\"]--strict['\"][^)]*\)\s*", "\n", s)
s = re.sub(r"\n\s*d\.add_argument\(['\"]--fix['\"][^)]*\)\s*", "\n", s)

# Insert both flags right after the doctor --host line (first match only)
s = re.sub(
    r"(d\.add_argument\(\"--host\"[^)]*\)\s*\n)",
    r"\1    d.add_argument(\"--strict\", action=\"store_true\")\n    d.add_argument(\"--fix\", action=\"store_true\")\n",
    s, count=1
)

# Ensure we pass 'fix' into doctor_run(...)
s = re.sub(
    r"rows\s*=\s*doctor_run\(\s*host\s*\)",
    r"rows = doctor_run(host, fix=getattr(args, \"fix\", False))",
    s
)

p.write_text(s, encoding="utf-8")
print("doctor flags deduped and inserted once.")
