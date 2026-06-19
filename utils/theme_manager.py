"""
utils/theme_manager.py
──────────────────────
ThemeManager: المدير المركزي لكل إعدادات المظهر.
- يحفظ/يقرأ الإعدادات من JSON
- يطبّق التغييرات فوراً على ttk.Style وكل Treeview مسجّل
- يمكن توسيعه مستقبلاً بإضافة عناصر جديدة في SCHEMA فقط
"""

import json
import os
import copy
from tkinter import ttk
import tkinter as tk

# ─────────────────────────────────────────────────────────────
# مسار ملف الحفظ
# ─────────────────────────────────────────────────────────────
import sys as _sys
if getattr(_sys, 'frozen', False):
    _BASE_DIR = os.environ.get("PHARMACY_DATA_DIR", os.path.dirname(_sys.executable))
else:
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME_FILE = os.path.join(_BASE_DIR, "assets", "theme_custom.json")


# ─────────────────────────────────────────────────────────────
# القيم الافتراضية لكل عنصر (dark mode)
# ─────────────────────────────────────────────────────────────
DEFAULT_THEME = {
    "meta": {
        "name":    "افتراضي داكن",
        "version": "1.0",
    },
    "global": {
        "font_family":  "Segoe UI",
        "accent_color": "#2563eb",
    },
    "treeview": {
        "row_height":        30,
        "font_family":       "Segoe UI",
        "font_size":         11,
        "bg":                "#111827",
        "fg":                "#f1f5f9",
        "heading_bg":        "#1f2937",
        "heading_fg":        "#f1f5f9",
        "heading_font_bold": True,
        "selected_bg":       "#2563eb",
        "selected_fg":       "#ffffff",
        "zebra":             True,
        "odd_row_bg":        "#111827",
        "odd_row_fg":        "#f1f5f9",
        "even_row_bg":       "#172033",
        "even_row_fg":       "#f1f5f9",
        "low_fg":            "#f59e0b",
        "out_fg":            "#ef4444",
    },
    "notebook": {
        "tab_bg":           "#1f2937",
        "tab_fg":           "#f1f5f9",
        "tab_selected_bg":  "#2563eb",
        "tab_selected_fg":  "#ffffff",
        "tab_padding_x":    14,
        "tab_padding_y":    8,
        "font_size":        11,
        "font_bold":        True,
    },
    "combobox": {
        "field_bg":   "#0b1220",
        "fg":         "#f1f5f9",
        "font_size":  11,
        "font_bold":  True,
        "arrow_size": 14,
    },
    "button": {
        "bg":         "#2563eb",
        "fg":         "#ffffff",
        "hover_bg":   "#1d4ed8",
        "font_size":  11,
        "font_bold":  False,
        "padding_x":  10,
        "padding_y":  5,
        "relief":     "flat",
    },
    "label": {
        "bg":        "#111827",
        "fg":        "#f1f5f9",
        "font_size": 11,
        "font_bold": False,
    },
    "entry": {
        "bg":           "#0b1220",
        "fg":           "#f1f5f9",
        "border_color": "#334155",
        "font_size":    11,
    },
    "scrollbar": {
        "bg":     "#1f2937",
        "trough": "#111827",
        "arrow":  "#f1f5f9",
    },
}


