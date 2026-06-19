import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
from models.user import (get_all_users, get_user_by_id, add_user, update_user,
                          get_all_roles, get_all_permissions,
                          get_role_permissions, update_role_permissions)
from utils.auth import has_permission, get_current_user

# ── ألوان ثابتة متوافقة مع الثيم الداكن ──
_BG      = "#111827"
_PANEL   = "#1f2937"
_BORDER  = "#334155"
_FG      = "#f1f5f9"
_MUTED   = "#94a3b8"
_ACCENT  = "#2563eb"
_SUCCESS = "#059669"
_DANGER  = "#dc2626"


def _frame(parent, **kw):
    kw.setdefault("bg", _PANEL)
    kw.setdefault("highlightthickness", 1)
    kw.setdefault("highlightbackground", _BORDER)
    return tk.Frame(parent, **kw)


def _label(parent, text, size=11, bold=False, color=None, **kw):
    kw.setdefault("bg", parent.cget("bg"))
    kw.setdefault("fg", color or _FG)
    kw.setdefault("anchor", "e")
    kw.setdefault("justify", "right")
    return tk.Label(parent, text=text,
                    font=("Segoe UI", size, "bold" if bold else "normal"),
                    **kw)


def _btn(parent, text, color=_ACCENT, fg="#fff", cmd=None, w=None, **kw):
    b = tk.Button(parent, text=text,
                  bg=color, fg=fg,
                  activebackground=color, activeforeground=fg,
                  relief="flat", borderwidth=0, cursor="hand2",
                  font=("Segoe UI", 10, "bold"),
                  padx=10, pady=5,
                  command=cmd, **kw)
    if w:
        b.configure(width=w)
    b.bind("<Enter>", lambda e: b.configure(bg=_darken(color)))
    b.bind("<Leave>", lambda e: b.configure(bg=color))
    return b


def _darken(hex_color):
    try:
        r, g, b = int(hex_color[1:3],16), int(hex_color[3:5],16), int(hex_color[5:7],16)
        r, g, b = max(0,r-25), max(0,g-25), max(0,b-25)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color


