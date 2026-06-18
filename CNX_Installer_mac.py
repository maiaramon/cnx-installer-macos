#!/usr/bin/python3
#
# CNX Pack Installer - macOS
# Copyright (C) 2026 maiaramon
#
# macOS port of CNX_Installer. The CNX Pack itself is created and
# maintained by CostelaBR — https://github.com/CostelaCNX/CNX
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details: https://www.gnu.org/licenses/
#
"""
CNX Pack Installer - macOS v1.4

v1.4 — Dual mode (Nova Instalação / Atualização), exclusão inteligente,
         changelog completo com formatação corrigida.

Runs on the system Python (/usr/bin/python3) which ships with tkinter.

Note on rendering: this macOS Tk build ignores explicit `bg` colors on classic
widgets (Frame/Label/Button) under dark mode, so the entire UI is drawn on a
single tk.Canvas — canvas primitives (rectangles, text) always honor their
colors. The only real widget is the tk.Text log, which does honor its bg.
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import threading
import urllib.request
import json
import zipfile
import io
import os
import re
import plistlib

REPOS = ["CostelaCNX/CNX", "CNX17/CNX_spare"]
VERSION = "v1.4  ·  macOS Edition"

# ── Design tokens ────────────────────────────────────────────────────────────
C = {
    "bg":           "#F4F5FB",
    "card":         "#FFFFFF",
    "header":       "#4834D4",
    "header_lo":    "#5B4FE0",
    "accent":       "#6C5CE7",
    "accent_dim":   "#A29BFE",
    "accent_press": "#5547D0",
    "green":        "#00B894",
    "green_hover":  "#00CEA6",
    "green_press":  "#019875",
    "orange":       "#E17055",
    "orange_hover": "#F08070",
    "orange_press": "#C05F45",
    "text":         "#2D3436",
    "muted":        "#8C95A6",
    "border":       "#D9DEEC",
    "field":        "#EEF0F8",
    "field_hover":  "#E2E6F4",
    "term_bg":      "#1A1B26",
    "term_fg":      "#9ECE6A",
    "term_dim":     "#565F89",
    "term_cyan":    "#7DCFFF",
    "term_white":   "#C0CAF5",
    "term_amber":   "#E0AF68",
    "term_red":     "#F7768E",
}

FONT_UI   = "Avenir Next"
FONT_MONO = "Menlo"


# ── disk helpers ──────────────────────────────────────────────────────────────

def list_removable_drives():
    """All removable/ejectable whole disks (handles built-in SD readers too)."""
    try:
        r = subprocess.run(["diskutil", "list", "-plist"], capture_output=True)
        data = plistlib.loads(r.stdout)
        out = []
        for disk in data.get("WholeDisks", []):
            info = _disk_info(disk)
            if info and info["removable"]:
                label = "{}  ·  {}  ·  [{}]".format(info["name"], info["size"], disk)
                out.append((label, disk))
        return out
    except Exception:
        return []


def _disk_info(disk):
    try:
        r = subprocess.run(["diskutil", "info", "-plist", disk], capture_output=True)
        d = plistlib.loads(r.stdout)
        name = d.get("VolumeName") or d.get("MediaName") or disk
        size = d.get("TotalSize", 0)
        removable = d.get("RemovableMedia") or d.get("RemovableMediaOrExternalDevice")
        return {"name": name, "size": "{:.0f} GB".format(size / 1e9),
                "removable": bool(removable)}
    except Exception:
        return None


def _dev_from_label(label):
    m = re.search(r'\[(disk\d+)\]', label)
    return "/dev/{}".format(m.group(1)) if m else None


# ── GitHub / download ─────────────────────────────────────────────────────────

def _zip_url(repo):
    url = "https://api.github.com/repos/{}/releases/latest".format(repo)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    tag = data.get("tag_name", "?")
    for asset in data.get("assets", []):
        if asset["name"].endswith(".zip"):
            return asset["browser_download_url"], tag
    raise ValueError("Nenhum ZIP no release de {}".format(repo))


def _download(url, progress_cb):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        buf = bytearray()
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            buf.extend(chunk)
            if total:
                progress_cb(len(buf), total)
    return bytes(buf)


# ── ZIP / BMP ─────────────────────────────────────────────────────────────────

def _extract_zip(data, dest, log):
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        for name in names:
            try:
                zf.extract(name, dest)
            except Exception as e:
                log("   ! {} — {}".format(name, e), "warn")
        log("   {} arquivos extraídos".format(len(names)), "dim")


def _extract_hidden_zip(dest, log):
    bmp = os.path.join(dest, "bootloader", "bootlogo_atmo_sys.bmp")
    if not os.path.exists(bmp):
        log("   (sem pacote oculto — ok)", "dim")
        return
    tmp = os.path.join(dest, "cnx_temp.zip")
    try:
        with open(bmp, "rb") as f:
            data = f.read()
        idx = data.find(b"PK\x03\x04")
        if idx == -1:
            log("   (nenhum ZIP embutido no BMP)", "dim")
            return
        with open(tmp, "wb") as f:
            f.write(data[idx:])
        with zipfile.ZipFile(tmp) as zf:
            names = zf.namelist()
            for name in names:
                try:
                    zf.extract(name, dest)
                except Exception as e:
                    log("   ! {} — {}".format(name, e), "warn")
        log("   {} arquivos ocultos extraídos".format(len(names)), "dim")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ── Main app (Canvas-based UI) ────────────────────────────────────────────────

class App(tk.Tk):
    W, H = 720, 648
    PAD = 24

    def __init__(self):
        super().__init__()
        self.title("CNX Pack Installer")
        try:
            self.tk_setPalette(background=C["bg"], foreground=C["text"])
        except tk.TclError:
            pass
        self.resizable(False, False)
        self.geometry("{}x{}".format(self.W, self.H))

        self.canvas = tk.Canvas(self, width=self.W, height=self.H,
                                bg=C["bg"], highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        self._buttons = {}     # tag -> dict(rect, label, fill, hover, press, fg, enabled, cmd)
        self._drives = []
        self._sel_label = ""
        self._dropdown = None
        self._mode = "new"          # "new" | "update"
        self._exclusions = []       # relative paths to preserve in update mode

        self._build()
        self._set_mode("update")   # open in update mode by default
        self._refresh()
        self._center()

        self.canvas.bind("<Button-1>", self._maybe_close_dropdown, add="+")
        self.after(100, self._bring_to_front)

    # ── geometry ──────────────────────────────────────────────────────────────

    def _bring_to_front(self):
        try:
            self.lift()
            self.attributes("-topmost", True)
            self.after(400, lambda: self.attributes("-topmost", False))
            self.focus_force()
        except tk.TclError:
            pass
        try:
            subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to set frontmost of '
                 "(first process whose unix id is {}) to true".format(os.getpid())],
                check=False, capture_output=True, timeout=3,
            )
        except Exception:
            pass

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = max(0, (sw - self.W) // 2)
        y = max(0, (sh - self.H) // 3)
        self.geometry("+{}+{}".format(x, y))

    # ── primitives ────────────────────────────────────────────────────────────

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [
            x1 + r, y1,  x2 - r, y1,  x2, y1,  x2, y1 + r,
            x2, y2 - r,  x2, y2,  x2 - r, y2,  x1 + r, y2,
            x1, y2,  x1, y2 - r,  x1, y1 + r,  x1, y1,
        ]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def _button(self, tag, x1, y1, x2, y2, text, font_size,
                fill, hover, press, fg, cmd, radius=10):
        rect = self._round_rect(x1, y1, x2, y2, radius,
                                fill=fill, outline=fill, tags=(tag,))
        lbl = self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=text,
                                      fill=fg, font=(FONT_UI, font_size, "bold"),
                                      tags=(tag,))
        self._buttons[tag] = {
            "rect": rect, "label": lbl, "fill": fill, "hover": hover,
            "press": press, "fg": fg, "enabled": True, "cmd": cmd,
        }
        self.canvas.tag_bind(tag, "<Enter>",
                             lambda e, t=tag: self._btn_state(t, "hover"))
        self.canvas.tag_bind(tag, "<Leave>",
                             lambda e, t=tag: self._btn_state(t, "fill"))
        self.canvas.tag_bind(tag, "<ButtonPress-1>",
                             lambda e, t=tag: self._btn_state(t, "press"))
        self.canvas.tag_bind(tag, "<ButtonRelease-1>",
                             lambda e, t=tag: self._btn_click(t))
        return tag

    def _btn_state(self, tag, which):
        b = self._buttons[tag]
        if not b["enabled"]:
            return
        col = b[which]
        self.canvas.itemconfig(b["rect"], fill=col, outline=col)
        self.canvas.configure(cursor="pointinghand")

    def _btn_click(self, tag):
        b = self._buttons[tag]
        if not b["enabled"]:
            return
        self.canvas.itemconfig(b["rect"], fill=b["hover"], outline=b["hover"])
        b["cmd"]()

    def _btn_enable(self, tag, enabled):
        b = self._buttons[tag]
        b["enabled"] = enabled
        col = b["fill"] if enabled else C["border"]
        self.canvas.itemconfig(b["rect"], fill=col, outline=col)
        self.canvas.itemconfig(b["label"], fill=b["fg"] if enabled else C["muted"])

    def _btn_repaint(self, tag, fill, hover, press, fg):
        """Update a button's color scheme and repaint it."""
        b = self._buttons[tag]
        b.update(fill=fill, hover=hover, press=press, fg=fg)
        if b["enabled"]:
            self.canvas.itemconfig(b["rect"], fill=fill, outline=fill)
            self.canvas.itemconfig(b["label"], fill=fg)

    # ── build static layout ───────────────────────────────────────────────────

    def _build(self):
        cv = self.canvas
        W, P = self.W, self.PAD

        # ── Header ────────────────────────────────────────────────────────────
        cv.create_rectangle(0, 0, W, 96, fill=C["header"], outline=C["header"])
        cv.create_rectangle(0, 92, W, 96, fill=C["header_lo"], outline=C["header_lo"])
        cv.create_text(P, 34, anchor="w", text="⬢  CNX Pack Installer",
                       fill="white", font=(FONT_UI, 22, "bold"))
        cv.create_text(P + 2, 66, anchor="w", text=VERSION,
                       fill=C["accent_dim"], font=(FONT_UI, 12))
        # Changelog button — top right of header
        self._button("changelog", W - P - 138, 54, W - P, 82,
                     "📋  Changelog", 11,
                     C["accent_press"], C["accent"], C["header_lo"], "white",
                     self._show_changelog, radius=8)

        # ── Section 1 — SD Card ───────────────────────────────────────────────
        self._section(P, 120, "1", "Selecione o SD Card")

        self.sel_x1, self.sel_y1, self.sel_x2, self.sel_y2 = P, 144, 556, 186
        self._round_rect(self.sel_x1, self.sel_y1, self.sel_x2, self.sel_y2, 10,
                         fill=C["field"], outline=C["border"], tags=("selector",))
        self.sel_text = cv.create_text(
            self.sel_x1 + 16, (self.sel_y1 + self.sel_y2) / 2,
            anchor="w", text="Procurando unidades…",
            fill=C["muted"], font=(FONT_UI, 12), tags=("selector",))
        cv.create_text(self.sel_x2 - 18, (self.sel_y1 + self.sel_y2) / 2,
                       text="▾", fill=C["accent"], font=(FONT_UI, 13, "bold"),
                       tags=("selector",))
        cv.tag_bind("selector", "<Enter>",
                    lambda e: cv.configure(cursor="pointinghand"))
        cv.tag_bind("selector", "<Leave>",
                    lambda e: cv.configure(cursor=""))
        cv.tag_bind("selector", "<Button-1>", self._toggle_dropdown)

        self._button("refresh", 568, 144, W - P, 186, "⟳  Atualizar", 12,
                     C["accent"], C["accent_dim"], C["accent_press"], "white",
                     self._refresh)

        # ── Section 2 — Modo de Instalação ────────────────────────────────────
        self._section(P, 208, "2", "Modo de Instalação")

        # NEW (active by default)
        self._button("mode_new", P, 230, 330, 272,
                     "⚠  Nova Instalação", 12,
                     C["accent"], C["accent_dim"], C["accent_press"], "white",
                     lambda: self._set_mode("new"), radius=10)
        # UPDATE (inactive by default)
        self._button("mode_update", 342, 230, 556, 272,
                     "↑  Atualização", 12,
                     C["field"], C["field_hover"], C["border"], C["muted"],
                     lambda: self._set_mode("update"), radius=10)
        # Exceção button (disabled in NEW mode)
        self._button("exclusion_add", 568, 230, W - P, 272,
                     "＋ Exceção", 12,
                     C["border"], C["border"], C["border"], C["muted"],
                     self._add_exclusion, radius=10)
        self._buttons["exclusion_add"]["enabled"] = False

        # Warning strip — NEW mode (data will be erased)
        self.warn_rect = self._round_rect(P, 280, W - P, 308, 8,
                                          fill="#FFF0ED", outline=C["orange"])
        self.warn_text = cv.create_text(
            P + 14, 294, anchor="w",
            text="⚠  ATENÇÃO: todos os dados do SD card serão APAGADOS permanentemente!",
            fill="#8B2500", font=(FONT_UI, 11, "bold"))

        # Exclusion display line — UPDATE mode (hidden initially)
        self.excl_text = cv.create_text(
            P + 2, 294, anchor="w",
            text="Nenhuma exceção definida.",
            fill=C["muted"], font=(FONT_UI, 11),
            state="hidden")

        # ── Section 3 — Status ────────────────────────────────────────────────
        self._section(P, 312, "3", "Status do Processo")

        log_y1, log_y2 = 334, 534
        self._round_rect(P, log_y1, W - P, log_y2, 10,
                         fill=C["term_bg"], outline=C["border"])
        self.log = tk.Text(cv, font=(FONT_MONO, 11), bg=C["term_bg"],
                           fg=C["term_fg"], insertbackground=C["term_fg"],
                           relief="flat", bd=0, padx=14, pady=12, wrap="word",
                           state="disabled", highlightthickness=0,
                           spacing1=1, spacing3=2)
        cv.create_window(P + 2, log_y1 + 2, anchor="nw", window=self.log,
                         width=(W - P) - P - 4, height=(log_y2 - log_y1) - 4)
        for tag, col, bold in [
            ("info",  C["term_fg"],    False),
            ("step",  C["term_cyan"],  True),
            ("ok",    "#9ECE6A",       True),
            ("warn",  C["term_amber"], False),
            ("err",   C["term_red"],   True),
            ("dim",   C["term_dim"],   False),
            ("white", C["term_white"], False),
        ]:
            self.log.tag_configure(
                tag, foreground=col,
                font=(FONT_MONO, 11, "bold") if bold else (FONT_MONO, 11))

        # ── Progress bar ──────────────────────────────────────────────────────
        self.pb_x1, self.pb_x2 = P, W - P
        self.pb_y1, self.pb_y2 = 542, 554
        self._round_rect(self.pb_x1, self.pb_y1, self.pb_x2, self.pb_y2, 6,
                         fill=C["field"], outline=C["field"])
        self.pb_fill = self._round_rect(
            self.pb_x1, self.pb_y1, self.pb_x1 + 1, self.pb_y2, 6,
            fill=C["green"], outline=C["green"])

        # ── Start button ──────────────────────────────────────────────────────
        self._button("start", P, 566, W - P, 624, "INICIAR PROCESSO", 15,
                     C["green"], C["green_hover"], C["green_press"], "white",
                     self._start)

    def _section(self, x, y, num, title):
        cv = self.canvas
        self._round_rect(x, y - 11, x + 26, y + 11, 6,
                         fill=C["accent"], outline=C["accent"])
        cv.create_text(x + 13, y, text=num, fill="white",
                       font=(FONT_UI, 12, "bold"))
        cv.create_text(x + 38, y, anchor="w", text=title, fill=C["text"],
                       font=(FONT_UI, 14, "bold"))

    # ── progress ──────────────────────────────────────────────────────────────

    def _set_progress(self, v):
        def apply():
            w = self.pb_x1 + max(1, (self.pb_x2 - self.pb_x1) * v / 100.0)
            self.canvas.coords(self.pb_fill, *self._round_pts(
                self.pb_x1, self.pb_y1, w, self.pb_y2, 6))
        self.after(0, apply)

    def _round_pts(self, x1, y1, x2, y2, r):
        return [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]

    # ── logging ───────────────────────────────────────────────────────────────

    def _log(self, msg, tag="info"):
        self.after(0, self._log_main, msg, tag)

    def _log_main(self, msg, tag):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    # ── mode toggle ───────────────────────────────────────────────────────────

    def _set_mode(self, mode):
        self._mode = mode
        if mode == "new":
            self._btn_repaint("mode_new",
                              C["accent"], C["accent_dim"], C["accent_press"], "white")
            self._btn_repaint("mode_update",
                              C["field"], C["field_hover"], C["border"], C["muted"])
            # Disable exclusion button
            self._btn_repaint("exclusion_add",
                              C["border"], C["border"], C["border"], C["muted"])
            self._buttons["exclusion_add"]["enabled"] = False
            # Show erase warning, hide exclusion text
            self.canvas.itemconfig(self.warn_rect, state="normal")
            self.canvas.itemconfig(self.warn_text, state="normal")
            self.canvas.itemconfig(self.excl_text, state="hidden")
        else:
            self._btn_repaint("mode_update",
                              C["orange"], C["orange_hover"], C["orange_press"], "white")
            self._btn_repaint("mode_new",
                              C["field"], C["field_hover"], C["border"], C["muted"])
            # Enable exclusion button
            self._btn_repaint("exclusion_add",
                              C["accent"], C["accent_dim"], C["accent_press"], "white")
            self._buttons["exclusion_add"]["enabled"] = True
            # Hide erase warning, show exclusion text
            self.canvas.itemconfig(self.warn_rect, state="hidden")
            self.canvas.itemconfig(self.warn_text, state="hidden")
            self.canvas.itemconfig(self.excl_text, state="normal")
            self.canvas.itemconfig(self.excl_text,
                                   fill=C["text"] if self._exclusions else C["muted"])

    # ── exclusion management ──────────────────────────────────────────────────

    def _add_exclusion(self):
        if self._mode != "update":
            return
        mount = self._find_mount_for_update(
            _dev_from_label(self._sel_label)) if self._sel_label else None
        initial = mount or os.path.expanduser("~")

        answer = messagebox.askquestion(
            "Tipo de exceção",
            "Selecionar uma PASTA para preservar?\n\n"
            "(Escolha 'Não' para selecionar um arquivo específico.)",
            icon="question")
        if answer == "yes":
            path = filedialog.askdirectory(
                title="Pasta a preservar durante atualização",
                initialdir=initial)
        else:
            path = filedialog.askopenfilename(
                title="Arquivo a preservar durante atualização",
                initialdir=initial)
        if not path:
            return

        rel = path
        if mount and path.startswith(mount):
            rel = os.path.relpath(path, mount).replace(os.sep, "/")
        rel = rel.strip("/")

        if rel and rel not in self._exclusions:
            self._exclusions.append(rel)
            self._update_exclusion_display()

    def _update_exclusion_display(self):
        if not self._exclusions:
            text = "Nenhuma exceção definida."
            color = C["muted"]
        else:
            shown = self._exclusions[:3]
            rest = len(self._exclusions) - len(shown)
            text = "Exceções: " + ", ".join(shown)
            if rest > 0:
                text += "  +{} mais".format(rest)
            color = C["text"]
        self.canvas.itemconfig(self.excl_text, text=text, fill=color)

    def _is_excluded(self, rel_path):
        norm = rel_path.replace("\\", "/").strip("/")
        for excl in self._exclusions:
            excl_norm = excl.replace(os.sep, "/").strip("/")
            if norm == excl_norm or norm.startswith(excl_norm + "/"):
                return True
        return False

    # ── changelog window ──────────────────────────────────────────────────────

    def _show_changelog(self):
        win = tk.Toplevel(self)
        win.title("Changelog — CNX Pack")
        win.geometry("680x540")
        win.configure(bg=C["term_bg"])
        win.resizable(True, True)

        # Header bar
        hdr = tk.Frame(win, bg=C["header"], height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📋  Histórico de Versões — CNX Pack",
                 bg=C["header"], fg="white",
                 font=(FONT_UI, 14, "bold"), anchor="w", padx=16).pack(
            side="left", fill="both", expand=True)

        # Scrollable text area
        frame = tk.Frame(win, bg=C["term_bg"])
        frame.pack(fill="both", expand=True)
        scroll = tk.Scrollbar(frame, bg=C["term_bg"])
        scroll.pack(side="right", fill="y")
        txt = tk.Text(frame, font=(FONT_MONO, 11), bg=C["term_bg"],
                      fg=C["term_white"], wrap="word",
                      padx=18, pady=14, state="disabled",
                      highlightthickness=0, yscrollcommand=scroll.set,
                      spacing1=2, spacing3=3)
        txt.pack(side="left", fill="both", expand=True)
        scroll.config(command=txt.yview)

        txt.tag_configure("sep",     foreground=C["term_dim"])
        txt.tag_configure("version", foreground=C["term_cyan"],
                          font=(FONT_MONO, 12, "bold"))
        txt.tag_configure("date",    foreground=C["term_dim"],
                          font=(FONT_MONO, 10))
        txt.tag_configure("body",    foreground=C["term_white"])

        def fetch():
            try:
                url = "https://api.github.com/repos/CostelaCNX/CNX/releases"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    releases = json.loads(resp.read())

                def render():
                    txt.configure(state="normal")
                    txt.delete("1.0", "end")
                    if not releases:
                        txt.insert("end", "Nenhum release encontrado.", "body")
                        txt.configure(state="disabled")
                        return
                    sep = "─" * 60 + "\n"
                    for rel in releases:
                        txt.insert("end", sep, "sep")
                        name = rel.get("name") or rel.get("tag_name", "")
                        tag  = rel.get("tag_name", "")
                        display = name if name and name != tag else tag
                        txt.insert("end", "  {}\n".format(display), "version")
                        date = (rel.get("published_at") or "")[:10]
                        if date:
                            txt.insert("end", "  {}\n\n".format(date), "date")
                        body = (rel.get("body") or "Sem notas de versão.")
                        # Normalize line endings
                        body = body.replace("\r\n", "\n").replace("\r", "\n").strip()
                        txt.insert("end", body + "\n\n", "body")
                    txt.insert("end", sep, "sep")
                    txt.configure(state="disabled")

                win.after(0, render)

            except Exception as e:
                def show_err():
                    txt.configure(state="normal")
                    txt.delete("1.0", "end")
                    txt.insert("end", "Erro ao carregar changelog:\n\n{}".format(e))
                    txt.configure(state="disabled")
                win.after(0, show_err)

        txt.configure(state="normal")
        txt.insert("end", "Carregando…")
        txt.configure(state="disabled")
        threading.Thread(target=fetch, daemon=True).start()

    # ── drive dropdown ────────────────────────────────────────────────────────

    def _toggle_dropdown(self, _=None):
        if self._dropdown is not None:
            self._close_dropdown()
            return
        if not self._drives:
            return
        rows = self._drives
        rowh = 36
        h = rowh * len(rows) + 4
        width = int(self.sel_x2 - self.sel_x1)
        x = self.winfo_rootx() + int(self.sel_x1)
        y = self.winfo_rooty() + int(self.sel_y2) + 4

        dd = tk.Toplevel(self)
        dd.overrideredirect(True)
        dd.geometry("{}x{}+{}+{}".format(width, h, x, y))
        dc = tk.Canvas(dd, width=width, height=h, bg=C["card"],
                       highlightthickness=1, highlightbackground=C["accent"])
        dc.pack(fill="both", expand=True)
        for i, (label, dev) in enumerate(rows):
            ry = 2 + i * rowh
            tag = "row{}".format(i)
            rect = dc.create_rectangle(2, ry, width - 2, ry + rowh,
                                       fill=C["card"], outline=C["card"], tags=(tag,))
            dc.create_text(14, ry + rowh / 2, anchor="w", text=label,
                           fill=C["text"], font=(FONT_UI, 12), tags=(tag,))
            dc.tag_bind(tag, "<Enter>",
                        lambda e, r=rect: dc.itemconfig(r, fill=C["field"],
                                                         outline=C["field"]))
            dc.tag_bind(tag, "<Leave>",
                        lambda e, r=rect: dc.itemconfig(r, fill=C["card"],
                                                         outline=C["card"]))
            dc.tag_bind(tag, "<Button-1>", lambda e, lab=label: self._pick(lab))
        dd.bind("<Escape>", lambda e: self._close_dropdown())
        self._dropdown = dd

    def _close_dropdown(self):
        if self._dropdown is not None:
            try:
                self._dropdown.destroy()
            except tk.TclError:
                pass
            self._dropdown = None

    def _maybe_close_dropdown(self, event):
        if self._dropdown is None:
            return
        items = self.canvas.find_withtag("selector")
        hit = self.canvas.find_withtag("current")
        if hit and hit[0] in items:
            return
        self._close_dropdown()

    def _pick(self, label):
        self._sel_label = label
        self.canvas.itemconfig(self.sel_text, text=label, fill=C["text"])
        self._close_dropdown()
        dev = _dev_from_label(label)
        if dev:
            self._log("→ Selecionado: {}".format(dev), "white")

    # ── refresh ───────────────────────────────────────────────────────────────

    def _refresh(self):
        self._close_dropdown()
        self._drives = list_removable_drives()
        if self._drives:
            self._pick(self._drives[0][0])
        else:
            self._sel_label = ""
            self.canvas.itemconfig(self.sel_text,
                                   text="Nenhuma unidade removível encontrada",
                                   fill=C["muted"])
            self._log("Nenhuma unidade removível encontrada.", "warn")
            self._log("Conecte o SD card e clique em Atualizar.", "dim")

    def _set_ui(self, enabled):
        for tag in ("start", "refresh", "changelog"):
            self._btn_enable(tag, enabled)
        self._btn_enable("mode_new", enabled)
        self._btn_enable("mode_update", enabled)
        if enabled:
            # Restore correct visual state for mode buttons and exclusion button
            self._set_mode(self._mode)
        else:
            self._btn_enable("exclusion_add", False)

    # ── install flow ──────────────────────────────────────────────────────────

    def _start(self):
        label = self._sel_label
        if not label:
            messagebox.showwarning("Atenção", "Selecione uma unidade primeiro.")
            return
        dev = _dev_from_label(label)
        if not dev:
            messagebox.showerror("Erro", "Não foi possível identificar a unidade.")
            return
        if dev in ("/dev/disk0", "/dev/disk1", "/dev/disk2", "/dev/disk3"):
            messagebox.showerror("Erro Crítico",
                                 "Disco interno detectado — operação bloqueada por segurança!")
            return

        if self._mode == "new":
            if not messagebox.askyesno(
                "Confirmar formatação",
                "A unidade {} será FORMATADA como FAT32.\n\n"
                "TODOS OS DADOS SERÃO APAGADOS PERMANENTEMENTE.\n\n"
                "Deseja continuar?".format(dev), icon="warning"):
                return
        else:
            excl_info = ""
            if self._exclusions:
                lines = "\n".join("  • " + e for e in self._exclusions)
                excl_info = "\n\nExceções preservadas ({}):\n{}".format(
                    len(self._exclusions), lines)
            if not messagebox.askyesno(
                "Confirmar atualização",
                "O CNX Pack será atualizado na unidade {}.\n\n"
                "Dados existentes serão preservados.{}".format(dev, excl_info),
                icon="question"):
                return

        self._set_ui(False)
        self._set_progress(0)
        threading.Thread(target=self._run, args=(dev,), daemon=True).start()

    def _run(self, dev):
        try:
            self._install(dev)
        except Exception as e:
            self._log("", "info")
            self._log("✕  ERRO: {}".format(e), "err")
            self.after(0, lambda: messagebox.showerror(
                "Erro", "Falha no processo:\n\n{}\n\n"
                "Verifique a unidade e tente novamente.".format(e)))
        finally:
            self.after(0, lambda: self._set_ui(True))

    def _install(self, dev):
        if self._mode == "new":
            self._install_new(dev)
        else:
            self._install_update(dev)

    # ── mode: nova instalação ─────────────────────────────────────────────────

    def _install_new(self, dev):
        # 1 — format
        self._log("", "info")
        self._log("[1/4]  Formatando {} como FAT32 (MBR)…".format(dev), "step")
        # MBRFormat is required: Switch/modchips only boot from MBR partition scheme.
        r = subprocess.run(
            ["diskutil", "eraseDisk", "FAT32", "SWITCH SD", "MBRFormat", dev],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or "diskutil eraseDisk falhou")
        self._log("   ✓ Formatação concluída", "ok")
        self._set_progress(10)

        mount = self._find_mount(dev)
        if not mount:
            raise RuntimeError("A unidade não montou após a formatação.")
        self._log("   ↳ Montado em: {}".format(mount), "dim")
        self._set_progress(15)

        # 2 — download
        zip_data = self._download_cnx("[2/4]", base=15)
        self._set_progress(83)

        # 3 — extract
        self._log("", "info")
        self._log("[3/4]  Extraindo arquivos para o SD card…", "step")
        _extract_zip(zip_data, mount, self._log)
        self._log("   ✓ Extração concluída", "ok")
        self._set_progress(92)

        # 4 — hidden zip
        self._log("", "info")
        self._log("[4/4]  Verificando pacote oculto…", "step")
        _extract_hidden_zip(mount, self._log)
        self._log("   ✓ Verificação concluída", "ok")
        self._set_progress(100)

        self._log("", "info")
        self._log("✓  CONCLUÍDO! SD card pronto para uso.", "ok")
        self._log("   Pode remover o cartão com segurança.", "dim")
        self.after(0, lambda: messagebox.showinfo(
            "Sucesso 🎉",
            "CNX Pack instalado com sucesso em {}!\n\n"
            "Você já pode remover o SD card com segurança.".format(dev)))

    # ── mode: atualização ─────────────────────────────────────────────────────

    def _install_update(self, dev):
        # 1 — find existing mount (no format)
        self._log("", "info")
        self._log("[1/3]  Localizando SD card montado…", "step")
        mount = self._find_mount_for_update(dev)
        if not mount:
            raise RuntimeError(
                "SD card não encontrado/montado.\n"
                "Verifique se o cartão está inserido e montado.")
        self._log("   ↳ Montado em: {}".format(mount), "dim")
        if self._exclusions:
            self._log("   ↳ {} exceção(ões) configurada(s)".format(
                len(self._exclusions)), "dim")
        self._set_progress(10)

        # 2 — download
        zip_data = self._download_cnx("[2/3]", base=10)
        self._set_progress(83)

        # 3 — smart extract
        self._log("", "info")
        self._log("[3/3]  Atualizando arquivos (preservando exceções)…", "step")
        self._smart_extract_zip(zip_data, mount)
        self._log("   ✓ Atualização concluída", "ok")
        self._set_progress(94)

        # Hidden zip (part of CNX pack — still extract on update)
        _extract_hidden_zip(mount, self._log)
        self._set_progress(100)

        self._log("", "info")
        self._log("✓  ATUALIZAÇÃO CONCLUÍDA! Saves e configurações preservados.", "ok")
        self.after(0, lambda: messagebox.showinfo(
            "Sucesso 🎉",
            "CNX Pack atualizado com sucesso em {}!\n\n"
            "Saves e configurações foram preservados.".format(dev)))

    # ── shared download helper ────────────────────────────────────────────────

    def _download_cnx(self, step_label, base=15):
        """Download CNX pack from REPOS; returns raw bytes. `base` = progress %."""
        self._log("", "info")
        self._log("{}  Baixando o CNX Pack…".format(step_label), "step")
        zip_data = None
        for repo in REPOS:
            try:
                url, tag = _zip_url(repo)
                self._log("   ↳ {} ({})".format(repo, tag), "dim")
                last = [0]
                def cb(done, total, lp=last, b=base):
                    self._set_progress(b + int((done / total) * (83 - b)))
                    pct = int((done / total) * 100)
                    if pct >= lp[0] + 5:
                        lp[0] = pct
                        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                        self._log("   {} {:>3}%  ({:.0f}/{:.0f} MB)".format(
                            bar, pct, done / 1e6, total / 1e6), "info")
                zip_data = _download(url, cb)
                self._log("   ✓ Download concluído — {:.1f} MB".format(
                    len(zip_data) / 1e6), "ok")
                break
            except Exception as e:
                self._log("   ! Falha em {}: {}".format(repo, e), "warn")
                if repo != REPOS[-1]:
                    self._log("   ↳ Tentando repositório de backup…", "dim")
        if not zip_data:
            raise RuntimeError("Falha no download em todos os repositórios.")
        return zip_data

    def _smart_extract_zip(self, data, dest):
        """Extract zip skipping paths that match self._exclusions."""
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            skipped, extracted = 0, 0
            for name in names:
                if self._is_excluded(name):
                    skipped += 1
                    continue
                try:
                    zf.extract(name, dest)
                    extracted += 1
                except Exception as e:
                    self._log("   ! {} — {}".format(name, e), "warn")
            self._log("   {} atualizados, {} preservados".format(
                extracted, skipped), "dim")

    # ── mount helpers ─────────────────────────────────────────────────────────

    def _find_mount(self, dev):
        """Mount point after formatting (SWITCH SD label)."""
        for part in ("s2", "s1"):
            try:
                r = subprocess.run(["diskutil", "info", "-plist", dev + part],
                                   capture_output=True)
                mp = plistlib.loads(r.stdout).get("MountPoint")
                if mp and os.path.isdir(mp):
                    return mp
            except Exception:
                pass
        if os.path.isdir("/Volumes/SWITCH SD"):
            return "/Volumes/SWITCH SD"
        return None

    def _find_mount_for_update(self, dev):
        """Mount point of an already-mounted drive (any volume name)."""
        if not dev:
            return None
        disk_id = dev.replace("/dev/", "")
        for part in ("s1", "s2", "s3", "s4"):
            try:
                r = subprocess.run(["diskutil", "info", "-plist", dev + part],
                                   capture_output=True)
                d = plistlib.loads(r.stdout)
                mp = d.get("MountPoint")
                if mp and os.path.isdir(mp):
                    return mp
            except Exception:
                pass
        # Try the disk node itself
        try:
            r = subprocess.run(["diskutil", "info", "-plist", dev],
                               capture_output=True)
            d = plistlib.loads(r.stdout)
            mp = d.get("MountPoint")
            if mp and os.path.isdir(mp):
                return mp
        except Exception:
            pass
        # Scan /Volumes for a partition belonging to this disk
        try:
            for vol in os.listdir("/Volumes"):
                vpath = os.path.join("/Volumes", vol)
                r2 = subprocess.run(["diskutil", "info", "-plist", vpath],
                                    capture_output=True)
                d2 = plistlib.loads(r2.stdout)
                did = d2.get("DeviceIdentifier", "")
                if did.startswith(disk_id):
                    return vpath
        except Exception:
            pass
        return None


if __name__ == "__main__":
    App().mainloop()
