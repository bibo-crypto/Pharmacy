"""
screens/db_setup.py
────────────────────
شاشة إعداد قاعدة البيانات — تظهر عند أول تشغيل
أو من قائمة الإعدادات.
تدعم: SQLite محلي | SQLite على الشبكة | MySQL/MariaDB
"""
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading
import customtkinter as ctk
from database.db_config import get_config, save_config, test_connection

_BG     = "#0f172a"
_PANEL  = "#1e293b"
_CARD   = "#253047"
_BORDER = "#334155"
_FG     = "#f1f5f9"
_MUTED  = "#94a3b8"
_ACCENT = "#2563eb"
_GREEN  = "#059669"
_RED    = "#dc2626"
_YELLOW = "#d97706"


def _label(p, t, size=11, bold=False, color=None):
    return tk.Label(p, text=t, bg=p.cget("bg"),
                    fg=color or _FG,
                    font=("Segoe UI", size, "bold" if bold else "normal"),
                    anchor="e", justify="right")


def _entry(p, var, show="", w=28):
    return tk.Entry(p, textvariable=var, show=show,
                    bg="#0b1220", fg=_FG, insertbackground=_FG,
                    relief="solid", bd=1, width=w,
                    highlightthickness=1,
                    highlightbackground=_BORDER,
                    highlightcolor=_ACCENT,
                    font=("Segoe UI", 11), justify="right")


def _btn(p, text, color, cmd, w=None):
    b = tk.Button(p, text=text, bg=color, fg="#fff",
                  activebackground=color, activeforeground="#fff",
                  relief="flat", bd=0, cursor="hand2",
                  font=("Segoe UI", 10, "bold"),
                  padx=12, pady=6, command=cmd)
    if w: b.configure(width=w)
    return b


