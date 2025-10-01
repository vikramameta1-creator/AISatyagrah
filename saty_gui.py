#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Satyagrah Button Console/GUI
============================

Fix: Avoids `ModuleNotFoundError: tkinter` by **gracefully falling back** to a console menu
when Tk is unavailable (e.g., sandboxed environments). On systems with Tk installed,
this launches the original button-based GUI. Otherwise, it launches a key-driven menu
with the same actions.

Usage
-----
    # auto: GUI if Tk available, else console menu
    python saty_gui.py

    # force console (even if Tk exists)
    python saty_gui.py --console

    # run built-in self tests
    python saty_gui.py --selftest

What’s included
---------------
- GUI (Tkinter) **or** Console Menu fallback.
- Buttons/Actions: doctor, research, triage, quick, batch, layout, thumbs,
  socialcsv, seeds, publish (supports --image and --platform), open folders,
  feeds list/add/remove/reset.
- A small test suite you can run with `--selftest`.

Note: The console mode uses simple number keys as "virtual buttons" so you don’t have to
remember commands.
"""
from __future__ import annotations
import os
import sys
import json
import argparse
import threading
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional

APP_TITLE = "Satyagrah – Button Console"
ROOT = Path.cwd()

# ---------------------------- optional Tk import ----------------------------
TK_AVAILABLE = False
TK_IMPORT_ERROR: Optional[BaseException] = None
try:
    import tkinter as tk  # type: ignore
    from tkinter import ttk, filedialog, messagebox  # type: ignore
    from tkinter.scrolledtext import ScrolledText  # type: ignore
    TK_AVAILABLE = True
except Exception as _e:
    TK_AVAILABLE = False
    TK_IMPORT_ERROR = _e

# ---------------------------- utilities & helpers ----------------------------

def which_python() -> str:
    """Return the current Python executable (respects venv)."""
    return sys.executable or "python"


def platform_default_image(platform: Optional[str]) -> Optional[str]:
    """Map platform -> default image aspect. Returns None if unknown.

    >>> platform_default_image('instagram')
    '4x5'
    >>> platform_default_image('instagram-stories')
    '9x16'
    >>> platform_default_image('shorts')
    '9x16'
    >>> platform_default_image('x')
    '4x5'
    >>> platform_default_image('unknown') is None
    True
    >>> platform_default_image(None) is None
    True
    """
    if not platform:
        return None
    p = platform.lower().strip()
    if p in ("instagram-stories", "shorts"):
        return "9x16"
    if p in ("instagram", "twitter", "x", "linkedin", "facebook"):
        return "4x5"
    return None


def build_publish_args(
    *, date: str, topic_id: str, image: Optional[str] = None, platform: Optional[str] = None,
    lang: str = "en", csv: bool = True, auto_open: bool = False
) -> List[str]:
    """Build argument list for `python -m satyagrah publish`.

    >>> build_publish_args(date='latest', topic_id='t2')[:4]
    ['publish', '--date', 'latest', '--id']
    >>> build_publish_args(date='2025-09-20', topic_id='t3', platform='instagram')
    ['publish', '--date', '2025-09-20', '--id', 't3', '--lang', 'en', '--platform', 'instagram', '--csv']
    >>> build_publish_args(date='2025-09-20', topic_id='t3', image='4x5', platform='shorts')
    ['publish', '--date', '2025-09-20', '--id', 't3', '--lang', 'en', '--image', '4x5', '--csv']
    """
    args = [
        "publish", "--date", date, "--id", topic_id, "--lang", lang,
    ]
    if image:
        args += ["--image", image]
    elif platform:
        args += ["--platform", platform]
    if csv:
        args.append("--csv")
    if auto_open:
        args.append("--open")
    return args


def parse_indices_csv(txt: str) -> List[int]:
    """Parse a CSV of 1-based indices like "1,3,5" -> [1,3,5]. Ignore blanks/spaces.

    >>> parse_indices_csv('1,3, 5 , 10')
    [1, 3, 5, 10]
    >>> parse_indices_csv('')
    []
    >>> parse_indices_csv('a,2,b,4')
    [2, 4]
    """
    out: List[int] = []
    for tok in (txt or "").split(','):
        tok = tok.strip()
        if not tok:
            continue
        try:
            v = int(tok)
        except Exception:
            continue
        if v >= 1:
            out.append(v)
    return out

# ---------------------------- subprocess runner ----------------------------

class BaseRunner:
    def run(self, args: List[str]) -> None:  # pragma: no cover (abstract)
        raise NotImplementedError


class ConsoleRunner(BaseRunner):
    def __init__(self):
        self.proc: Optional[subprocess.Popen] = None
        self.lock = threading.Lock()

    def run(self, args: List[str]) -> None:
        py = which_python()
        cmd = [py, "-m", "satyagrah"] + args
        print("\n$", " ".join(cmd))
        try:
            self.proc = subprocess.Popen(
                cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            assert self.proc.stdout is not None
            for line in self.proc.stdout:
                print(line, end="")
            rc = self.proc.wait()
            print(f"[exit {rc}]\n")
        except FileNotFoundError:
            print("ERROR: Could not find Python or module. Ensure your venv is active and 'satyagrah' is installed.")
        except Exception as e:
            print(f"ERROR: {e}")
        finally:
            self.proc = None


# ---------------------------- GUI runner (only if Tk exists) ----------------------------
if TK_AVAILABLE:
    class TkRunner(BaseRunner):
        def __init__(self, text_widget: 'ScrolledText', run_button: 'ttk.Button | None' = None):
            self.text = text_widget
            self.run_btn = run_button
            self.proc: Optional[subprocess.Popen] = None
            self.lock = threading.Lock()

        def _append(self, s: str) -> None:
            self.text.configure(state="normal")
            self.text.insert("end", s)
            self.text.see("end")
            self.text.configure(state="disabled")

        def run(self, args: List[str]) -> None:
            if self.proc is not None:
                messagebox.showwarning("Busy", "A command is already running.")
                return
            py = which_python()
            cmd = [py, "-m", "satyagrah"] + args
            self._append("\n$ " + " ".join(cmd) + "\n")
            if self.run_btn:
                self.run_btn.configure(state=tk.DISABLED)

            def _worker():
                try:
                    self.proc = subprocess.Popen(
                        cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1
                    )
                    assert self.proc.stdout is not None
                    for line in self.proc.stdout:
                        self._append(line)
                    rc = self.proc.wait()
                    self._append(f"\n[exit {rc}]\n")
                except Exception as e:
                    self._append(f"\n[error] {e}\n")
                finally:
                    self.proc = None
                    if self.run_btn:
                        self.run_btn.configure(state=tk.NORMAL)

# ---------------------------- GUI app (only if Tk exists) ----------------------------
if TK_AVAILABLE:
    class Labeled(ttk.Frame):
        def __init__(self, parent, text: str, child, *cargs, **ckw):
            super().__init__(parent)
            ttk.Label(self, text=text).grid(row=0, column=0, sticky="w", padx=(0,6))
            self.child = child(self, *cargs, **ckw)
            self.child.grid(row=0, column=1, sticky="ew")
            self.columnconfigure(1, weight=1)

    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title(APP_TITLE)
            self.geometry("1100x720")
            self.minsize(900, 600)

            # top params
            top = ttk.Frame(self)
            top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)

            self.date_var = tk.StringVar(value="latest")
            self.idx_var = tk.IntVar(value=1)
            self.top_var = tk.IntVar(value=3)
            self.indices_var = tk.StringVar(value="")
            self.id_var = tk.StringVar(value="auto")
            self.seed_var = tk.IntVar(value=12345)
            self.lang_var = tk.StringVar(value="en,hi")
            self.aspect_var = tk.StringVar(value="all")
            self.image_var = tk.StringVar(value="")  # 4x5|1x1|9x16 (optional)
            self.platform_var = tk.StringVar(value="")  # instagram|instagram-stories|x|twitter|linkedin|facebook|shorts

            # checkboxes
            self.skip_image = tk.BooleanVar(value=False)
            self.package = tk.BooleanVar(value=False)
            self.saveas = tk.BooleanVar(value=True)
            self.strict = tk.BooleanVar(value=True)
            self.csv = tk.BooleanVar(value=True)
            self.auto_open = tk.BooleanVar(value=False)

            # controls row 1
            row1 = ttk.Frame(top)
            row1.pack(side=tk.TOP, fill=tk.X)
            Labeled(row1, "Date", ttk.Entry, textvariable=self.date_var, width=14)
            Labeled(row1, "Idx", ttk.Spinbox, from_=1, to=999, textvariable=self.idx_var, width=6).grid_configure(padx=(12,0))
            Labeled(row1, "Top", ttk.Spinbox, from_=1, to=99, textvariable=self.top_var, width=6).grid_configure(padx=(12,0))
            Labeled(row1, "Indices", ttk.Entry, textvariable=self.indices_var, width=18).grid_configure(padx=(12,0))
            Labeled(row1, "ID", ttk.Entry, textvariable=self.id_var, width=10).grid_configure(padx=(12,0))
            Labeled(row1, "Seed", ttk.Spinbox, from_=-2**31, to=2**31-1, textvariable=self.seed_var, width=14).grid_configure(padx=(12,0))

            # controls row 2
            row2 = ttk.Frame(top)
            row2.pack(side=tk.TOP, fill=tk.X, pady=(6,0))
            Labeled(row2, "Lang", ttk.Entry, textvariable=self.lang_var, width=18)
            Labeled(row2, "Aspect", ttk.Combobox, textvariable=self.aspect_var, values=["all","4x5","1x1","9x16"], width=8).grid_configure(padx=(12,0))
            Labeled(row2, "Image", ttk.Combobox, textvariable=self.image_var, values=["","4x5","1x1","9x16"], width=8).grid_configure(padx=(12,0))
            Labeled(row2, "Platform", ttk.Combobox, textvariable=self.platform_var, values=["","instagram","instagram-stories","shorts","x","twitter","linkedin","facebook"], width=18).grid_configure(padx=(12,0))

            # toggles
            row3 = ttk.Frame(top)
            row3.pack(side=tk.TOP, fill=tk.X, pady=(6,0))
            ttk.Checkbutton(row3, text="Skip image", variable=self.skip_image).pack(side=tk.LEFT, padx=(0,12))
            ttk.Checkbutton(row3, text="Package", variable=self.package).pack(side=tk.LEFT, padx=(0,12))
            ttk.Checkbutton(row3, text="SaveAs", variable=self.saveas).pack(side=tk.LEFT, padx=(0,12))
            ttk.Checkbutton(row3, text="Strict doctor", variable=self.strict).pack(side=tk.LEFT, padx=(0,12))
            ttk.Checkbutton(row3, text="CSV (publish)", variable=self.csv).pack(side=tk.LEFT, padx=(0,12))
            ttk.Checkbutton(row3, text="Open outbox", variable=self.auto_open).pack(side=tk.LEFT, padx=(0,12))

            # notebook
            nb = ttk.Notebook(self)
            nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0,8))

            self.pipeline_tab = self._build_pipeline_tab(nb)
            self.publish_tab = self._build_publish_tab(nb)
            self.feeds_tab = self._build_feeds_tab(nb)
            self.tools_tab = self._build_tools_tab(nb)

            # log
            logfrm = ttk.Frame(self)
            logfrm.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False, padx=10, pady=(0,10))
            ttk.Label(logfrm, text="Output:").pack(anchor="w")
            self.log = ScrolledText(logfrm, height=14, wrap="word", state="disabled")
            self.log.pack(fill=tk.BOTH, expand=True)

            # runner
            self.runner = TkRunner(self.log)

        # ---------------- build tabs ----------------
        def _build_pipeline_tab(self, nb):
            tab = ttk.Frame(nb)
            nb.add(tab, text="Pipeline")

            # row of main actions
            bar = ttk.Frame(tab)
            bar.pack(side=tk.TOP, fill=tk.X, pady=4)
            ttk.Button(bar, text="Doctor", command=self.on_doctor).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Research", command=self.on_research).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Triage", command=self.on_triage).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Quick", command=self.on_quick).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Batch", command=self.on_batch).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Layout", command=self.on_layout).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Thumbs", command=self.on_thumbs).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="SocialCSV", command=self.on_socialcsv).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Seeds", command=self.on_seeds).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Stop", command=lambda: None).pack(side=tk.RIGHT, padx=4)
            return tab

        def _build_publish_tab(self, nb):
            tab = ttk.Frame(nb)
            nb.add(tab, text="Publish")
            bar = ttk.Frame(tab)
            bar.pack(side=tk.TOP, fill=tk.X, pady=4)
            ttk.Button(bar, text="Publish", command=self.on_publish).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Open exports", command=lambda: self.open_path(ROOT/"exports"/self.date_var.get())).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Open runs", command=lambda: self.open_path(ROOT/"data"/"runs"/self.date_var.get())).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Open outbox", command=lambda: self.open_path(ROOT/"exports"/self.date_var.get()/"outbox")).pack(side=tk.LEFT, padx=4)
            return tab

        def _build_feeds_tab(self, nb):
            tab = ttk.Frame(nb)
            nb.add(tab, text="Feeds")

            # controls
            ctrl = ttk.Frame(tab)
            ctrl.pack(side=tk.TOP, fill=tk.X, pady=4)
            ttk.Button(ctrl, text="List", command=self.on_feeds_list).pack(side=tk.LEFT, padx=4)
            self.new_feed_var = tk.StringVar(value="")
            ttk.Entry(ctrl, textvariable=self.new_feed_var, width=60).pack(side=tk.LEFT, padx=4)
            ttk.Button(ctrl, text="Add", command=self.on_feeds_add).pack(side=tk.LEFT, padx=4)
            self.rm_index_var = tk.IntVar(value=0)
            ttk.Spinbox(ctrl, from_=1, to=999, textvariable=self.rm_index_var, width=6).pack(side=tk.LEFT, padx=(16,4))
            ttk.Button(ctrl, text="Remove by index", command=self.on_feeds_remove_index).pack(side=tk.LEFT, padx=4)
            ttk.Button(ctrl, text="Reset (backup/defaults)", command=self.on_feeds_reset).pack(side=tk.LEFT, padx=(16,4))
            return tab

        def _build_tools_tab(self, nb):
            tab = ttk.Frame(nb)
            nb.add(tab, text="Tools")
            bar = ttk.Frame(tab)
            bar.pack(side=tk.TOP, fill=tk.X, pady=4)
            ttk.Button(bar, text="Open configs", command=lambda: self.open_path(ROOT/"configs")).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Open project root", command=lambda: self.open_path(ROOT)).pack(side=tk.LEFT, padx=4)
            ttk.Button(bar, text="Smoke", command=self.on_smoke).pack(side=tk.LEFT, padx=4)
            return tab

        # ---------------- button handlers ----------------
        def on_doctor(self):
            args = ["doctor", "--strict"]
            self.runner.run(args)

        def on_research(self):
            args = ["research", "--date", self.date_var.get()]
            self.runner.run(args)

        def on_triage(self):
            args = ["triage", "--date", self.date_var.get()]
            self.runner.run(args)

        def on_quick(self):
            args = [
                "quick", "--date", self.date_var.get(),
                "--idx", str(self.idx_var.get()),
                "--seed", str(self.seed_var.get()),
            ]
            if self.aspect_var.get() and self.aspect_var.get() != "all":
                args += ["--aspect", self.aspect_var.get()]
            if self.lang_var.get():
                args += ["--lang", self.lang_var.get()]
            if True:  # expose useful toggles
                # skip_image, package, saveas read from GUI toggles
                pass
            self.runner.run(args)

        def on_batch(self):
            args = [
                "batch",
                "--date", self.date_var.get(),
                "--seed", str(self.seed_var.get()),
            ]
            if self.indices_var.get().strip():
                args += ["--indices", self.indices_var.get().strip()]
            else:
                args += ["--top", str(self.top_var.get())]
            if self.aspect_var.get() and self.aspect_var.get() != "all":
                args += ["--aspect", self.aspect_var.get()]
            if self.lang_var.get():
                args += ["--lang", self.lang_var.get()]
            self.runner.run(args)

        def on_layout(self):
            args = [
                "layout", "--date", self.date_var.get(),
                "--id", "auto",
            ]
            if self.aspect_var.get() and self.aspect_var.get() != "all":
                args += ["--aspect", self.aspect_var.get()]
            self.runner.run(args)

        def on_thumbs(self):
            self.runner.run(["thumbs", "--date", self.date_var.get()])

        def on_socialcsv(self):
            self.runner.run(["socialcsv", "--date", self.date_var.get()])

        def on_seeds(self):
            self.runner.run(["seeds", "--date", self.date_var.get()])

        def on_publish(self):
            img = (self.image_var.get() or "").strip() or None
            plat = (self.platform_var.get() or "").strip() or None
            if not img:
                img = platform_default_image(plat)
            args = build_publish_args(
                date=self.date_var.get(), topic_id=(self.id_var.get() or "auto"),
                image=img, platform=plat, lang=(self.lang_var.get() or "en"),
                csv=True, auto_open=True,
            )
            self.runner.run(args)

        def on_smoke(self):
            self.runner.run(["smoke", "--date", self.date_var.get()])

        # feeds
        def on_feeds_list(self):
            self.runner.run(["feeds", "list"]) 

        def on_feeds_add(self):
            url = getattr(self, "new_feed_var", tk.StringVar(value="")).get().strip()
            if not url:
                messagebox.showinfo("Add feed", "Enter a feed URL first.")
                return
            self.runner.run(["feeds", "add", url])

        def on_feeds_remove_index(self):
            i = getattr(self, "rm_index_var", tk.IntVar(value=0)).get()
            if i <= 0:
                messagebox.showinfo("Remove feed", "Enter a 1-based index (see 'List').")
                return
            self.runner.run(["feeds", "remove", "--index", str(i)])

        def on_feeds_reset(self):
            use_file = messagebox.askyesno(
                "Feeds reset",
                "Restore from a specific feeds.yaml file?\n(Choose No to use backup/defaults)"
            )
            if use_file:
                path = filedialog.askopenfilename(
                    title="Select feeds.yaml",
                    filetypes=[("YAML", "*.yaml;*.yml"), ("All", "*.*")]
                )
                if path:
                    self.runner.run(["feeds", "reset", "--from", path])
            else:
                self.runner.run(["feeds", "reset"])  

        # ---------------- misc ----------------
        def open_path(self, p: Path):
            try:
                os.startfile(str(p))  # Windows
            except Exception:
                try:
                    subprocess.run(["open", str(p)])  # macOS
                except Exception:
                    subprocess.run(["xdg-open", str(p)])  # Linux

# ---------------------------- console (fallback UI) ----------------------------

def console_menu(runner: ConsoleRunner, *, default_date: str = "latest") -> int:
    print("\nSatyagrah Console (Tk not available)\n" + ("-"*34))
    if TK_IMPORT_ERROR:
        print(f"[notice] Tkinter import failed: {TK_IMPORT_ERROR}")
    print("Virtual buttons: type a number and press Enter.\n")

    def ask(prompt: str, default: str = "") -> str:
        val = input(f"{prompt} [{default}]: ").strip()
        return val or default

    date = default_date
    while True:
        print("""
