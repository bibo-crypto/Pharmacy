import sys
import os

# ── مسار التشغيل: يعمل مع PyInstaller (frozen) والتشغيل المباشر ──
if getattr(sys, 'frozen', False):
    # نحن داخل ملف EXE مُجمَّع بـ PyInstaller
    _BASE_DIR = sys._MEIPASS          # مجلد temp المستخرج تلقائياً
    _APP_DIR  = os.path.dirname(sys.executable)  # مجلد الـ EXE نفسه
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _APP_DIR  = _BASE_DIR

# أضف مسار الـ base للـ path حتى تُوجد packages
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

# اجعل البيانات (DB + receipts + assets) تُكتب في مجلد الـ EXE
os.environ.setdefault("PHARMACY_DATA_DIR", _APP_DIR)

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox

from database import init_db
from utils.helpers import get_setting
from utils.auth import get_current_user, logout, has_permission


class PharmacyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("نظام إدارة الصيدلية")
        self.geometry("1366x768")
        self.minsize(1024, 650)
        try:
            self.state("zoomed")
        except Exception:
            pass
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        init_db()
        # تهيئة ThemeManager وتطبيق الثيم المحفوظ
        try:
            from utils.theme_manager import ThemeManager
            self._theme_manager = ThemeManager.instance()
        except Exception:
            pass
        self._apply_theme()
        self._show_login()

    def _apply_theme(self):
        theme      = get_setting("theme", "blue")
        appearance = get_setting("appearance", "dark")
        ctk.set_appearance_mode(appearance)
        try:
            ctk.set_default_color_theme(theme)
        except Exception:
            ctk.set_default_color_theme("blue")
        # تطبيق ThemeManager (يُطبّق الإعدادات المخصصة المحفوظة)
        try:
            from utils.theme_manager import ThemeManager
            ThemeManager.instance().apply()
        except Exception:
            pass

    def _show_login(self):
        for w in self.winfo_children():
            w.destroy()
        self.configure(fg_color=("#f0f2f5", "#1a1a2e"))
        # تحقق من إعداد قاعدة البيانات — عرض الشاشة عند أول تشغيل
        import os as _os
        from database.db_config import _config_dir
        _cfg_path = _config_dir() / "db_config.json"
        if not _cfg_path.is_file():
            self._show_db_setup_first()
            return
        from screens.login import LoginScreen
        login_frame = LoginScreen(self, on_success=self._on_login_success)
        login_frame.grid(row=0, column=0, sticky="nsew")
        self.title(f"نظام إدارة الصيدلية - {get_setting('pharmacy_name','صيدلية الأمل')}")

    def _show_db_setup_first(self):
        """يعرض شاشة إعداد DB عند أول تشغيل."""
        from screens.db_setup import DBSetupScreen
        for w in self.winfo_children():
            w.destroy()
        ctk.CTkLabel(self, text="🗄️  مرحباً — أعدّ قاعدة البيانات أولاً",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 4))
        DBSetupScreen(self, on_done=self._show_login).pack(
            fill="both", expand=True)

    def _on_login_success(self, user):
        for w in self.winfo_children():
            w.destroy()
        self._build_main_ui()

    def _build_main_ui(self):
        self.configure(fg_color=("#f0f4f8", "#0f0f1a"))
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self._build_sidebar()
        self._build_content_area()
        self._show_screen("dashboard")

    # ─────────────────────────────────────────
    # Sidebar — قابل للتمرير، مضغوط
    # ─────────────────────────────────────────
    def _build_sidebar(self):
        SIDEBAR_BG = "#0d1117"
        SIDEBAR_W  = 210

        # Outer container
        self.sidebar = tk.Frame(self, width=SIDEBAR_W, bg=SIDEBAR_BG)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(0, weight=0)  # logo
        self.sidebar.grid_rowconfigure(1, weight=1)  # scrollable nav
        self.sidebar.grid_rowconfigure(2, weight=0)  # user + logout
        self.sidebar.grid_columnconfigure(0, weight=1)

        user          = get_current_user()
        pharmacy_name = get_setting("pharmacy_name", "صيدلية الأمل")

        # ── شعار + اسم الصيدلية ──
        logo_frame = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        logo_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(14, 6))
        tk.Label(logo_frame, text="💊", font=("Segoe UI", 26),
                 bg=SIDEBAR_BG, fg="white").pack()
        tk.Label(logo_frame, text=pharmacy_name, font=("Segoe UI", 11, "bold"),
                 bg=SIDEBAR_BG, fg="white", wraplength=180,
                 justify="center").pack()
        tk.Frame(logo_frame, height=1, bg="#1e293b").pack(fill="x", pady=(8, 0))

        # ── Canvas + Scrollbar للتنقل ──
        nav_canvas  = tk.Canvas(self.sidebar, bg=SIDEBAR_BG,
                                 highlightthickness=0, borderwidth=0)
        nav_vsb     = ttk.Scrollbar(self.sidebar, orient="vertical",
                                     command=nav_canvas.yview)
        nav_canvas.configure(yscrollcommand=nav_vsb.set)

        nav_canvas.grid(row=1, column=0, sticky="nsew")
        # نُظهر الـ scrollbar فقط عند الحاجة (تلقائي)

        nav_inner = tk.Frame(nav_canvas, bg=SIDEBAR_BG)
        nav_win   = nav_canvas.create_window((0, 0), window=nav_inner, anchor="nw")

        def _on_nav_configure(e=None):
            nav_canvas.configure(scrollregion=nav_canvas.bbox("all"))
            # إخفاء/إظهار الـ scrollbar تلقائياً
            bbox = nav_canvas.bbox("all")
            if bbox and (bbox[3] - bbox[1]) > nav_canvas.winfo_height():
                nav_vsb.grid(row=1, column=1, sticky="ns")
            else:
                nav_vsb.grid_remove()

        def _on_canvas_resize(e):
            nav_canvas.itemconfig(nav_win, width=e.width)

        def _on_mousewheel(e):
            try: nav_canvas.yview_scroll(int(-1*(e.delta/120)), "units")
            except Exception: pass

        nav_inner.bind("<Configure>",  _on_nav_configure)
        nav_canvas.bind("<Configure>", _on_canvas_resize)
        nav_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ── أزرار التنقل ──
        self._nav_buttons = {}
        nav_items = self._get_nav_items()

        for key, icon, label, perm in nav_items:
            if perm and not has_permission(perm):
                continue
            btn = tk.Button(
                nav_inner,
                text=f" {icon}  {label}",
                anchor="e",
                bg=SIDEBAR_BG,
                fg="#94a3b8",
                activebackground="#1e293b",
                activeforeground="white",
                relief="flat", borderwidth=0,
                cursor="hand2",
                padx=8, pady=5,
                font=("Segoe UI", 11),
                width=22,
                command=lambda k=key: self._show_screen(k),
            )
            btn.pack(fill="x", padx=6, pady=1)
            self._nav_buttons[key] = btn

        # ── فاصل + مستخدم + خروج (ثابت أسفل) ──
        bottom_frame = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        bottom_frame.grid(row=2, column=0, sticky="ew")

        tk.Frame(bottom_frame, height=1, bg="#1e293b").pack(fill="x")

        tk.Label(bottom_frame,
                 text=f"👤 {user['full_name'][:16]}",
                 font=("Segoe UI", 10),
                 bg=SIDEBAR_BG, fg="#64748b",
                 anchor="e", justify="right").pack(
            fill="x", padx=10, pady=(6, 1))
        tk.Label(bottom_frame,
                 text=user.get("role_name", ""),
                 font=("Segoe UI", 9),
                 bg=SIDEBAR_BG, fg="#475569",
                 anchor="e", justify="right").pack(
            fill="x", padx=10, pady=(0, 4))

        tk.Button(
            bottom_frame,
            text="🚪  تسجيل الخروج",
            bg=SIDEBAR_BG, fg="#ef4444",
            activebackground="#1a0a0a", activeforeground="#ef4444",
            relief="flat", borderwidth=0,
            cursor="hand2", padx=8, pady=6,
            font=("Segoe UI", 10, "bold"),
            anchor="e",
            command=self._logout,
        ).pack(fill="x", padx=6, pady=(0, 10))

    def _get_nav_items(self):
        return [
            ("dashboard",  "🏠", "لوحة التحكم",    None),
            ("pos",        "🖥", "نقطة البيع",      "create_sales"),
            ("cashier",    "💵", "الكاشير",         "create_sales"),
            ("medicines",  "💊", "الأدوية",         "view_medicines"),
            ("sales",      "📋", "المبيعات",        "view_sales"),
            ("purchases",  "🛒", "المشتريات",       "view_purchases"),
            ("inventory",  "📦", "المخزون",         "manage_inventory"),
            ("customers",  "👥", "العملاء",         "manage_customers"),
            ("suppliers",  "🏭", "الموردين",        "manage_suppliers"),
            ("returns",    "↩",  "المرتجعات",       "process_returns"),
            ("treasury",   "💰", "الخزينة",         "manage_treasury"),
            ("reports",    "📊", "التقارير",        "view_reports"),
            ("users",      "👤", "المستخدمون",      "manage_users"),
            ("audit_logs", "📝", "سجل العمليات",    "manage_users"),
            ("settings",      "⚙",  "الإعدادات",       "manage_settings"),
            ("db_setup",      "🗄", "إعداد قاعدة البيانات", "manage_settings"),
            ("theme_designer", "🎨", "مصمم المظهر",     "manage_settings"),
        ]

    def _highlight_nav(self, active_key: str):
        SIDEBAR_BG = "#0d1117"
        ACTIVE_BG  = "#2563eb"
        for key, btn in self._nav_buttons.items():
            if key == active_key:
                btn.configure(bg=ACTIVE_BG, fg="white",
                              activebackground=ACTIVE_BG)
            else:
                btn.configure(bg=SIDEBAR_BG, fg="#94a3b8",
                              activebackground="#1e293b",
                              activeforeground="white")

    # ─────────────────────────────────────────
    # Content area
    # ─────────────────────────────────────────
    def _build_content_area(self):
        self.content_frame = ctk.CTkFrame(self, corner_radius=0,
                                           fg_color=("gray92", "#111827"))
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_rowconfigure(1, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.topbar = ctk.CTkFrame(self.content_frame, height=50, corner_radius=0,
                                    fg_color=("#ffffff", "#1f2937"))
        self.topbar.grid(row=0, column=0, sticky="ew")
        self.topbar.grid_columnconfigure(1, weight=1)
        self.topbar.grid_propagate(False)

        self.page_title_label = ctk.CTkLabel(
            self.topbar, text="لوحة التحكم",
            font=ctk.CTkFont(size=16, weight="bold"), anchor="e")
        self.page_title_label.grid(row=0, column=0, padx=20, pady=8, sticky="e")

        self.clock_label = ctk.CTkLabel(self.topbar, text="",
                                         font=ctk.CTkFont(size=11),
                                         text_color="gray")
        self.clock_label.grid(row=0, column=2, padx=20, sticky="w")
        self._update_clock()

        self.screen_container = ctk.CTkFrame(self.content_frame,
                                              fg_color="transparent")
        self.screen_container.grid(row=1, column=0, sticky="nsew")
        self.screen_container.grid_rowconfigure(0, weight=1)
        self.screen_container.grid_columnconfigure(0, weight=1)

    def _update_clock(self):
        from datetime import datetime
        self.clock_label.configure(
            text=datetime.now().strftime("%H:%M:%S  |  %Y/%m/%d"))
        self.after(1000, self._update_clock)

    def _show_screen(self, screen_key: str):
        for w in self.screen_container.winfo_children():
            w.destroy()

        self._highlight_nav(screen_key)

        titles = {
            "dashboard": "لوحة التحكم",    "pos":       "نقطة البيع",
            "cashier":   "شاشة الكاشير",   "medicines": "إدارة الأدوية",
            "sales":     "سجل المبيعات",   "purchases": "إدارة المشتريات",
            "inventory": "إدارة المخزون",  "customers": "إدارة العملاء",
            "suppliers": "إدارة الموردين", "returns":   "المرتجعات",
            "treasury":  "الخزينة",        "reports":   "التقارير",
            "users":     "إدارة المستخدمين","audit_logs":"سجل العمليات",
            "settings":       "الإعدادات",
            "db_setup":       "إعداد قاعدة البيانات",
            "theme_designer":  "مصمم المظهر — Theme Designer",
        }
        self.page_title_label.configure(text=titles.get(screen_key, ""))

        screen = self._load_screen(screen_key)
        if screen:
            screen.grid(row=0, column=0, sticky="nsew")

    def _load_screen(self, key):
        try:
            m = {
                "dashboard":  ("screens.dashboard",  "DashboardScreen"),
                "pos":        ("screens.pos",         "POSScreen"),
                "cashier":    ("screens.cashier",     "CashierScreen"),
                "medicines":  ("screens.medicines",   "MedicinesScreen"),
                "sales":      ("screens.sales",       "SalesScreen"),
                "purchases":  ("screens.purchases",   "PurchasesScreen"),
                "inventory":  ("screens.inventory",   "InventoryScreen"),
                "customers":  ("screens.customers",   "CustomersScreen"),
                "suppliers":  ("screens.suppliers",   "SuppliersScreen"),
                "returns":    ("screens.returns",     "ReturnsScreen"),
                "treasury":   ("screens.treasury",    "TreasuryScreen"),
                "reports":    ("screens.reports",     "ReportsScreen"),
                "users":      ("screens.users",       "UsersScreen"),
                "audit_logs": ("screens.audit_logs",  "AuditLogsScreen"),
                "settings":       ("screens.settings",       "SettingsScreen"),
                "db_setup":       ("screens.db_setup",       "DBSetupScreen"),
                "theme_designer": ("screens.theme_designer", "ThemeDesignerScreen"),
            }
            if key not in m:
                return None
            mod_name, cls_name = m[key]
            mod = __import__(mod_name, fromlist=[cls_name])
            cls = getattr(mod, cls_name)
            return cls(self.screen_container)
        except Exception as e:
            import traceback
            err = ctk.CTkFrame(self.screen_container)
            err.grid_rowconfigure(0, weight=1)
            err.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(err,
                         text=f"⚠️ خطأ في تحميل الشاشة:\n{e}\n\n{traceback.format_exc()[:600]}",
                         text_color="red", wraplength=700,
                         font=ctk.CTkFont(size=12)).grid(
                row=0, column=0, padx=20, pady=20)
            return err

    def _logout(self):
        if messagebox.askyesno("تسجيل الخروج", "هل تريد تسجيل الخروج؟"):
            logout()
            self._show_login()


def main():
    app = PharmacyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
