"""
screens/theme_designer.py
─────────────────────────
Theme Designer — واجهة رسومية كاملة لتخصيص المظهر.
"""
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, font as tkfont
import copy

import customtkinter as ctk
from utils.theme_manager import ThemeManager, DEFAULT_THEME


# ─────────────────────────────────────────────────────────────
# أداة اختيار اللون المدمجة
# ─────────────────────────────────────────────────────────────
class ColorButton(tk.Frame):
    """زر يعرض لوناً ويفتح color picker عند الضغط."""
    def __init__(self, master, color="#111827", on_change=None, width=48, **kw):
        super().__init__(master, **kw)
        self._color    = color
        self._callback = on_change
        self._btn = tk.Button(
            self, bg=color, width=3,
            relief="solid", borderwidth=1,
            cursor="hand2",
            command=self._pick,
        )
        self._btn.pack(fill="both", expand=True)
        self._lbl = tk.Label(self, text=color, font=("Segoe UI", 8),
                             bg=self.master.cget("bg") if hasattr(self.master,"cget") else "#1f2937",
                             fg="#94a3b8", width=8)
        self._lbl.pack()

    def _pick(self):
        result = colorchooser.askcolor(color=self._color, title="اختر لوناً",
                                        parent=self)
        if result and result[1]:
            self.set(result[1])

    def set(self, color: str):
        self._color = color
        self._btn.configure(bg=color)
        self._lbl.configure(text=color)
        if self._callback:
            self._callback(color)

    def get(self) -> str:
        return self._color


# ─────────────────────────────────────────────────────────────
# Row helper
# ─────────────────────────────────────────────────────────────
def _row(parent, label, widget, row, label_width=18, bg="#1f2937"):
    tk.Label(parent, text=label, font=("Segoe UI", 10),
             bg=bg, fg="#94a3b8",
             width=label_width, anchor="e").grid(
        row=row, column=0, sticky="e", padx=(8, 6), pady=4)
    widget.grid(row=row, column=1, sticky="w", padx=(0, 8), pady=4)