class DBSetupScreen(ctk.CTkFrame):
    """يُعرض عند أول تشغيل أو من الإعدادات."""
    def __init__(self, parent, on_done=None):
        super().__init__(parent, fg_color=_BG)
        self._on_done = on_done
        self._cfg = get_config()
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        center = tk.Frame(self, bg=_BG)
        center.grid(row=0, column=0)

        # ── عنوان ──
        tk.Label(center, text="🗄️  إعداد قاعدة البيانات",
                 font=("Segoe UI", 20, "bold"),
                 bg=_BG, fg=_FG).pack(pady=(32, 4))
        tk.Label(center,
                 text="اختر نوع الاتصال بقاعدة البيانات المشتركة",
                 font=("Segoe UI", 12), bg=_BG, fg=_MUTED).pack(pady=(0, 24))

        # ── اختيار النوع ──
        type_frame = tk.Frame(center, bg=_BG)
        type_frame.pack(fill="x", padx=40)
        self._db_type_var = tk.StringVar(value=self._cfg.get("db_type", "sqlite"))
        self._db_type_var.trace("w", lambda *_: self._on_type_change())

        for val, icon, title, desc in [
            ("sqlite", "💾", "SQLite",
             "محلي أو مشترك عبر مسار الشبكة\n(مناسب لـ 2-4 أجهزة)"),
            ("mysql",  "🐬", "MySQL / MariaDB",
             "قاعدة بيانات مركزية على سيرفر\n(مناسب لـ 5+ أجهزة)"),
        ]:
            card = tk.Frame(type_frame, bg=_CARD, bd=0,
                            highlightthickness=2,
                            highlightbackground=_BORDER,
                            cursor="hand2")
            card.pack(side="right", padx=10, pady=4, fill="both", expand=True)
            card.bind("<Button-1>", lambda e, v=val: self._db_type_var.set(v))

            inner = tk.Frame(card, bg=_CARD)
            inner.pack(padx=20, pady=16)

            tk.Radiobutton(inner, text=f"{icon}  {title}",
                           variable=self._db_type_var, value=val,
                           bg=_CARD, fg=_FG,
                           activebackground=_CARD, activeforeground=_FG,
                           selectcolor=_BG,
                           font=("Segoe UI", 13, "bold"),
                           cursor="hand2").pack(anchor="e")
            tk.Label(inner, text=desc,
                     bg=_CARD, fg=_MUTED,
                     font=("Segoe UI", 9),
                     justify="right", anchor="e").pack(anchor="e")

        # ── إعدادات SQLite ──
        self._sqlite_frame = self._build_sqlite_section(center)
        self._sqlite_frame.pack(fill="x", padx=40, pady=(16, 0))

        # ── إعدادات MySQL ──
        self._mysql_frame = self._build_mysql_section(center)
        self._mysql_frame.pack(fill="x", padx=40, pady=(16, 0))

        # ── اختبار الاتصال ──
        test_row = tk.Frame(center, bg=_BG)
        test_row.pack(pady=(20, 4))
        _btn(test_row, "🔌 اختبار الاتصال", _YELLOW, self._test).pack(side="right", padx=6)
        self._status_lbl = tk.Label(test_row, text="", bg=_BG, fg=_MUTED,
                                     font=("Segoe UI", 10))
        self._status_lbl.pack(side="right", padx=6)

        # ── أزرار ──
        actions = tk.Frame(center, bg=_BG)
        actions.pack(pady=16)
        _btn(actions, "💾 حفظ وتطبيق", _GREEN, self._save, w=18).pack(side="right", padx=8)
        if self._on_done:
            _btn(actions, "إلغاء", "#475569", self._on_done, w=10).pack(side="right", padx=8)

        self._on_type_change()

    # ── SQLite Section ────────────────────────────────────
    def _build_sqlite_section(self, parent):
        frame = tk.LabelFrame(parent, text="  إعدادات SQLite  ",
                               bg=_PANEL, fg=_ACCENT,
                               font=("Segoe UI", 11, "bold"),
                               bd=1, relief="solid",
                               labelanchor="ne")

        info_frame = tk.Frame(frame, bg=_PANEL)
        info_frame.pack(fill="x", padx=16, pady=(12, 4))

        tk.Label(info_frame,
                 text="مسار ملف قاعدة البيانات (اتركه فارغاً للمسار التلقائي):",
                 bg=_PANEL, fg=_MUTED, font=("Segoe UI", 9),
                 anchor="e").pack(anchor="e")

        path_row = tk.Frame(frame, bg=_PANEL)
        path_row.pack(fill="x", padx=16, pady=(4, 12))

        self._sqlite_path_var = tk.StringVar(
            value=self._cfg.get("sqlite_path", ""))
        path_entry = _entry(path_row, self._sqlite_path_var, w=40)
        path_entry.pack(side="right", padx=(0, 8))
        _btn(path_row, "📂 تصفح", "#334155",
             self._browse_sqlite).pack(side="right", padx=4)
        _btn(path_row, "🌐 شبكة", "#334155",
             self._set_network_example).pack(side="right", padx=4)

        # مثال
        tk.Label(frame,
                 text="مثال شبكة Windows: \\\\ServerPC\\pharmacy\\pharmacy.db\n"
                      "مثال Linux:         /mnt/server/pharmacy/pharmacy.db",
                 bg=_PANEL, fg="#64748b",
                 font=("Segoe UI", 8), justify="right", anchor="e").pack(
            padx=16, pady=(0, 12), anchor="e")

        return frame

    # ── MySQL Section ─────────────────────────────────────
    def _build_mysql_section(self, parent):
        frame = tk.LabelFrame(parent, text="  إعدادات MySQL / MariaDB  ",
                               bg=_PANEL, fg="#00b4d8",
                               font=("Segoe UI", 11, "bold"),
                               bd=1, relief="solid",
                               labelanchor="ne")

        fields_data = [
            ("عنوان السيرفر (IP أو hostname):", "mysql_host", "localhost", False),
            ("رقم المنفذ (Port):",               "mysql_port", "3306",      False),
            ("اسم قاعدة البيانات:",              "mysql_database", "pharmacy_db", False),
            ("اسم المستخدم:",                    "mysql_user", "pharmacy_user", False),
            ("كلمة المرور:",                     "mysql_password", "",      True),
        ]
        self._mysql_vars = {}

        grid = tk.Frame(frame, bg=_PANEL)
        grid.pack(fill="x", padx=16, pady=12)
        grid.grid_columnconfigure(1, weight=1)

        for i, (label, key, default, is_pw) in enumerate(fields_data):
            tk.Label(grid, text=label, bg=_PANEL, fg=_MUTED,
                     font=("Segoe UI", 10), anchor="e").grid(
                row=i, column=0, sticky="e", padx=(0, 10), pady=4)
            var = tk.StringVar(value=str(self._cfg.get(key, default)))
            self._mysql_vars[key] = var
            _entry(grid, var, show="●" if is_pw else "", w=30).grid(
                row=i, column=1, sticky="ew", pady=4)

        # زر نسخ SQL لإنشاء قاعدة البيانات
        tk.Frame(frame, height=1, bg=_BORDER).pack(fill="x", padx=16, pady=(4, 8))
        help_row = tk.Frame(frame, bg=_PANEL)
        help_row.pack(fill="x", padx=16, pady=(0, 12))
        tk.Label(help_row,
                 text="💡 تأكد من إنشاء قاعدة البيانات على السيرفر أولاً",
                 bg=_PANEL, fg=_YELLOW,
                 font=("Segoe UI", 9), anchor="e").pack(side="right")
        _btn(help_row, "📋 نسخ SQL", "#334155",
             self._copy_mysql_setup_sql).pack(side="left")

        return frame

    # ── Event Handlers ────────────────────────────────────
    def _on_type_change(self):
        t = self._db_type_var.get()
        if t == "sqlite":
            self._sqlite_frame.pack(fill="x", padx=40, pady=(16, 0))
            self._mysql_frame.pack_forget()
        else:
            self._mysql_frame.pack(fill="x", padx=40, pady=(16, 0))
            self._sqlite_frame.pack_forget()

    def _browse_sqlite(self):
        path = filedialog.askopenfilename(
            title="اختر ملف قاعدة البيانات",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
            parent=self)
        if path:
            self._sqlite_path_var.set(path)

    def _set_network_example(self):
        self._sqlite_path_var.set("\\\\ServerPC\\pharmacy\\pharmacy.db")

    def _copy_mysql_setup_sql(self):
        db = self._mysql_vars.get("mysql_database",
                                   tk.StringVar(value="pharmacy_db")).get()
        user = self._mysql_vars.get("mysql_user",
                                     tk.StringVar(value="pharmacy_user")).get()
        sql = f"""-- شغّل هذا على سيرفر MySQL:
CREATE DATABASE IF NOT EXISTS `{db}`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS '{user}'@'%'
  IDENTIFIED BY 'YOUR_PASSWORD_HERE';

GRANT ALL PRIVILEGES ON `{db}`.* TO '{user}'@'%';
FLUSH PRIVILEGES;"""
        try:
            self.clipboard_clear()
            self.clipboard_append(sql)
            messagebox.showinfo("تم النسخ",
                                "✅ تم نسخ SQL لإنشاء قاعدة البيانات.\n"
                                "الصقه في MySQL Workbench أو phpMyAdmin.",
                                parent=self)
        except Exception as e:
            messagebox.showerror("خطأ", str(e), parent=self)

    def _build_config_from_ui(self) -> dict:
        cfg = {"db_type": self._db_type_var.get()}
        if cfg["db_type"] == "sqlite":
            cfg["sqlite_path"] = self._sqlite_path_var.get().strip()
        else:
            for key, var in self._mysql_vars.items():
                val = var.get().strip()
                cfg[key] = int(val) if key == "mysql_port" and val.isdigit() else val
        return cfg

    def _test(self):
        cfg = self._build_config_from_ui()
        self._status_lbl.configure(text="⏳ جاري الاختبار...", fg=_YELLOW)
        self.update()

        def _run():
            ok, msg = test_connection(cfg)
            self.after(0, lambda: self._status_lbl.configure(
                text=msg[:60], fg=_GREEN if ok else _RED))

        threading.Thread(target=_run, daemon=True).start()

    def _save(self):
        cfg = self._build_config_from_ui()
        # اختبار سريع قبل الحفظ
        ok, msg = test_connection(cfg)
        if not ok:
            if not messagebox.askyesno(
                    "تحذير",
                    f"فشل اختبار الاتصال:\n{msg}\n\nهل تريد الحفظ على أي حال؟",
                    parent=self):
                return
        save_config(cfg)
        # أعد تهيئة قاعدة البيانات بالإعدادات الجديدة
        try:
            from database.connection import init_db
            init_db()
            messagebox.showinfo("تم",
                                "✅ تم حفظ إعدادات قاعدة البيانات وتطبيقها.",
                                parent=self)
        except Exception as e:
            messagebox.showerror("خطأ",
                                 f"تم الحفظ لكن حدث خطأ في التهيئة:\n{e}",
                                 parent=self)
        if self._on_done:
            self._on_done()
