import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk


_APPEARANCE_MODE = "dark"
_THEME_NAME = "blue"
_THEME_ACCENT = "#2563eb"

# ── Treeview global font/size (يُستخدم في apply_treeview_style) ──
_TV_ROW_HEIGHT  = 30
_TV_FONT_FAMILY = "Segoe UI"
_TV_FONT_SIZE   = 11

_PALETTE = {
    "dark": {
        "window":  "#0f172a",
        "surface": "#111827",
        "panel":   "#1f2937",
        "entry":   "#0b1220",
        "text":    "#f1f5f9",      # فاتح واضح على الخلفية الداكنة
        "muted":   "#94a3b8",
        "border":  "#334155",
        "tree_bg": "#111827",
        "tree_row_alt": "#172033",
    },
    "light": {
        "window":  "#f8fafc",
        "surface": "#ffffff",
        "panel":   "#f1f5f9",
        "entry":   "#ffffff",
        "text":    "#0f172a",      # داكن واضح على الخلفية الفاتحة
        "muted":   "#6b7280",
        "border":  "#cbd5e1",
        "tree_bg": "#ffffff",
        "tree_row_alt": "#f8fafc",
    },
}

_THEMES = {
    "blue":      "#2563eb",
    "green":     "#059669",
    "dark-blue": "#1d4ed8",
}


def _is_dark():
    return _APPEARANCE_MODE != "light"


def _palette():
    return _PALETTE["dark" if _is_dark() else "light"]


def _resolve_color(value, fallback=None, master=None):
    if value is None:
        return fallback
    if value == "transparent":
        if master is not None:
            try:
                return master.cget("bg")
            except Exception:
                pass
        return fallback
    if isinstance(value, (tuple, list)):
        if not value:
            return fallback
        if len(value) == 1:
            return value[0]
        return value[1] if _is_dark() else value[0]
    return value