1) Doctor (strict)
2) Research (date)
3) Triage (date)
4) Quick (date, idx, seed)
5) Batch (indices or top)
6) Layout (date, aspect)
7) Thumbs (date)
8) SocialCSV (date)
9) Seeds (date)
10) Publish (id, image|platform, lang, csv/open)
11) Feeds: list
12) Feeds: add
13) Feeds: remove by index
14) Feeds: reset (backup/defaults)
15) Open exports folder
16) Open runs folder
0) Exit
""")
        choice = input("Select: ").strip()
        if choice == "0":
            return 0
        elif choice == "1":
            runner.run(["doctor", "--strict"]) 
        elif choice == "2":
            date = ask("Date", date)
            runner.run(["research", "--date", date])
        elif choice == "3":
            date = ask("Date", date)
            runner.run(["triage", "--date", date])
        elif choice == "4":
            date = ask("Date", date)
            idx = ask("Idx", "1")
            seed = ask("Seed", "12345")
            runner.run(["quick", "--date", date, "--idx", idx, "--seed", seed])
        elif choice == "5":
            date = ask("Date", date)
            raw = ask("Indices (CSV) or blank for Top", "")
            if raw:
                runner.run(["batch", "--date", date, "--indices", raw])
            else:
                top = ask("Top", "3")
                runner.run(["batch", "--date", date, "--top", top])
        elif choice == "6":
            date = ask("Date", date)
            aspect = ask("Aspect (all|4x5|1x1|9x16)", "all")
            runner.run(["layout", "--date", date, "--id", "auto", "--aspect", aspect])
        elif choice == "7":
            date = ask("Date", date)
            runner.run(["thumbs", "--date", date])
        elif choice == "8":
            date = ask("Date", date)
            runner.run(["socialcsv", "--date", date])
        elif choice == "9":
            date = ask("Date", date)
            runner.run(["seeds", "--date", date])
        elif choice == "10":
            date = ask("Date", date)
            tid  = ask("ID (e.g., t1 or auto)", "auto")
            image = ask("Image (blank to use platform) [4x5|1x1|9x16]", "")
            platform = ask("Platform (instagram/instagram-stories/x/twitter/linkedin/facebook/shorts)", "")
            lang = ask("Lang CSV", "en,hi")
            csv = ask("CSV? (y/n)", "y").lower().startswith('y')
            do_open = ask("Open outbox? (y/n)", "n").lower().startswith('y')
            args = build_publish_args(date=date, topic_id=tid, image=(image or None), platform=(platform or None), lang=lang.split(',')[0], csv=csv, auto_open=do_open)
            runner.run(args)
        elif choice == "11":
            runner.run(["feeds", "list"]) 
        elif choice == "12":
            url = ask("Feed URL", "")
            if url:
                runner.run(["feeds", "add", url])
        elif choice == "13":
            idx = ask("Remove index (1-based)", "1")
            runner.run(["feeds", "remove", "--index", idx])
        elif choice == "14":
            runner.run(["feeds", "reset"]) 
        elif choice == "15":
            _open_path(ROOT/"exports"/date)
        elif choice == "16":
            _open_path(ROOT/"data"/"runs"/date)
        else:
            print("Unknown choice. Try again.")


def _open_path(p: Path) -> None:
    try:
        os.startfile(str(p))  # Windows
    except Exception:
        try:
            subprocess.run(["open", str(p)])  # macOS
        except Exception:
            subprocess.run(["xdg-open", str(p)])  # Linux

# ---------------------------- test suite ----------------------------

def _selftest() -> int:
    import unittest

    class Tests(unittest.TestCase):
        def test_platform_map(self):
            self.assertEqual(platform_default_image('instagram'), '4x5')
            self.assertEqual(platform_default_image('instagram-stories'), '9x16')
            self.assertEqual(platform_default_image('shorts'), '9x16')
            self.assertEqual(platform_default_image('x'), '4x5')
            self.assertIsNone(platform_default_image('unknown'))
            self.assertIsNone(platform_default_image(None))

        def test_build_publish_args_prefers_image(self):
            args = build_publish_args(date='2025-09-20', topic_id='t3', image='4x5', platform='shorts')
            self.assertIn('--image', args)
            self.assertNotIn('--platform', args)

        def test_build_publish_args_platform_only(self):
            args = build_publish_args(date='2025-09-20', topic_id='t3', platform='instagram')
            self.assertIn('--platform', args)
            self.assertNotIn('--image', args)

        def test_indices_parse(self):
            self.assertEqual(parse_indices_csv('1, 3,5'), [1,3,5])
            self.assertEqual(parse_indices_csv(''), [])
            self.assertEqual(parse_indices_csv('a,2,b,4'), [2,4])

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

# ---------------------------- main ----------------------------

def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument('--console', action='store_true', help='Force console menu even if Tk is available')
    parser.add_argument('--selftest', action='store_true', help='Run built-in tests and exit')
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.selftest:
        return _selftest()

    if TK_AVAILABLE and not args.console:
        # GUI path
        try:
            app = App()  # type: ignore[name-defined]
            app.mainloop()
            return 0
        except Exception as e:
            # If something goes wrong at runtime, fall back to console
            print(f"GUI error: {e}. Falling back to console...")

    # Console fallback
    runner = ConsoleRunner()
    return console_menu(runner)


if __name__ == "__main__":
    raise SystemExit(main())