# ─────────────────────────────────────────────────────────────
# ThemeManager
# ─────────────────────────────────────────────────────────────
class ThemeManager:
    """
    Singleton — استخدم ThemeManager.instance() للوصول.
    """
    _instance = None

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if ThemeManager._instance is not None:
            raise RuntimeError("Use ThemeManager.instance()")
        self._theme: dict   = copy.deepcopy(DEFAULT_THEME)
        self._trees: list   = []          # قائمة Treeview مسجّلة
        self._callbacks: list = []        # دوال تُستدعى عند كل تحديث
        os.makedirs(os.path.dirname(THEME_FILE), exist_ok=True)
        self.load()

    # ── حفظ / قراءة ────────────────────────────────────────
    def load(self):
        if os.path.isfile(THEME_FILE):
            try:
                with open(THEME_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._deep_update(self._theme, saved)
            except Exception:
                pass

    def save(self):
        with open(THEME_FILE, "w", encoding="utf-8") as f:
            json.dump(self._theme, f, ensure_ascii=False, indent=2)

    def reset_to_defaults(self):
        self._theme = copy.deepcopy(DEFAULT_THEME)
        if os.path.isfile(THEME_FILE):
            os.remove(THEME_FILE)
        self.apply()

    # ── getter / setter ─────────────────────────────────────
    def get(self, section: str, key: str, fallback=None):
        return self._theme.get(section, {}).get(key, fallback)

    def set(self, section: str, key: str, value):
        if section not in self._theme:
            self._theme[section] = {}
        self._theme[section][key] = value

    def get_section(self, section: str) -> dict:
        return copy.deepcopy(self._theme.get(section, {}))

    def update_section(self, section: str, data: dict):
        if section not in self._theme:
            self._theme[section] = {}
        self._theme[section].update(data)

    # ── تسجيل Treeview ──────────────────────────────────────
    def register_tree(self, tree: ttk.Treeview):
        """سجّل Treeview ليتلقى التحديثات التلقائية."""
        if tree not in self._trees:
            self._trees.append(tree)

    def unregister_tree(self, tree: ttk.Treeview):
        if tree in self._trees:
            self._trees.remove(tree)

    def register_callback(self, fn):
        """سجّل دالة تُستدعى عند كل apply()."""
        if fn not in self._callbacks:
            self._callbacks.append(fn)

    # ── تطبيق الثيم ─────────────────────────────────────────
    def apply(self):
        """طبّق كل إعدادات الثيم الحالية على ttk.Style وكل الـ Treeview."""
        root = tk._default_root
        if root is None:
            return
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        self._apply_treeview_global(style)
        self._apply_notebook(style)
        self._apply_combobox(style, root)
        self._apply_scrollbar(style)
        self._apply_label(style)

        # تحديث كل Treeview مسجّل
        active = []
        for tree in self._trees:
            try:
                if tree.winfo_exists():
                    self._apply_tree_widget(style, tree)
                    active.append(tree)
            except Exception:
                pass
        self._trees = active

        # استدعاء الـ callbacks
        for cb in self._callbacks:
            try:
                cb()
            except Exception:
                pass

    def apply_to_tree(self, tree: ttk.Treeview):
        """طبّق على Treeview واحد وسجّله."""
        self.register_tree(tree)
        style = ttk.Style()
        self._apply_tree_widget(style, tree)

    # ── تطبيق مقسَّم ────────────────────────────────────────
    def _apply_treeview_global(self, style: ttk.Style):
        tv = self.get_section("treeview")
        ff = tv.get("font_family", "Segoe UI")
        fs = tv.get("font_size",   11)
        bold = ("bold",) if tv.get("heading_font_bold", True) else ()
        style.configure("Treeview",
                        background=tv["bg"],
                        fieldbackground=tv["bg"],
                        foreground=tv["fg"],
                        rowheight=tv["row_height"],
                        font=(ff, fs))
        style.configure("Treeview.Heading",
                        background=tv["heading_bg"],
                        foreground=tv["heading_fg"],
                        relief="flat",
                        font=(ff, fs) + bold)
        style.map("Treeview",
                  background=[("selected", tv["selected_bg"])],
                  foreground=[("selected", tv["selected_fg"])])
        style.map("Treeview.Heading",
                  background=[("active", tv.get("selected_bg","#2563eb"))],
                  foreground=[("active", "#ffffff")])

    def _apply_tree_widget(self, style: ttk.Style, tree: ttk.Treeview):
        tv  = self.get_section("treeview")
        ff  = tv.get("font_family", "Segoe UI")
        fs  = tv.get("font_size",   11)
        bold= ("bold",) if tv.get("heading_font_bold", True) else ()

        uid = f"TV{id(tree)}.Treeview"
        style.configure(uid,
                        background=tv["bg"],
                        fieldbackground=tv["bg"],
                        foreground=tv["fg"],
                        rowheight=tv["row_height"],
                        font=(ff, fs))
        style.configure(f"{uid}.Heading",
                        background=tv["heading_bg"],
                        foreground=tv["heading_fg"],
                        relief="flat",
                        font=(ff, fs) + bold)
        style.map(uid,
                  background=[("selected", tv["selected_bg"])],
                  foreground=[("selected", tv["selected_fg"])])
        tree.configure(style=uid)

        # tag colors
        if tv.get("zebra", True):
            tree.tag_configure("oddrow",  background=tv["odd_row_bg"],
                                           foreground=tv["odd_row_fg"])
            tree.tag_configure("evenrow", background=tv["even_row_bg"],
                                           foreground=tv["even_row_fg"])
        else:
            tree.tag_configure("oddrow",  background=tv["bg"], foreground=tv["fg"])
            tree.tag_configure("evenrow", background=tv["bg"], foreground=tv["fg"])

        tree.tag_configure("ok",  background=tv["bg"],    foreground=tv["fg"])
        tree.tag_configure("low", background=tv["bg"],    foreground=tv.get("low_fg","#f59e0b"))
        tree.tag_configure("out", background=tv["bg"],    foreground=tv.get("out_fg","#ef4444"))
        tree.tag_configure("selected_row",
                           background=tv["selected_bg"], foreground=tv["selected_fg"])

    def _apply_notebook(self, style: ttk.Style):
        nb = self.get_section("notebook")
        fs   = nb.get("font_size", 11)
        ff   = self.get("global", "font_family", "Segoe UI")
        bold = "bold" if nb.get("font_bold", True) else "normal"
        style.configure("TNotebook",
                        background=nb["tab_bg"], borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=nb["tab_bg"],
                        foreground=nb["tab_fg"],
                        padding=(nb["tab_padding_x"], nb["tab_padding_y"]),
                        font=(ff, fs, bold))
        style.map("TNotebook.Tab",
                  background=[("selected", nb["tab_selected_bg"])],
                  foreground=[("selected", nb["tab_selected_fg"])])

    def _apply_combobox(self, style: ttk.Style, root):
        cb = self.get_section("combobox")
        ff   = self.get("global", "font_family", "Segoe UI")
        fs   = cb.get("font_size", 11)
        bold = "bold" if cb.get("font_bold", True) else "normal"
        font = (ff, fs, bold)
        style.configure("TCombobox",
                        fieldbackground=cb["field_bg"],
                        background=cb["field_bg"],
                        foreground=cb["fg"],
                        selectforeground=cb["fg"],
                        selectbackground=cb["field_bg"],
                        arrowsize=cb.get("arrow_size", 14),
                        font=font)
        style.map("TCombobox",
                  fieldbackground=[("readonly", cb["field_bg"])],
                  foreground=[("readonly", cb["fg"])],
                  selectbackground=[("readonly", cb["field_bg"])],
                  selectforeground=[("readonly", cb["fg"])])
        accent = self.get("global", "accent_color", "#2563eb")
        root.option_add("*TCombobox*Listbox.foreground",        cb["fg"])
        root.option_add("*TCombobox*Listbox.background",        cb["field_bg"])
        root.option_add("*TCombobox*Listbox.selectForeground",  "#ffffff")
        root.option_add("*TCombobox*Listbox.selectBackground",  accent)
        root.option_add("*TCombobox*Listbox.font",              font)

    def _apply_scrollbar(self, style: ttk.Style):
        sb = self.get_section("scrollbar")
        style.configure("TScrollbar",
                        background=sb["bg"],
                        troughcolor=sb["trough"],
                        bordercolor=sb["trough"],
                        arrowcolor=sb["arrow"])

    def _apply_label(self, style: ttk.Style):
        lb = self.get_section("label")
        style.configure("TFrame", background=lb["bg"])
        style.configure("TLabel", background=lb["bg"], foreground=lb["fg"])

    # ── helper ──────────────────────────────────────────────
    @staticmethod
    def _deep_update(base: dict, override: dict):
        for k, v in override.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                ThemeManager._deep_update(base[k], v)
            else:
                base[k] = v