def _apply_ttk_style():
    root = tk._default_root
    if root is None:
        return
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    colors = _palette()
    accent = _THEME_ACCENT
    tv_font        = (_TV_FONT_FAMILY, _TV_FONT_SIZE)
    tv_font_bold   = (_TV_FONT_FAMILY, _TV_FONT_SIZE, "bold")
    combo_font     = (_TV_FONT_FAMILY, _TV_FONT_SIZE, "bold")

    # ── Frame / Label ──
    style.configure("TFrame",  background=colors["surface"])
    style.configure("TLabel",  background=colors["surface"], foreground=colors["text"])

    # ── Notebook (Tabs) ──
    style.configure("TNotebook",     background=colors["surface"], borderwidth=0)
    style.configure("TNotebook.Tab", background=colors["panel"],
                    foreground=colors["text"], padding=(14, 8),
                    font=(_TV_FONT_FAMILY, 11, "bold"))
    style.map("TNotebook.Tab",
              background=[("selected", accent)],
              foreground=[("selected", "#ffffff")])

    # ── Treeview ── (مركزي - لا تضع style.configure في الشاشات)
    style.configure("Treeview",
                    background=colors["tree_bg"],
                    fieldbackground=colors["tree_bg"],
                    foreground=colors["text"],       # ← اللون الرئيسي للنص
                    bordercolor=colors["border"],
                    rowheight=_TV_ROW_HEIGHT,
                    font=tv_font)
    style.configure("Treeview.Heading",
                    background=colors["panel"],
                    foreground=colors["text"],
                    relief="flat",
                    font=tv_font_bold)
    style.map("Treeview",
              background=[("selected", accent)],
              foreground=[("selected", "#ffffff")])
    style.map("Treeview.Heading",
              background=[("active", accent)],
              foreground=[("active", "#ffffff")])

    # ── Combobox (CTkOptionMenu) ──
    style.configure("TCombobox",
                    fieldbackground=colors["entry"],
                    background=colors["entry"],
                    foreground=colors["text"],
                    selectforeground=colors["text"],
                    selectbackground=colors["entry"],
                    arrowsize=14,
                    font=combo_font)
    style.map("TCombobox",
              fieldbackground=[("readonly", colors["entry"])],
              foreground=[("readonly", colors["text"])],
              selectbackground=[("readonly", colors["entry"])],
              selectforeground=[("readonly", colors["text"])])

    # ── Scrollbar ──
    style.configure("TScrollbar",
                    background=colors["panel"],
                    troughcolor=colors["surface"],
                    bordercolor=colors["surface"],
                    arrowcolor=colors["text"])

    # ── Listbox داخل Combobox dropdown ──
    root.option_add("*TCombobox*Listbox.foreground",  colors["text"])
    root.option_add("*TCombobox*Listbox.background",  colors["entry"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox.selectBackground", accent)
    root.option_add("*TCombobox*Listbox.font",        combo_font)


def apply_treeview_style():
    """
    استدعِها مباشرةً بعد إنشاء أي Treeview بدلاً من كتابة ttk.Style() في كل شاشة.
    تضمن أن ألوان الوضع الحالي (dark/light) مُطبَّقة بشكل صحيح.
    """
    _apply_ttk_style()

def configure_treeview(tree):
    """
    اطلبها بعد إنشاء أي ttk.Treeview.
    تضمن ألوان dark/light صحيحة حتى على Windows + صفوف متناوبة.
    تُسجّل الـ tree في ThemeManager تلقائياً.
    """
    try:
        from utils.theme_manager import ThemeManager
        ThemeManager.instance().apply_to_tree(tree)
        return  # ThemeManager يتولى كل شيء
    except Exception:
        pass  # fallback للكود القديم لو ThemeManager غير متاح
    _apply_ttk_style()
    colors = _palette()

    # ── أسلوب فريد لكل widget لضمان عدم التجاوز من الثيم ──
    from tkinter import ttk
    style = ttk.Style()
    uid = f"TV{id(tree)}.Treeview"
    style.configure(uid,
                    background=colors["tree_bg"],
                    fieldbackground=colors["tree_bg"],
                    foreground=colors["text"],
                    rowheight=_TV_ROW_HEIGHT,
                    font=(_TV_FONT_FAMILY, _TV_FONT_SIZE))
    style.configure(f"{uid}.Heading",
                    background=colors["panel"],
                    foreground=colors["text"],
                    relief="flat",
                    font=(_TV_FONT_FAMILY, _TV_FONT_SIZE, "bold"))
    style.map(uid,
              background=[("selected", _THEME_ACCENT)],
              foreground=[("selected", "#ffffff")])
    tree.configure(style=uid)

    # ── ألوان الصفوف والتاجات ──
    tree.tag_configure("oddrow",  background=colors["tree_bg"],      foreground=colors["text"])
    tree.tag_configure("evenrow", background=colors["tree_row_alt"],  foreground=colors["text"])
    tree.tag_configure("ok",      background=colors["tree_bg"],       foreground=colors["text"])
    tree.tag_configure("low",     background=colors["tree_bg"],       foreground="#f59e0b")
    tree.tag_configure("out",     background=colors["tree_bg"],       foreground="#ef4444")
    tree.tag_configure("selected_row", background=_THEME_ACCENT,     foreground="#ffffff")



def set_appearance_mode(mode):
    global _APPEARANCE_MODE
    _APPEARANCE_MODE = "light" if str(mode).lower() == "light" else "dark"
    _apply_ttk_style()


def set_default_color_theme(theme):
    global _THEME_NAME, _THEME_ACCENT
    _THEME_NAME = theme
    _THEME_ACCENT = _THEMES.get(theme, _THEMES["blue"])
    _apply_ttk_style()


# ── kept for backward compat (no-op) ──
def set_combobox_text_color(color):
    _apply_ttk_style()

def set_combobox_bold(is_bold):
    _apply_ttk_style()


# ─────────────────────────────────────────
# Font helper
# ─────────────────────────────────────────
def CTkFont(size=12, weight="normal", family="Segoe UI", slant="roman", underline=0):
    return tkfont.Font(family=family, size=size, weight=weight,
                       slant=slant, underline=underline)


# ─────────────────────────────────────────
# Var aliases
# ─────────────────────────────────────────
StringVar  = tk.StringVar
BooleanVar = tk.BooleanVar
IntVar     = tk.IntVar
DoubleVar  = tk.DoubleVar


# ─────────────────────────────────────────
# Grid mixin
# ─────────────────────────────────────────
class _GridMixin:
    def grid_columnconfigure(self, index, **kwargs):
        if isinstance(index, (tuple, list)):
            for i in index:
                super().grid_columnconfigure(i, **kwargs)
            return
        return super().grid_columnconfigure(index, **kwargs)

    def grid_rowconfigure(self, index, **kwargs):
        if isinstance(index, (tuple, list)):
            for i in index:
                super().grid_rowconfigure(i, **kwargs)
            return
        return super().grid_rowconfigure(index, **kwargs)


# ─────────────────────────────────────────
# CTk / CTkToplevel
# ─────────────────────────────────────────
class CTk(_GridMixin, tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_ttk_style()
        self.configure(bg=_palette()["window"])

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        fg_color = kwargs.pop("fg_color", None)
        if fg_color is not None:
            kwargs["bg"] = _resolve_color(fg_color, _palette()["window"], self)
        return super().configure(**kwargs)

    config = configure


class CTkToplevel(_GridMixin, tk.Toplevel):
    def __init__(self, master=None, *args, **kwargs):
        self._requested_fg_color = kwargs.pop("fg_color", None)
        super().__init__(master, *args, **kwargs)
        self.configure(bg=_resolve_color(
            self._requested_fg_color, _palette()["window"], master))

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        fg_color = kwargs.pop("fg_color", None)
        if fg_color is not None:
            kwargs["bg"] = _resolve_color(fg_color, _palette()["window"], self.master)
        return super().configure(**kwargs)

    config = configure


# ─────────────────────────────────────────
# CTkFrame
# ─────────────────────────────────────────
class CTkFrame(_GridMixin, tk.Frame):
    def __init__(self, master=None, *args, **kwargs):
        fg_color = kwargs.pop("fg_color", None)
        kwargs.pop("corner_radius", None)
        width  = kwargs.pop("width",  None)
        height = kwargs.pop("height", None)
        bg = _resolve_color(fg_color, _palette()["surface"], master)
        if width  is not None: kwargs["width"]  = width
        if height is not None: kwargs["height"] = height
        super().__init__(master, *args, bg=bg, **kwargs)
        self._bg = bg

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        fg_color = kwargs.pop("fg_color", None)
        if fg_color is not None:
            kwargs["bg"] = _resolve_color(fg_color, self._bg, self.master)
        return super().configure(**kwargs)

    config = configure


# ─────────────────────────────────────────
# CTkLabel
# ─────────────────────────────────────────
class CTkLabel(_GridMixin, tk.Label):
    def __init__(self, master=None, *args, **kwargs):
        text_color = kwargs.pop("text_color", None)
        fg_color   = kwargs.pop("fg_color",   None)
        kwargs.pop("corner_radius", None)
        try:
            parent_bg = master.cget("bg")
        except Exception:
            parent_bg = _palette()["surface"]
        bg = _resolve_color(fg_color, parent_bg, master)
        fg = _resolve_color(text_color, _palette()["text"], master)
        super().__init__(master, *args, bg=bg, fg=fg, **kwargs)
        self._bg = bg
        self._fg = fg

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if "fg_color"   in kwargs:
            kwargs["bg"] = _resolve_color(kwargs.pop("fg_color"), self._bg, self.master)
        if "text_color" in kwargs:
            kwargs["fg"] = _resolve_color(kwargs.pop("text_color"), self._fg, self.master)
        return super().configure(**kwargs)

    config = configure


# ─────────────────────────────────────────
# CTkButton
# ─────────────────────────────────────────
class CTkButton(_GridMixin, tk.Button):
    def __init__(self, master=None, *args, **kwargs):
        fg_color    = kwargs.pop("fg_color",    None)
        hover_color = kwargs.pop("hover_color", None)
        text_color  = kwargs.pop("text_color",  None)
        kwargs.pop("corner_radius", None)
        width  = kwargs.pop("width",  None)
        height = kwargs.pop("height", None)
        bg  = _resolve_color(fg_color,    _THEME_ACCENT, master)
        fg  = _resolve_color(text_color,  "#ffffff",     master)
        hbg = _resolve_color(hover_color, bg,            master)
        # height → pady تقريباً (tk.Button يقيس الارتفاع بعدد الأسطر)
        btn_pady = 4
        if height is not None:
            btn_pady = max(2, (height - 22) // 2)
        if width is not None: kwargs["width"] = width
        super().__init__(master, *args,
                         bg=bg, fg=fg,
                         activebackground=hbg, activeforeground=fg,
                         relief="flat", borderwidth=0, cursor="hand2",
                         padx=10, pady=btn_pady,
                         **kwargs)
        self._base_bg  = bg
        self._hover_bg = hbg
        self._base_fg  = fg
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _):
        if str(self["state"]) != "disabled":
            super().configure(bg=self._hover_bg)

    def _on_leave(self, _):
        if str(self["state"]) != "disabled":
            super().configure(bg=self._base_bg)

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if "fg_color" in kwargs:
            self._base_bg = _resolve_color(kwargs.pop("fg_color"), self._base_bg, self.master)
            kwargs["bg"] = self._base_bg
        if "hover_color" in kwargs:
            self._hover_bg = _resolve_color(kwargs.pop("hover_color"), self._hover_bg, self.master)
            kwargs["activebackground"] = self._hover_bg
        if "text_color" in kwargs:
            self._base_fg = _resolve_color(kwargs.pop("text_color"), self._base_fg, self.master)
            kwargs["fg"] = self._base_fg
            kwargs["activeforeground"] = self._base_fg
        return super().configure(**kwargs)

    config = configure


# ─────────────────────────────────────────
# CTkEntry
# ─────────────────────────────────────────
class CTkEntry(_GridMixin, tk.Entry):
    def __init__(self, master=None, *args, **kwargs):
        text_color = kwargs.pop("text_color",      None)
        fg_color   = kwargs.pop("fg_color",        None)
        kwargs.pop("placeholder_text", None)
        # نأخذ font من المستدعي لو موجود، وإلا نستخدم الافتراضي
        caller_font = kwargs.pop("font", None)
        width  = kwargs.pop("width",  None)
        height = kwargs.pop("height", None)
        kwargs.pop("corner_radius", None)
        bg = _resolve_color(fg_color,    _palette()["entry"], master)
        fg = _resolve_color(text_color,  _palette()["text"],  master)
        # font: نستخدم font المستدعي لو موجود، وإلا الافتراضي
        entry_font = caller_font if caller_font is not None else (_TV_FONT_FAMILY, _TV_FONT_SIZE)
        ipady = 0
        if height is not None:
            # tk.Entry لا يدعم height مباشرة - نحوّله لـ ipady
            ipady = max(0, (height - 22) // 2)
        if width is not None: kwargs["width"] = width
        super().__init__(master, *args,
                         bg=bg, fg=fg,
                         insertbackground=fg,
                         relief="solid", borderwidth=1,
                         highlightthickness=1,
                         highlightbackground=_palette()["border"],
                         highlightcolor=_THEME_ACCENT,
                         font=entry_font,
                         **kwargs)
        self._bg    = bg
        self._fg    = fg
        self._ipady = ipady
        # نطبق ipady عبر pack/grid بعد الإنشاء مش ممكن مباشرة
        # لكن نحفظها للاستخدام في الـ pack wrapper
        if ipady > 0:
            self.configure(highlightthickness=1)  # force redraw

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if "fg_color" in kwargs:
            self._bg = _resolve_color(kwargs.pop("fg_color"), self._bg, self.master)
            kwargs["bg"] = self._bg
        if "text_color" in kwargs:
            self._fg = _resolve_color(kwargs.pop("text_color"), self._fg, self.master)
            kwargs["fg"] = self._fg
            kwargs["insertbackground"] = self._fg
        return super().configure(**kwargs)

    config = configure


# ─────────────────────────────────────────
# CTkCheckBox
# ─────────────────────────────────────────
class CTkCheckBox(_GridMixin, tk.Checkbutton):
    def __init__(self, master=None, *args, **kwargs):
        text_color = kwargs.pop("text_color", None)
        fg_color   = kwargs.pop("fg_color",   None)
        kwargs.pop("corner_radius", None)
        try:
            parent_bg = master.cget("bg")
        except Exception:
            parent_bg = _palette()["surface"]
        bg = _resolve_color(fg_color, parent_bg, master)
        fg = _resolve_color(text_color, _palette()["text"], master)
        super().__init__(master, *args,
                         bg=bg, fg=fg,
                         activebackground=bg, activeforeground=fg,
                         selectcolor=_palette()["panel"],
                         highlightthickness=0, relief="flat",
                         font=(_TV_FONT_FAMILY, _TV_FONT_SIZE),
                         **kwargs)


# ─────────────────────────────────────────
# CTkRadioButton  ← مضافة حديثاً
# ─────────────────────────────────────────
class CTkRadioButton(_GridMixin, tk.Radiobutton):
    """Radio button يتوافق مع نظام الألوان dark/light تلقائياً"""
    def __init__(self, master=None, *args, **kwargs):
        text_color = kwargs.pop("text_color",     None)
        fg_color   = kwargs.pop("fg_color",       None)
        hover_color= kwargs.pop("hover_color",    None)
        kwargs.pop("corner_radius",   None)
        kwargs.pop("border_width_checked", None)
        kwargs.pop("border_width_unchecked", None)
        kwargs.pop("radiobutton_height", None)
        kwargs.pop("radiobutton_width",  None)
        try:
            parent_bg = master.cget("bg")
        except Exception:
            parent_bg = _palette()["surface"]
        bg = _resolve_color(fg_color, parent_bg, master)
        fg = _resolve_color(text_color, _palette()["text"], master)
        super().__init__(master, *args,
                         bg=bg, fg=fg,
                         activebackground=bg,
                         activeforeground=fg,
                         selectcolor=_palette()["panel"],
                         highlightthickness=0,
                         relief="flat",
                         font=(_TV_FONT_FAMILY, _TV_FONT_SIZE),
                         **kwargs)

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        kwargs.pop("fg_color",    None)
        kwargs.pop("text_color",  None)
        kwargs.pop("hover_color", None)
        return super().configure(**kwargs)

    config = configure


# ─────────────────────────────────────────
# CTkTextbox
# ─────────────────────────────────────────
class CTkTextbox(_GridMixin, tk.Text):
    def __init__(self, master=None, *args, **kwargs):
        fg_color   = kwargs.pop("fg_color",   None)
        text_color = kwargs.pop("text_color", None)
        width  = kwargs.pop("width",  None)
        height = kwargs.pop("height", None)
        bg = _resolve_color(fg_color,    _palette()["entry"], master)
        fg = _resolve_color(text_color,  _palette()["text"],  master)
        if width  is not None: kwargs["width"]  = width
        if height is not None: kwargs["height"] = height
        super().__init__(master, *args,
                         bg=bg, fg=fg,
                         insertbackground=fg,
                         relief="solid", borderwidth=1,
                         highlightthickness=1,
                         highlightbackground=_palette()["border"],
                         highlightcolor=_THEME_ACCENT,
                         font=(_TV_FONT_FAMILY, _TV_FONT_SIZE),
                         wrap="word",
                         **kwargs)


# ─────────────────────────────────────────
# CTkOptionMenu  (ttk.Combobox)
# ─────────────────────────────────────────
class CTkOptionMenu(_GridMixin, ttk.Combobox):
    def __init__(self, master=None, *args, **kwargs):
        values   = kwargs.pop("values",   [])
        variable = kwargs.pop("variable", None)
        command  = kwargs.pop("command",  None)
        width    = kwargs.pop("width",    None)
        # pop font من المستدعي — ttk.Combobox يُعيّن الخط عبر ttk.Style
        kwargs.pop("font", None)
        for k in ("corner_radius", "fg_color", "button_color", "button_hover_color",
                  "dropdown_fg_color", "dropdown_hover_color",
                  "text_color", "text_color_disabled"):
            kwargs.pop(k, None)
        if width is not None:
            kwargs["width"] = width
        super().__init__(master, *args,
                         values=values,
                         textvariable=variable,
                         state="readonly",
                         font=(_TV_FONT_FAMILY, _TV_FONT_SIZE, "bold"),
                         **kwargs)
        self._command = command
        if self._command:
            self.bind("<<ComboboxSelected>>", self._on_selected)

    def _on_selected(self, _event=None):
        if self._command:
            self._command(self.get())

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if "command" in kwargs:
            self._command = kwargs.pop("command")
            self.bind("<<ComboboxSelected>>", self._on_selected)
        return super().configure(**kwargs)

    config = configure


# ─────────────────────────────────────────
# CTkScrollableFrame
# ─────────────────────────────────────────
class CTkScrollableFrame(tk.Frame):
    """
    Frame قابل للتمرير.
    الأبناء يُضافون لـ _inner مباشرة لتجنب تعارض grid/pack.
    استخدم CTkScrollableFrame كـ master لأي widget وسيذهب لـ _inner تلقائياً
    عبر override لـ tk internals.
    """
    def __init__(self, master=None, *args, **kwargs):
        fg_color = kwargs.pop("fg_color", None)
        kwargs.pop("corner_radius", None)
        width  = kwargs.pop("width",  None)
        height = kwargs.pop("height", None)
        bg = _resolve_color(fg_color, _palette()["surface"], master)
        super().__init__(master, bg=bg,
                         width=width or 200, height=height or 200)

        # Canvas + Scrollbar داخل الـ outer frame بـ pack
        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0, borderwidth=0)
        self._vsb    = ttk.Scrollbar(self, orient="vertical",
                                      command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vsb.set)
        self._vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        # الـ Frame الداخلي — هنا يُضاف كل شيء
        self._inner  = tk.Frame(self._canvas, bg=bg)
        self._win    = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>",  self._sync_scroll)
        self._canvas.bind("<Configure>", self._sync_width)
        self._canvas.bind_all("<MouseWheel>", self._on_wheel)

        self.content_frame = self._inner

    # ── tk intercept: أي widget يُنشأ بـ master=self يذهب لـ _inner ──
    def _w_intercept(self):
        """يُرجع اسم الـ inner frame للـ tk path — هكذا الأبناء يعتقدون أنهم في _inner."""
        return self._inner._w

    def grid_columnconfigure(self, index, **kwargs):
        if isinstance(index, (tuple, list)):
            for i in index: self._inner.grid_columnconfigure(i, **kwargs)
        else:
            self._inner.grid_columnconfigure(index, **kwargs)

    def grid_rowconfigure(self, index, **kwargs):
        if isinstance(index, (tuple, list)):
            for i in index: self._inner.grid_rowconfigure(i, **kwargs)
        else:
            self._inner.grid_rowconfigure(index, **kwargs)

    # geometry managers على الـ outer frame
    def grid(self, *a, **kw):  super().grid(*a, **kw)
    def pack(self, *a, **kw):  super().pack(*a, **kw)
    def place(self, *a, **kw): super().place(*a, **kw)

    def _sync_scroll(self, _e=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _sync_width(self, e):
        self._canvas.itemconfig(self._win, width=e.width)

    def _on_wheel(self, e):
        try: self._canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        except Exception: pass

    def get_inner(self):
        return self._inner


# ─────────────────────────────────────────
# CTkTabview  (ttk.Notebook wrapper)
# ─────────────────────────────────────────
class CTkTabview(_GridMixin, tk.Frame):
    def __init__(self, master=None, *args, **kwargs):
        fg_color = kwargs.pop("fg_color", None)
        kwargs.pop("corner_radius", None)
        bg = _resolve_color(fg_color, _palette()["surface"], master)
        super().__init__(master, *args, bg=bg, **kwargs)
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True)
        self._tabs = {}

    def add(self, name):
        if name in self._tabs:
            return self._tabs[name]
        page = tk.Frame(self._notebook, bg=self.cget("bg"))
        self._notebook.add(page, text=name)
        self._tabs[name] = page
        return page

    def set(self, name):
        if name in self._tabs:
            self._notebook.select(self._tabs[name])

    def tab(self, name):
        return self._tabs[name]


class CTkMessagebox:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Use tkinter.messagebox instead of CTkMessagebox.")
