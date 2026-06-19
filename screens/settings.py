import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
from tkinter import ttk
import shutil, os
from utils.helpers import get_setting, set_setting
from database.connection import DB_PATH


def _scrollable(parent):
    """إنشاء frame قابل للتمرير — يرجع الـ frame الداخلي لإضافة العناصر فيه."""
    outer = tk.Frame(parent, bg=parent.cget("bg") if hasattr(parent, "cget") else "#111827")
    outer.pack(fill="both", expand=True)

    canvas = tk.Canvas(outer, bg=outer.cget("bg"), highlightthickness=0, borderwidth=0)
    vsb    = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas, bg=outer.cget("bg"))
    win   = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner(e=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
    def _on_canvas(e):
        canvas.itemconfig(win, width=e.width)
    def _on_wheel(e):
        try: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        except Exception: pass

    inner.bind("<Configure>", _on_inner)
    canvas.bind("<Configure>", _on_canvas)
    canvas.bind_all("<MouseWheel>", _on_wheel)
    return inner


class SettingsScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        tabs = ctk.CTkTabview(self)
        tabs.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)

        self._build_pharmacy_tab(tabs.add("معلومات الصيدلية"))
        self._build_system_tab(tabs.add("إعدادات النظام"))
        self._build_backup_tab(tabs.add("النسخ الاحتياطي"))

    # ───────────────────────────────────────
    # تاب: معلومات الصيدلية
    # ───────────────────────────────────────
    def _build_pharmacy_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        inner = _scrollable(parent)
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_columnconfigure(1, weight=1)

        from customtkinter import CTkFont as F
        ctk.CTkLabel(inner, text="معلومات الصيدلية",
                     font=F(size=17, weight="bold")).grid(
            row=0, column=0, columnspan=2, pady=(10, 16), padx=16, sticky="e")

        fields = [
            ("اسم الصيدلية *",      "pharmacy_name"),
            ("العنوان",              "pharmacy_address"),
            ("رقم الهاتف",          "pharmacy_phone"),
            ("رقم الترخيص",         "pharmacy_license"),
            ("العملة",               "currency"),
            ("نسبة الضريبة %",      "tax_rate"),
            ("حد تنبيه المخزون",    "low_stock_alert"),
            ("بادئة الفاتورة",       "invoice_prefix"),
            ("بادئة أمر الشراء",    "purchase_prefix"),
        ]

        self.pharmacy_vars = {}
        for i, (label, key) in enumerate(fields):
            row = i + 1
            ctk.CTkLabel(inner, text=label + ":", anchor="e",
                         font=F(size=12)).grid(
                row=row, column=1, sticky="e", padx=12, pady=5)
            var = ctk.StringVar(value=get_setting(key, ""))
            ctk.CTkEntry(inner, textvariable=var, height=34,
                         justify="right", width=280, font=F(size=12)).grid(
                row=row, column=0, padx=12, pady=5, sticky="ew")
            self.pharmacy_vars[key] = var

        r = len(fields) + 1
        ctk.CTkLabel(inner, text="تذييل الإيصال:", anchor="e",
                     font=F(size=12)).grid(row=r, column=1, sticky="ne", padx=12, pady=5)
        self.footer_text = ctk.CTkTextbox(inner, height=70, width=280)
        self.footer_text.insert("1.0", get_setting("receipt_footer", ""))
        self.footer_text.grid(row=r, column=0, padx=12, pady=5, sticky="ew")

        ctk.CTkButton(inner, text="💾 حفظ", height=38,
                      fg_color="#059669", hover_color="#047857",
                      font=F(size=13, weight="bold"),
                      command=self._save_pharmacy).grid(
            row=r+1, column=0, columnspan=2, pady=14, padx=50, sticky="ew")

    def _save_pharmacy(self):
        if not self.pharmacy_vars["pharmacy_name"].get().strip():
            messagebox.showwarning("تحذير", "اسم الصيدلية مطلوب", parent=self)
            return
        for key, var in self.pharmacy_vars.items():
            set_setting(key, var.get().strip())
        set_setting("receipt_footer", self.footer_text.get("1.0", "end").strip())
        messagebox.showinfo("تم", "✅ تم حفظ إعدادات الصيدلية", parent=self)

    # ───────────────────────────────────────
    # تاب: إعدادات النظام
    # ───────────────────────────────────────
    def _build_system_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        inner = _scrollable(parent)
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_columnconfigure(1, weight=1)

        from customtkinter import CTkFont as F
        ctk.CTkLabel(inner, text="إعدادات النظام",
                     font=F(size=17, weight="bold")).grid(
            row=0, column=0, columnspan=2, pady=(10, 16), padx=16, sticky="e")

        # ── ثيم الألوان ──
        ctk.CTkLabel(inner, text="ثيم الألوان:", anchor="e",
                     font=F(size=12)).grid(row=1, column=1, sticky="e", padx=12, pady=6)
        self.theme_var = ctk.StringVar(value=get_setting("theme", "blue"))
        ctk.CTkOptionMenu(inner, values=["blue", "green", "dark-blue"],
                          variable=self.theme_var, width=200,
                          font=F(size=12)).grid(row=1, column=0, padx=12, pady=6, sticky="w")

        # ── وضع المظهر ──
        ctk.CTkLabel(inner, text="وضع المظهر:", anchor="e",
                     font=F(size=12)).grid(row=2, column=1, sticky="e", padx=12, pady=6)
        self.appearance_var = ctk.StringVar(value=get_setting("appearance", "dark"))
        ctk.CTkOptionMenu(inner, values=["dark", "light"],
                          variable=self.appearance_var,
                          command=lambda v: ctk.set_appearance_mode(v),
                          width=200, font=F(size=12)).grid(
            row=2, column=0, padx=12, pady=6, sticky="w")

        ctk.CTkButton(inner, text="🎨 تطبيق وحفظ الثيم", height=36,
                      fg_color="#2563eb", font=F(size=12),
                      command=self._apply_theme).grid(
            row=3, column=0, columnspan=2, padx=60, pady=(4, 16), sticky="ew")

        # ── فاصل ──
        sep = tk.Frame(inner, height=1, bg="#334155")
        sep.grid(row=4, column=0, columnspan=2, sticky="ew", padx=12, pady=4)

        # ── تغيير كلمة المرور ──
        ctk.CTkLabel(inner, text="تغيير كلمة المرور",
                     font=F(size=14, weight="bold")).grid(
            row=5, column=0, columnspan=2, pady=(12, 8), padx=16, sticky="e")

        pw_fields = [
            ("كلمة المرور الحالية:", "old_pw"),
            ("كلمة المرور الجديدة:", "new_pw"),
            ("تأكيد كلمة المرور:",   "confirm_pw"),
        ]
        self._pw_vars = {}
        for i, (label, key) in enumerate(pw_fields):
            ctk.CTkLabel(inner, text=label, anchor="e",
                         font=F(size=12)).grid(
                row=6+i, column=1, sticky="e", padx=12, pady=5)
            var = ctk.StringVar()
            ctk.CTkEntry(inner, textvariable=var, show="●",
                         width=200, height=34, font=F(size=12)).grid(
                row=6+i, column=0, padx=12, pady=5, sticky="w")
            self._pw_vars[key] = var

        ctk.CTkButton(inner, text="🔑 تغيير كلمة المرور", height=36,
                      fg_color="#7c3aed", hover_color="#6d28d9",
                      font=F(size=12),
                      command=self._change_password).grid(
            row=9, column=0, columnspan=2, padx=60, pady=12, sticky="ew")

    def _apply_theme(self):
        theme      = self.theme_var.get()
        appearance = self.appearance_var.get()
        set_setting("theme",      theme)
        set_setting("appearance", appearance)
        try:
            ctk.set_default_color_theme(theme)
        except Exception:
            pass
        ctk.set_appearance_mode(appearance)
        messagebox.showinfo("تم",
                            "✅ تم حفظ الثيم.\nبعض التغييرات تظهر عند إعادة التشغيل.",
                            parent=self)

    def _change_password(self):
        old     = self._pw_vars["old_pw"].get()
        new     = self._pw_vars["new_pw"].get()
        confirm = self._pw_vars["confirm_pw"].get()
        if not old or not new:
            messagebox.showwarning("تحذير", "يرجى ملء جميع الحقول", parent=self)
            return
        if new != confirm:
            messagebox.showerror("خطأ", "كلمتا المرور غير متطابقتين", parent=self)
            return
        if len(new) < 6:
            messagebox.showwarning("تحذير", "كلمة المرور يجب أن تكون 6 أحرف على الأقل",
                                   parent=self)
            return
        from utils.auth import change_password, get_current_user
        user = get_current_user()
        if not user:
            messagebox.showerror("خطأ", "لم يتم تسجيل الدخول", parent=self)
            return
        if change_password(user["id"], old, new):
            messagebox.showinfo("تم", "✅ تم تغيير كلمة المرور", parent=self)
            for var in self._pw_vars.values():
                var.set("")
        else:
            messagebox.showerror("خطأ", "كلمة المرور الحالية غير صحيحة", parent=self)

    # ───────────────────────────────────────
    # تاب: النسخ الاحتياطي
    # ───────────────────────────────────────
    def _build_backup_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        inner = _scrollable(parent)
        inner.grid_columnconfigure(0, weight=1)

        from customtkinter import CTkFont as F

        ctk.CTkLabel(inner, text="إدارة النسخ الاحتياطي",
                     font=F(size=17, weight="bold")).grid(
            row=0, column=0, pady=(10, 16), padx=20, sticky="e")

        # ── معلومات قاعدة البيانات ──
        db_frame = ctk.CTkFrame(inner, corner_radius=8)
        db_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=6)
        db_path = str(DB_PATH)
        db_size = os.path.getsize(db_path) // 1024 if os.path.exists(db_path) else 0
        ctk.CTkLabel(db_frame, text=f"📁 قاعدة البيانات:\n{db_path}",
                     justify="right", font=F(size=11)).pack(padx=14, pady=(10, 4), anchor="e")
        ctk.CTkLabel(db_frame, text=f"📊 الحجم: {db_size} KB",
                     font=F(size=11)).pack(padx=14, pady=(0, 10), anchor="e")

        # ── نسخ احتياطي ──
        bk_frame = ctk.CTkFrame(inner, corner_radius=8)
        bk_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=8)
        bk_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(bk_frame, text="💾 نسخ احتياطي",
                     font=F(size=14, weight="bold")).grid(
            row=0, column=0, pady=(12, 6), padx=14, sticky="e")

        path_row = ctk.CTkFrame(bk_frame, fg_color="transparent")
        path_row.grid(row=1, column=0, sticky="ew", padx=14, pady=4)
        ctk.CTkLabel(path_row, text="مسار الحفظ:", font=F(size=12)).pack(side="right", padx=6)
        self.backup_path_var = ctk.StringVar(value=get_setting("backup_path", ""))
        ctk.CTkEntry(path_row, textvariable=self.backup_path_var,
                     width=240, height=32).pack(side="right", padx=4)
        ctk.CTkButton(path_row, text="📂", width=40,
                      command=self._choose_backup_path).pack(side="right")

        ctk.CTkButton(bk_frame, text="💾 إنشاء نسخة احتياطية الآن",
                      height=40, fg_color="#059669", hover_color="#047857",
                      font=F(size=13, weight="bold"),
                      command=self._do_backup).grid(
            row=2, column=0, padx=20, pady=(8, 14), sticky="ew")

        # ── استعادة ──
        rs_frame = ctk.CTkFrame(inner, corner_radius=8)
        rs_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=8)
        rs_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(rs_frame, text="📂 استعادة نسخة احتياطية",
                     font=F(size=14, weight="bold")).grid(
            row=0, column=0, pady=(12, 4), padx=14, sticky="e")
        ctk.CTkLabel(rs_frame,
                     text="⚠️ تحذير: ستُستبدل جميع البيانات الحالية!",
                     text_color="#f59e0b", font=F(size=12)).grid(
            row=1, column=0, padx=14, pady=2, sticky="e")
        ctk.CTkButton(rs_frame, text="استعادة من ملف",
                      height=38, fg_color="#dc2626", hover_color="#b91c1c",
                      font=F(size=12),
                      command=self._do_restore).grid(
            row=2, column=0, padx=20, pady=(8, 14), sticky="ew")

        self.backup_status = ctk.CTkLabel(inner, text="", font=F(size=12))
        self.backup_status.grid(row=4, column=0, pady=6)

    def _choose_backup_path(self):
        path = filedialog.askdirectory(parent=self)
        if path:
            self.backup_path_var.set(path)
            set_setting("backup_path", path)

    def _do_backup(self):
        from datetime import datetime
        backup_dir = self.backup_path_var.get().strip() or str(DB_PATH.parent)
        if not os.path.exists(backup_dir):
            messagebox.showerror("خطأ", "مسار النسخ الاحتياطي غير موجود", parent=self)
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(backup_dir, f"pharmacy_backup_{ts}.db")
        try:
            shutil.copy2(str(DB_PATH), dest)
            self.backup_status.configure(
                text=f"✅ تم: {os.path.basename(dest)}", text_color="#059669")
            messagebox.showinfo("تم", f"✅ تم إنشاء النسخة الاحتياطية:\n{dest}", parent=self)
        except Exception as e:
            messagebox.showerror("خطأ", str(e), parent=self)

    def _do_restore(self):
        backup_file = filedialog.askopenfilename(
            filetypes=[("Database Files", "*.db"), ("All Files", "*.*")], parent=self)
        if not backup_file:
            return
        if not messagebox.askyesno("تأكيد",
                                    "هل أنت متأكد؟\nسيتم استبدال جميع البيانات الحالية!",
                                    parent=self):
            return
        try:
            shutil.copy2(backup_file, str(DB_PATH))
            self.backup_status.configure(text="✅ تمت الاستعادة", text_color="#059669")
            messagebox.showinfo("تم",
                                "✅ تمت الاستعادة.\nيرجى إعادة تشغيل البرنامج.", parent=self)
        except Exception as e:
            messagebox.showerror("خطأ", str(e), parent=self)