# ─────────────────────────────────────────────────────────────
# ThemeDesignerScreen
# ─────────────────────────────────────────────────────────────
class ThemeDesignerScreen(ctk.CTkFrame):
    BG    = "#111827"
    PANEL = "#1f2937"
    FG    = "#f1f5f9"
    MUTED = "#94a3b8"

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._tm     = ThemeManager.instance()
        self._live   = True          # Live Preview مفعّل
        self._widgets: dict = {}     # مرجع لكل widget قابل للتحديث في الـ preview
        self._vars:   dict = {}      # ctk.StringVar / ctk.BooleanVar / ctk.IntVar
        self._build()
        self._populate()

    # ─────────────────────────────────────────────────────────
    # بناء الواجهة
    # ─────────────────────────────────────────────────────────
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── شريط العنوان + أزرار الأفعال ──
        self._build_topbar()

        # ── اليسار: لوحة الإعدادات ──
        left = tk.Frame(self, bg=self.BG)
        left.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        self._build_settings_panel(left)

        # ── اليمين: معاينة حية ──
        right = tk.Frame(self, bg=self.BG)
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)
        self._build_preview_panel(right)

    # ── Topbar ──────────────────────────────────────────────
    def _build_topbar(self):
        bar = tk.Frame(self, bg=self.PANEL, height=52)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 6))
        bar.grid_columnconfigure(1, weight=1)
        bar.grid_propagate(False)

        tk.Label(bar, text="🎨  Theme Designer — مصمم المظهر",
                 font=("Segoe UI", 15, "bold"),
                 bg=self.PANEL, fg=self.FG).grid(
            row=0, column=0, padx=16, pady=8, sticky="e")

        btn_frame = tk.Frame(bar, bg=self.PANEL)
        btn_frame.grid(row=0, column=2, padx=12, pady=6)

        def _btn(text, color, cmd):
            b = tk.Button(btn_frame, text=text, bg=color, fg="white",
                          font=("Segoe UI", 9, "bold"),
                          relief="flat", borderwidth=0, cursor="hand2",
                          padx=12, pady=4, command=cmd)
            b.pack(side="right", padx=4)

        _btn("🔄 استعادة الافتراضي", "#dc2626", self._reset)
        _btn("💾 حفظ",               "#059669", self._save)
        _btn("✅ تطبيق",             "#2563eb", self._apply_live)

        # Live Preview toggle
        self._live_var = tk.BooleanVar(value=True)
        tk.Checkbutton(btn_frame, text="معاينة فورية",
                       variable=self._live_var,
                       bg=self.PANEL, fg=self.FG,
                       selectcolor=self.BG,
                       activebackground=self.PANEL,
                       activeforeground=self.FG,
                       font=("Segoe UI", 9),
                       command=lambda: setattr(self, "_live", self._live_var.get())
                       ).pack(side="right", padx=8)

    # ── Settings Panel ───────────────────────────────────────
    def _build_settings_panel(self, parent):
        # Canvas قابل للتمرير
        canvas = tk.Canvas(parent, bg=self.BG, highlightthickness=0)
        vsb    = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        canvas.grid(row=0, column=0, sticky="nsew")

        inner = tk.Frame(canvas, bg=self.BG)
        win   = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner(e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas(e):
            canvas.itemconfig(win, width=e.width)
        def _on_wheel(e):
            try: canvas.yview_scroll(int(-1*(e.delta/120)), "units")
            except Exception: pass

        inner.bind("<Configure>",  _on_inner)
        canvas.bind("<Configure>", _on_canvas)
        canvas.bind_all("<MouseWheel>", _on_wheel)

        inner.grid_columnconfigure(0, weight=1)
        row = 0

        # ── بناء كل قسم ──
        sections = [
            ("🌲 Treeview",    self._build_section_treeview),
            ("📑 Notebook",    self._build_section_notebook),
            ("🔽 Combobox",    self._build_section_combobox),
            ("🏷 Label",       self._build_section_label),
            ("📜 Scrollbar",   self._build_section_scrollbar),
        ]
        for title, builder in sections:
            row = self._section_card(inner, title, builder, row)

    def _section_card(self, parent, title, builder_fn, start_row) -> int:
        """ينشئ بطاقة قابلة للطي لكل قسم."""
        card = tk.Frame(parent, bg=self.PANEL, bd=0,
                        highlightthickness=1,
                        highlightbackground="#334155")
        card.grid(row=start_row, column=0, sticky="ew",
                  padx=8, pady=6)
        card.grid_columnconfigure(0, weight=1)

        # رأس البطاقة
        header = tk.Frame(card, bg="#253047", cursor="hand2")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        arrow_var = tk.StringVar(value="▼")
        tk.Label(header, textvariable=arrow_var,
                 bg="#253047", fg=self.MUTED,
                 font=("Segoe UI", 9)).grid(
            row=0, column=1, padx=8, pady=6)
        tk.Label(header, text=title,
                 bg="#253047", fg=self.FG,
                 font=("Segoe UI", 11, "bold"), anchor="e").grid(
            row=0, column=0, padx=12, pady=6, sticky="e")

        # محتوى البطاقة
        body = tk.Frame(card, bg=self.PANEL)
        body.grid(row=1, column=0, sticky="ew", padx=4, pady=4)
        body.grid_columnconfigure(1, weight=1)
        builder_fn(body)

        # طي/فتح
        def _toggle(_e=None):
            if body.winfo_ismapped():
                body.grid_remove()
                arrow_var.set("▶")
            else:
                body.grid()
                arrow_var.set("▼")

        header.bind("<Button-1>", _toggle)
        for child in header.winfo_children():
            child.bind("<Button-1>", _toggle)

        return start_row + 1

    # ── Treeview Section ─────────────────────────────────────
    def _build_section_treeview(self, body):
        BG = self.PANEL
        tm = self._tm

        def _cv(key, section="treeview"):
            """Color button بربط تلقائي."""
            initial = tm.get(section, key, "#000000")
            cb = ColorButton(body, color=initial, bg=BG,
                             on_change=lambda c, k=key: self._set_and_preview("treeview", k, c))
            return cb

        def _spin(key, from_=8, to=60, section="treeview"):
            val = tm.get(section, key, 11)
            var = tk.IntVar(value=val)
            self._vars[f"{section}.{key}"] = var
            sp = tk.Spinbox(body, from_=from_, to=to,
                            textvariable=var, width=5,
                            bg="#0b1220", fg=self.FG,
                            buttonbackground=self.PANEL,
                            font=("Segoe UI", 10),
                            relief="flat",
                            command=lambda k=key, v=var:
                                self._set_and_preview("treeview", k, v.get()))
            var.trace("w", lambda *_,k=key,v=var:
                      self._set_and_preview("treeview", k, self._safe_int(v.get(), 11)))
            return sp

        def _check(key, label, section="treeview"):
            val = tm.get(section, key, True)
            var = tk.BooleanVar(value=bool(val))
            self._vars[f"{section}.{key}"] = var
            cb = tk.Checkbutton(body, text=label, variable=var,
                                bg=BG, fg=self.FG,
                                selectcolor=self.BG,
                                activebackground=BG,
                                font=("Segoe UI", 10),
                                command=lambda k=key, v=var:
                                    self._set_and_preview("treeview", k, v.get()))
            return cb

        def _font_menu(key, section="treeview"):
            val   = tm.get(section, key, "Segoe UI")
            fonts = sorted(set(tkfont.families()))[:80]
            var   = tk.StringVar(value=val)
            self._vars[f"{section}.{key}"] = var
            opt = ttk.Combobox(body, textvariable=var, values=fonts,
                               state="readonly", width=18,
                               font=("Segoe UI", 10))
            opt.bind("<<ComboboxSelected>>",
                     lambda e,k=key,v=var:
                         self._set_and_preview("treeview", k, v.get()))
            return opt

        r = 0
        _row(body, "ارتفاع الصف (px):",  _spin("row_height", 20, 60), r, bg=BG); r+=1
        _row(body, "خط:",                 _font_menu("font_family"),   r, bg=BG); r+=1
        _row(body, "حجم الخط:",           _spin("font_size"),          r, bg=BG); r+=1

        tk.Frame(body, height=1, bg="#334155").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=6); r+=1

        _row(body, "خلفية الصفوف:",       _cv("bg"),          r, bg=BG); r+=1
        _row(body, "لون النص:",           _cv("fg"),          r, bg=BG); r+=1
        _row(body, "خلفية الرأس:",        _cv("heading_bg"),  r, bg=BG); r+=1
        _row(body, "لون نص الرأس:",       _cv("heading_fg"),  r, bg=BG); r+=1
        chk = _check("heading_font_bold", "رأس عريض (Bold)")
        chk.grid(row=r, column=0, columnspan=2, sticky="e", padx=8, pady=2); r+=1

        tk.Frame(body, height=1, bg="#334155").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=6); r+=1

        _row(body, "خلفية محدد:",     _cv("selected_bg"), r, bg=BG); r+=1
        _row(body, "نص محدد:",        _cv("selected_fg"), r, bg=BG); r+=1

        tk.Frame(body, height=1, bg="#334155").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=6); r+=1

        # Zebra
        chk_z = _check("zebra", "تفعيل Zebra Striping")
        chk_z.grid(row=r, column=0, columnspan=2, sticky="e", padx=8, pady=4); r+=1
        _row(body, "صف فردي BG:",  _cv("odd_row_bg"),  r, bg=BG); r+=1
        _row(body, "صف فردي FG:",  _cv("odd_row_fg"),  r, bg=BG); r+=1
        _row(body, "صف زوجي BG:", _cv("even_row_bg"), r, bg=BG); r+=1
        _row(body, "صف زوجي FG:", _cv("even_row_fg"), r, bg=BG); r+=1

        tk.Frame(body, height=1, bg="#334155").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=6); r+=1
        _row(body, "تحذير مخزون:",  _cv("low_fg"), r, bg=BG); r+=1
        _row(body, "نفاد مخزون:",   _cv("out_fg"), r, bg=BG); r+=1

    # ── Notebook Section ────────────────────────────────────
    def _build_section_notebook(self, body):
        BG = self.PANEL
        tm = self._tm

        def _cv(key):
            c = ColorButton(body, color=tm.get("notebook", key, "#1f2937"), bg=BG,
                            on_change=lambda v,k=key:
                                self._set_and_preview("notebook", k, v))
            return c

        def _spin(key, from_=6, to=40):
            var = tk.IntVar(value=tm.get("notebook", key, 11))
            self._vars[f"notebook.{key}"] = var
            sp = tk.Spinbox(body, from_=from_, to=to, textvariable=var,
                            width=5, bg="#0b1220", fg=self.FG,
                            buttonbackground=self.PANEL,
                            font=("Segoe UI", 10), relief="flat",
                            command=lambda k=key,v=var:
                                self._set_and_preview("notebook", k, v.get()))
            var.trace("w", lambda *_,k=key,v=var:
                      self._set_and_preview("notebook", k, self._safe_int(v.get(),11)))
            return sp

        r = 0
        _row(body, "خلفية التاب:",            _cv("tab_bg"),          r, bg=BG); r+=1
        _row(body, "نص التاب:",               _cv("tab_fg"),          r, bg=BG); r+=1
        _row(body, "خلفية المحدد:",           _cv("tab_selected_bg"), r, bg=BG); r+=1
        _row(body, "نص المحدد:",              _cv("tab_selected_fg"), r, bg=BG); r+=1
        _row(body, "حجم الخط:",               _spin("font_size"),     r, bg=BG); r+=1
        _row(body, "Padding أفقي:",           _spin("tab_padding_x", 4, 40), r, bg=BG); r+=1
        _row(body, "Padding رأسي:",           _spin("tab_padding_y", 2, 30), r, bg=BG); r+=1

    # ── Combobox Section ────────────────────────────────────
    def _build_section_combobox(self, body):
        BG = self.PANEL
        tm = self._tm

        def _cv(key):
            c = ColorButton(body, color=tm.get("combobox", key, "#0b1220"), bg=BG,
                            on_change=lambda v,k=key:
                                self._set_and_preview("combobox", k, v))
            return c

        def _spin(key, from_=6, to=40):
            var = tk.IntVar(value=tm.get("combobox", key, 11))
            self._vars[f"combobox.{key}"] = var
            sp = tk.Spinbox(body, from_=from_, to=to, textvariable=var,
                            width=5, bg="#0b1220", fg=self.FG,
                            buttonbackground=self.PANEL,
                            font=("Segoe UI", 10), relief="flat",
                            command=lambda k=key,v=var:
                                self._set_and_preview("combobox", k, v.get()))
            var.trace("w", lambda *_,k=key,v=var:
                      self._set_and_preview("combobox", k, self._safe_int(v.get(),11)))
            return sp

        r = 0
        _row(body, "خلفية الحقل:", _cv("field_bg"),              r, bg=BG); r+=1
        _row(body, "لون النص:",    _cv("fg"),                    r, bg=BG); r+=1
        _row(body, "حجم الخط:",    _spin("font_size"),           r, bg=BG); r+=1
        _row(body, "حجم السهم:",   _spin("arrow_size", 8, 28),   r, bg=BG); r+=1

    # ── Label Section ───────────────────────────────────────
    def _build_section_label(self, body):
        BG = self.PANEL
        tm = self._tm
        def _cv(key):
            return ColorButton(body, color=tm.get("label", key, "#111827"), bg=BG,
                               on_change=lambda v,k=key:
                                   self._set_and_preview("label", k, v))
        def _spin(key):
            var = tk.IntVar(value=tm.get("label", key, 11))
            self._vars[f"label.{key}"] = var
            sp = tk.Spinbox(body, from_=6, to=40, textvariable=var,
                            width=5, bg="#0b1220", fg=self.FG,
                            buttonbackground=self.PANEL,
                            font=("Segoe UI", 10), relief="flat",
                            command=lambda k=key,v=var:
                                self._set_and_preview("label", k, v.get()))
            var.trace("w", lambda *_,k=key,v=var:
                      self._set_and_preview("label", k, self._safe_int(v.get(),11)))
            return sp
        r = 0
        _row(body, "خلفية:", _cv("bg"),       r, bg=BG); r+=1
        _row(body, "نص:",    _cv("fg"),       r, bg=BG); r+=1
        _row(body, "خط:",    _spin("font_size"), r, bg=BG); r+=1

    # ── Scrollbar Section ───────────────────────────────────
    def _build_section_scrollbar(self, body):
        BG = self.PANEL
        tm = self._tm
        def _cv(key):
            return ColorButton(body, color=tm.get("scrollbar", key, "#1f2937"), bg=BG,
                               on_change=lambda v,k=key:
                                   self._set_and_preview("scrollbar", k, v))
        r = 0
        _row(body, "خلفية:",  _cv("bg"),     r, bg=BG); r+=1
        _row(body, "قناة:",   _cv("trough"), r, bg=BG); r+=1
        _row(body, "سهم:",    _cv("arrow"),  r, bg=BG); r+=1

    # ─────────────────────────────────────────────────────────
    # Live Preview Panel
    # ─────────────────────────────────────────────────────────
    def _build_preview_panel(self, parent):
        header = tk.Frame(parent, bg=self.PANEL, height=36)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="👁 معاينة حية",
                 font=("Segoe UI", 12, "bold"),
                 bg=self.PANEL, fg=self.FG).pack(side="right", padx=14, pady=6)

        container = tk.Frame(parent, bg=self.BG)
        container.pack(fill="both", expand=True, padx=8, pady=8)

        tm = self._tm

        # ── Notebook ──
        nb = ttk.Notebook(container)
        nb.pack(fill="x", padx=10, pady=(12, 6))
        tab1 = tk.Frame(nb, bg=self.BG)
        tab2 = tk.Frame(nb, bg=self.BG)
        nb.add(tab1, text="تاب أول")
        nb.add(tab2, text="تاب ثانٍ")
        self._widgets["notebook"] = nb

        # ── Treeview ──
        tv_frame = tk.Frame(container, bg=self.BG)
        tv_frame.pack(fill="both", expand=True, padx=10, pady=6)
        tv_frame.grid_rowconfigure(0, weight=1)
        tv_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "name", "qty", "price", "status")
        self._preview_tree = ttk.Treeview(tv_frame, columns=cols,
                                           show="headings", height=7)
        labels = {"id": "#", "name": "الدواء", "qty": "الكمية",
                  "price": "السعر", "status": "الحالة"}
        widths = {"id": 40, "name": 160, "qty": 70, "price": 80, "status": 80}
        for col in cols:
            self._preview_tree.heading(col, text=labels[col], anchor="center")
            self._preview_tree.column(col, width=widths[col], anchor="center")

        vsb = ttk.Scrollbar(tv_frame, orient="vertical",
                            command=self._preview_tree.yview)
        self._preview_tree.configure(yscrollcommand=vsb.set)
        self._preview_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # بيانات تجريبية
        demo_rows = [
            (1, "Augmentin 1g",     24, "165.00", "متوفر"),
            (2, "Paracetamol 500mg",  5, "12.00",  "تنبيه"),
            (3, "Surgical Gloves",    0, "88.00",  "نافد"),
            (4, "Amoxicillin 250mg", 18, "45.00",  "متوفر"),
            (5, "Omeprazole 20mg",   11, "55.00",  "متوفر"),
            (6, "Metformin 500mg",    3, "28.00",  "تنبيه"),
            (7, "Atorvastatin 10mg",  8, "92.00",  "متوفر"),
        ]
        tag_map = {"متوفر": "ok", "تنبيه": "low", "نافد": "out"}
        for i, row in enumerate(demo_rows):
            base_tag = "evenrow" if i % 2 == 0 else "oddrow"
            st_tag   = tag_map.get(row[4], "ok")
            self._preview_tree.insert("", "end",
                                       tags=(base_tag, st_tag),
                                       values=row)

        self._widgets["treeview"] = self._preview_tree
        tm.apply_to_tree(self._preview_tree)

        # ── Combobox + Label ──
        bottom = tk.Frame(container, bg=self.BG)
        bottom.pack(fill="x", padx=10, pady=8)

        tk.Label(bottom, text="Combobox:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side="right", padx=6)
        cb_prev = ttk.Combobox(bottom, values=["خيار 1","خيار 2","خيار 3"],
                               state="readonly", width=14)
        cb_prev.set("خيار 1")
        cb_prev.pack(side="right", padx=6)
        self._widgets["combobox"] = cb_prev

        tk.Label(bottom, text="نص عادي — Label",
                 bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side="right", padx=12)

        # اطبّق الثيم على المعاينة
        self._refresh_preview()

    # ─────────────────────────────────────────────────────────
    # Populate: ملء القيم من ThemeManager
    # ─────────────────────────────────────────────────────────
    def _populate(self):
        """تملأ كل الـ vars بالقيم الحالية من ThemeManager — تُستدعى عند Reset أيضاً."""
        tm = self._tm
        for key, var in self._vars.items():
            section, k = key.split(".", 1)
            val = tm.get(section, k)
            if val is None:
                continue
            try:
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(val))
                elif isinstance(var, tk.IntVar):
                    var.set(int(val))
                else:
                    var.set(str(val))
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────
    # Live Preview helpers
    # ─────────────────────────────────────────────────────────
    def _set_and_preview(self, section: str, key: str, value):
        self._tm.set(section, key, value)
        if self._live:
            self._refresh_preview()

    def _refresh_preview(self):
        self._tm._apply_treeview_global(ttk.Style())
        self._tm._apply_notebook(ttk.Style())
        self._tm._apply_combobox(ttk.Style(), self.winfo_toplevel())
        self._tm._apply_label(ttk.Style())
        self._tm._apply_scrollbar(ttk.Style())
        tree = self._widgets.get("treeview")
        if tree:
            try:
                self._tm.apply_to_tree(tree)
            except Exception:
                pass

    def _apply_live(self):
        self._tm.apply()
        messagebox.showinfo("تم", "✅ تم تطبيق الثيم على البرنامج كاملاً",
                            parent=self)

    def _save(self):
        self._tm.save()
        self._tm.apply()
        messagebox.showinfo("تم", "✅ تم حفظ الثيم بنجاح", parent=self)

    def _reset(self):
        if not messagebox.askyesno("تأكيد",
                                    "إعادة كل الإعدادات للافتراضي؟", parent=self):
            return
        self._tm.reset_to_defaults()
        self._populate()
        self._refresh_preview()
        messagebox.showinfo("تم", "✅ تم استعادة الإعدادات الافتراضية", parent=self)

    @staticmethod
    def _safe_int(val, fallback=11):
        try:
            return int(val)
        except Exception:
            return fallback