def _scrollable_frame(parent, bg=_PANEL):
    """Frame داخلي قابل للتمرير — يرجع (outer_frame, inner_frame)."""
    outer = tk.Frame(parent, bg=bg, highlightthickness=0)
    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0, borderwidth=0)
    vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=bg)
    win = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _sync(e=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
    def _resize(e):
        canvas.itemconfig(win, width=e.width)
    def _wheel(e):
        try: canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        except Exception: pass

    inner.bind("<Configure>", _sync)
    canvas.bind("<Configure>", _resize)
    canvas.bind_all("<MouseWheel>", _wheel)
    return outer, inner


class UsersScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=_BG)
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Tab Bar يدوي ──
        nav = tk.Frame(self, bg=_PANEL, height=46)
        nav.grid(row=0, column=0, sticky="ew")
        nav.grid_propagate(False)

        self._tabs = {}
        self._active_tab = tk.StringVar(value="users")

        for key, label in [("users", "إدارة المستخدمين"), ("roles", "الأدوار والصلاحيات")]:
            btn = tk.Button(nav, text=label,
                            font=("Segoe UI", 11, "bold"),
                            bg=_ACCENT if key == "users" else _PANEL,
                            fg=_FG,
                            relief="flat", borderwidth=0,
                            padx=18, pady=10, cursor="hand2",
                            command=lambda k=key: self._switch_tab(k))
            btn.pack(side="right", fill="y")
            self._tabs[key] = btn

        # ── محتوى الصفحة ──
        self._content = tk.Frame(self, bg=_BG)
        self._content.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._pages = {}
        self._build_users_page()
        self._build_roles_page()
        self._switch_tab("users")

    def _switch_tab(self, key):
        self._active_tab.set(key)
        for k, btn in self._tabs.items():
            btn.configure(bg=_ACCENT if k == key else _PANEL)
        for k, page in self._pages.items():
            if k == key:
                page.grid(row=0, column=0, sticky="nsew")
            else:
                page.grid_remove()

    # ─────────────────────────────────────────
    # صفحة المستخدمين
    # ─────────────────────────────────────────
    def _build_users_page(self):
        page = tk.Frame(self._content, bg=_BG)
        page.grid_rowconfigure(1, weight=1)
        page.grid_columnconfigure(0, weight=1)
        self._pages["users"] = page

        # Toolbar
        toolbar = tk.Frame(page, bg=_BG)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        _label(toolbar, "إدارة المستخدمين", size=16, bold=True, bg=_BG).pack(side="right", padx=8)

        for text, color, cmd in [
            ("➕ مستخدم جديد", _ACCENT,   self._add_user_dialog),
            ("✏ تعديل",        _SUCCESS,  self._edit_user_dialog),
            ("🔒 تعطيل",       _DANGER,   self._deactivate_user),
            ("🔄 تحديث",       "#475569", self._load_users),
        ]:
            _btn(toolbar, text, color=color, cmd=cmd).pack(side="left", padx=4)

        # جدول
        tbl = _frame(page, bg=_PANEL)
        tbl.grid(row=1, column=0, sticky="nsew")
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)

        cols = ("id","username","full_name","role","email","phone","is_active","last_login")
        labels = {"id":"#","username":"اسم المستخدم","full_name":"الاسم الكامل",
                  "role":"الدور","email":"البريد","phone":"الهاتف",
                  "is_active":"الحالة","last_login":"آخر تسجيل"}
        widths = {"id":40,"username":120,"full_name":160,"role":130,
                  "email":170,"phone":110,"is_active":70,"last_login":140}

        style = ttk.Style()
        style.configure("Users.Treeview",
                        background=_PANEL, fieldbackground=_PANEL,
                        foreground=_FG, rowheight=30,
                        font=("Segoe UI",11))
        style.configure("Users.Treeview.Heading",
                        background=_BG, foreground=_FG,
                        font=("Segoe UI",11,"bold"), relief="flat")
        style.map("Users.Treeview",
                  background=[("selected",_ACCENT)],
                  foreground=[("selected","#ffffff")])

        self.user_tree = ttk.Treeview(tbl, columns=cols, show="headings",
                                       style="Users.Treeview")
        for col in cols:
            self.user_tree.heading(col, text=labels[col], anchor="center")
            self.user_tree.column(col, width=widths.get(col,100), anchor="center")
        self.user_tree.tag_configure("inactive", foreground="#6b7280")
        self.user_tree.tag_configure("evenrow", background="#172033", foreground=_FG)
        self.user_tree.tag_configure("oddrow",  background=_PANEL,   foreground=_FG)

        vsb = ttk.Scrollbar(tbl, orient="vertical", command=self.user_tree.yview)
        self.user_tree.configure(yscrollcommand=vsb.set)
        self.user_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.user_tree.bind("<Double-1>", lambda e: self._edit_user_dialog())
        self._load_users()

    def _load_users(self):
        self.user_tree.delete(*self.user_tree.get_children())
        for i, u in enumerate(get_all_users()):
            base = "evenrow" if i % 2 == 0 else "oddrow"
            tag = "inactive" if not u.get("is_active") else base
            self.user_tree.insert("", "end", iid=str(u["id"]), tags=(tag,), values=(
                u["id"], u.get("username",""), u.get("full_name",""),
                u.get("role_name",""), u.get("email",""), u.get("phone",""),
                "نشط" if u.get("is_active") else "معطل",
                (u.get("last_login") or "")[:16],
            ))

    def _get_selected_uid(self):
        sel = self.user_tree.selection()
        if not sel:
            messagebox.showwarning("تحذير", "يرجى اختيار مستخدم أولاً", parent=self)
            return None
        return int(sel[0])

    def _add_user_dialog(self):
        UserFormDialog(self, None, on_save=self._load_users)

    def _edit_user_dialog(self):
        uid = self._get_selected_uid()
        if uid:
            UserFormDialog(self, get_user_by_id(uid), on_save=self._load_users)

    def _deactivate_user(self):
        uid = self._get_selected_uid()
        if not uid: return
        if uid == get_current_user()["id"]:
            messagebox.showwarning("تحذير", "لا يمكنك تعطيل حسابك الخاص", parent=self)
            return
        u = get_user_by_id(uid)
        action = "تعطيل" if u.get("is_active") else "تفعيل"
        if messagebox.askyesno("تأكيد", f"{action} المستخدم: {u['full_name']}؟", parent=self):
            data = dict(u)
            data["is_active"] = 0 if u.get("is_active") else 1
            update_user(uid, data)
            self._load_users()

    # ─────────────────────────────────────────
    # صفحة الأدوار والصلاحيات
    # ─────────────────────────────────────────
    def _build_roles_page(self):
        page = tk.Frame(self._content, bg=_BG)
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(0, weight=0)
        page.grid_columnconfigure(1, weight=1)
        self._pages["roles"] = page

        # ── عمود الأدوار ──
        left = _frame(page, bg=_PANEL, width=220)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_propagate(False)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        _label(left, "الأدوار", size=14, bold=True, bg=_PANEL).grid(
            row=0, column=0, pady=14, padx=12, sticky="e")

        roles_outer, roles_inner = _scrollable_frame(left, bg=_PANEL)
        roles_outer.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        left.grid_rowconfigure(1, weight=1)
        roles_inner.grid_columnconfigure(0, weight=1)

        self.role_buttons = {}
        for i, role in enumerate(get_all_roles()):
            btn = tk.Button(roles_inner,
                            text=role["name"],
                            bg=_PANEL, fg=_FG,
                            activebackground=_ACCENT, activeforeground="#fff",
                            font=("Segoe UI", 11),
                            relief="flat", borderwidth=0,
                            cursor="hand2", anchor="e",
                            padx=10, pady=7,
                            command=lambda r=role: self._select_role(r))
            btn.grid(row=i, column=0, sticky="ew", padx=4, pady=2)
            sep = tk.Frame(roles_inner, height=1, bg=_BORDER)
            sep.grid(row=i*2+1 if False else i+100, column=0, sticky="ew")  # skip sep
            self.role_buttons[role["id"]] = btn

        # ── عمود الصلاحيات ──
        right = _frame(page, bg=_PANEL)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # رأس
        header = tk.Frame(right, bg=_BG, height=52)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)
        self.role_title_lbl = tk.Label(header,
                                        text="← اختر دوراً من القائمة",
                                        font=("Segoe UI", 13, "bold"),
                                        bg=_BG, fg=_MUTED,
                                        anchor="e")
        self.role_title_lbl.grid(row=0, column=0, padx=16, pady=12, sticky="e")

        self.save_perms_btn = _btn(header, "💾 حفظ الصلاحيات",
                                    color=_SUCCESS, cmd=self._save_permissions)
        self.save_perms_btn.grid(row=0, column=1, padx=12, pady=10)
        self.save_perms_btn.configure(state="disabled",
                                       bg="#1f4030", fg="#4b7a5f",
                                       cursor="arrow")

        # منطقة الصلاحيات
        perms_outer, self._perms_inner = _scrollable_frame(right, bg=_PANEL)
        perms_outer.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0,8))

        self._current_role = None
        self._perm_vars    = {}

        # placeholder
        self._perms_placeholder = _label(self._perms_inner,
                                          "اختر دوراً لعرض صلاحياته",
                                          size=13, color=_MUTED, bg=_PANEL)
        self._perms_placeholder.pack(pady=40)

    def _select_role(self, role):
        self._current_role = role
        self.role_title_lbl.configure(
            text=f"صلاحيات دور: {role['name']}", fg=_FG)
        self.save_perms_btn.configure(state="normal",
                                       bg=_SUCCESS, fg="#fff", cursor="hand2")

        # تظليل الزر النشط
        for rid, btn in self.role_buttons.items():
            btn.configure(bg=_ACCENT if rid == role["id"] else _PANEL,
                          fg="#fff" if rid == role["id"] else _FG)

        # مسح الصلاحيات القديمة
        for w in self._perms_inner.winfo_children():
            w.destroy()
        self._perm_vars = {}
        self._perms_inner.grid_columnconfigure((0, 1), weight=1)

        all_perms  = get_all_permissions()
        role_perms = get_role_permissions(role["id"])

        categories: dict = {}
        for p in all_perms:
            cat = p.get("category", "عام")
            categories.setdefault(cat, []).append(p)

        row = 0
        for cat, perms in categories.items():
            # رأس الفئة
            cat_frame = tk.Frame(self._perms_inner, bg=_BG)
            cat_frame.grid(row=row, column=0, columnspan=2,
                           sticky="ew", padx=8, pady=(12, 4))
            tk.Label(cat_frame, text=f"  {cat}",
                     font=("Segoe UI", 11, "bold"),
                     bg=_BG, fg=_ACCENT,
                     anchor="e").pack(fill="x")
            tk.Frame(cat_frame, height=1, bg=_ACCENT).pack(fill="x", pady=2)
            row += 1

            col_idx = 0
            for p in perms:
                var = tk.BooleanVar(value=p["code"] in role_perms)
                cb = tk.Checkbutton(
                    self._perms_inner,
                    text=f"  {p['label']}",
                    variable=var,
                    bg=_PANEL, fg=_FG,
                    activebackground=_PANEL, activeforeground=_FG,
                    selectcolor=_BG,
                    highlightthickness=0,
                    font=("Segoe UI", 10),
                    anchor="e",
                    justify="right",
                    cursor="hand2",
                )
                cb.grid(row=row, column=col_idx,
                        sticky="e", padx=16, pady=3)
                self._perm_vars[p["code"]] = var
                col_idx += 1
                if col_idx >= 2:
                    col_idx = 0
                    row += 1
            if col_idx != 0:
                row += 1

    def _save_permissions(self):
        if not self._current_role:
            return
        selected = [code for code, var in self._perm_vars.items() if var.get()]
        update_role_permissions(self._current_role["id"], selected)
        messagebox.showinfo("تم",
                            f"✅ تم حفظ صلاحيات: {self._current_role['name']}",
                            parent=self)


# ─────────────────────────────────────────────────────────────
# نافذة إضافة / تعديل مستخدم
# ─────────────────────────────────────────────────────────────
class UserFormDialog(tk.Toplevel):
    def __init__(self, parent, user_data, on_save):
        super().__init__(parent)
        self.data    = user_data
        self.on_save = on_save
        self.title("تعديل مستخدم" if user_data else "إضافة مستخدم جديد")
        self.geometry("500x540")
        self.resizable(False, False)
        self.configure(bg=_PANEL)
        self.grab_set()
        self._build()
        if user_data:
            self._populate()

    def _build(self):
        # عنوان
        tk.Label(self, text="بيانات المستخدم",
                 font=("Segoe UI", 15, "bold"),
                 bg=_PANEL, fg=_FG).pack(pady=(20, 4))
        tk.Frame(self, height=1, bg=_BORDER).pack(fill="x", padx=24)

        body = tk.Frame(self, bg=_PANEL)
        body.pack(fill="both", expand=True, padx=24, pady=12)
        body.grid_columnconfigure((0, 1), weight=1)

        fields = [
            ("اسم المستخدم *", "username", 0, 0, 2, False),
            ("الاسم الكامل *", "full_name", 1, 0, 2, False),
            ("كلمة المرور",    "password",  2, 0, 1, True),
            ("البريد",         "email",     2, 1, 1, False),
            ("الهاتف",         "phone",     3, 0, 1, False),
        ]
        self.vars = {}
        for label, key, row, col, span, is_pw in fields:
            tk.Label(body, text=label,
                     font=("Segoe UI", 10), bg=_PANEL, fg=_MUTED,
                     anchor="e").grid(
                row=row*2, column=col, columnspan=span,
                sticky="e", padx=6, pady=(10, 2))
            var = tk.StringVar()
            e = tk.Entry(body, textvariable=var,
                         show="●" if is_pw else "",
                         bg=_BG, fg=_FG, insertbackground=_FG,
                         relief="solid", borderwidth=1,
                         highlightthickness=1,
                         highlightbackground=_BORDER,
                         highlightcolor=_ACCENT,
                         font=("Segoe UI", 11),
                         justify="right")
            e.grid(row=row*2+1, column=col, columnspan=span,
                   sticky="ew", padx=6, ipady=6)
            self.vars[key] = var

        # الدور
        tk.Label(body, text="الدور *",
                 font=("Segoe UI", 10), bg=_PANEL, fg=_MUTED,
                 anchor="e").grid(row=6, column=1, sticky="e", padx=6, pady=(10,2))
        roles = get_all_roles()
        self.role_names = [r["name"] for r in roles]
        self.role_ids   = [r["id"]   for r in roles]
        self.role_var   = tk.StringVar(value=self.role_names[0] if self.role_names else "")
        role_cb = ttk.Combobox(body, textvariable=self.role_var,
                               values=self.role_names,
                               state="readonly",
                               font=("Segoe UI", 11),
                               justify="right")
        role_cb.grid(row=7, column=1, sticky="ew", padx=6, ipady=4)

        # مستخدم نشط
        self.active_var = tk.BooleanVar(value=True)
        tk.Checkbutton(body, text="مستخدم نشط",
                       variable=self.active_var,
                       bg=_PANEL, fg=_FG,
                       activebackground=_PANEL, activeforeground=_FG,
                       selectcolor=_BG,
                       font=("Segoe UI", 11),
                       cursor="hand2").grid(
            row=7, column=0, padx=6, sticky="w")

        if not self.data:
            tk.Label(body, text="* كلمة المرور الافتراضية: 123456",
                     font=("Segoe UI", 9), bg=_PANEL,
                     fg=_MUTED).grid(
                row=8, column=0, columnspan=2, pady=6)

        # أزرار
        tk.Frame(self, height=1, bg=_BORDER).pack(fill="x", padx=24)
        btns = tk.Frame(self, bg=_PANEL)
        btns.pack(pady=14)
        _btn(btns, "💾 حفظ", color=_SUCCESS, cmd=self._save, w=12).pack(side="left", padx=8)
        _btn(btns, "إلغاء", color="#475569", cmd=self.destroy, w=10).pack(side="left", padx=8)

    def _populate(self):
        self.vars["username"].set(self.data.get("username",""))
        self.vars["full_name"].set(self.data.get("full_name",""))
        self.vars["email"].set(self.data.get("email","") or "")
        self.vars["phone"].set(self.data.get("phone","") or "")
        self.active_var.set(bool(self.data.get("is_active",1)))
        rname = self.data.get("role_name","")
        if rname in self.role_names:
            self.role_var.set(rname)

    def _save(self):
        username  = self.vars["username"].get().strip()
        full_name = self.vars["full_name"].get().strip()
        if not username or not full_name:
            messagebox.showerror("خطأ", "اسم المستخدم والاسم الكامل مطلوبان", parent=self)
            return
        rname = self.role_var.get()
        if rname not in self.role_names:
            messagebox.showerror("خطأ", "يرجى اختيار دور", parent=self)
            return
        role_id = self.role_ids[self.role_names.index(rname)]
        data = {
            "username":  username,
            "full_name": full_name,
            "email":     self.vars["email"].get().strip(),
            "phone":     self.vars["phone"].get().strip(),
            "role_id":   role_id,
            "is_active": int(self.active_var.get()),
        }
        from utils.auth import hash_password
        pw = self.vars["password"].get().strip()
        if pw:
            data["password"] = hash_password(pw)
        if self.data:
            update_user(self.data["id"], data)
        else:
            data.setdefault("password", hash_password("123456"))
            add_user(data)
        self.on_save()
        self.destroy()
