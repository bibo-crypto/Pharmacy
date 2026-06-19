import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
from utils.audit import get_audit_logs
from models.user import get_all_users


class AuditLogsScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        ctk.CTkLabel(toolbar, text="سجل العمليات",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="right")
        btn_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_frame.pack(side="left")
        ctk.CTkButton(btn_frame, text="🔄 تحديث", width=100,
                      fg_color="gray", command=self._load).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="📥 تصدير", width=100,
                      fg_color="#059669", command=self._export).pack(side="left", padx=4)

        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))

        users = get_all_users()
        self.user_names = ["الكل"] + [u["full_name"] for u in users]
        self.user_ids_map = {u["full_name"]: u["id"] for u in users}
        self.user_filter_var = ctk.StringVar(value="الكل")
        ctk.CTkOptionMenu(filter_frame, values=self.user_names,
                          variable=self.user_filter_var,
                          command=lambda v: self._load(),
                          width=150).pack(side="right", padx=4)

        ctk.CTkLabel(filter_frame, text="المستخدم:").pack(side="right", padx=4)

        actions = ["الكل", "login", "logout", "add", "edit", "delete",
                   "create_sale", "cancel_sale", "create_purchase",
                   "process_returns", "open_shift", "close_shift", "treasury_income",
                   "treasury_expense"]
        self.action_filter_var = ctk.StringVar(value="الكل")
        ctk.CTkOptionMenu(filter_frame, values=actions,
                          variable=self.action_filter_var,
                          command=lambda v: self._load(),
                          width=150).pack(side="right", padx=4)
        ctk.CTkLabel(filter_frame, text="العملية:").pack(side="right", padx=4)

        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *a: self._load())
        ctk.CTkEntry(filter_frame, textvariable=self.search_var,
                     placeholder_text="🔍 بحث...", width=220, height=36).pack(side="left", padx=4)

        ctk.CTkLabel(filter_frame, text="عدد السجلات:").pack(side="left", padx=8)
        self.limit_var = ctk.StringVar(value="200")
        ctk.CTkOptionMenu(filter_frame, values=["50", "100", "200", "500"],
                          variable=self.limit_var,
                          command=lambda v: self._load(),
                          width=80).pack(side="left")

        table_frame = ctk.CTkFrame(self, corner_radius=10)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 12))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "user", "action", "table_name", "record_id", "timestamp")
        labels = {"id": "#", "user": "المستخدم", "action": "العملية",
                  "table_name": "الجدول", "record_id": "رقم السجل", "timestamp": "الوقت"}
        widths = {"id": 40, "user": 130, "action": 130, "table_name": 110,
                  "record_id": 80, "timestamp": 140}


        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        ctk.configure_treeview(self.tree)
        for col in cols:
            self.tree.heading(col, text=labels[col], anchor="center")
            self.tree.column(col, width=widths.get(col, 100), anchor="center")

        self.tree.tag_configure("login", foreground="#059669")
        self.tree.tag_configure("delete", foreground="#dc2626")
        self.tree.tag_configure("sale", foreground="#2563eb")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Double-1>", self._show_detail)

        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self.status_label.grid(row=3, column=0, sticky="e", padx=20, pady=(0, 8))

        self._load()

    def _load(self):
        user_name = self.user_filter_var.get()
        user_id = self.user_ids_map.get(user_name) if user_name != "الكل" else None
        action = self.action_filter_var.get()
        if action == "الكل":
            action = None
        try:
            limit = int(self.limit_var.get())
        except ValueError:
            limit = 200

        logs = get_audit_logs(limit=limit, user_id=user_id, action=action)

        search = self.search_var.get().strip().lower()
        if search:
            logs = [l for l in logs if search in (l.get("full_name", "") + l.get("action", "") +
                                                    (l.get("table_name", "") or "")).lower()]

        self.tree.delete(*self.tree.get_children())
        self._logs_cache = logs
        for log in logs:
            action_val = log.get("action", "")
            tag = ""
            if "login" in action_val:
                tag = "login"
            elif "delete" in action_val or "cancel" in action_val:
                tag = "delete"
            elif "sale" in action_val:
                tag = "sale"
            self.tree.insert("", "end", iid=str(log["id"]), tags=(tag,), values=(
                log["id"],
                log.get("full_name", log.get("username", "")),
                action_val,
                log.get("table_name", "") or "",
                log.get("record_id", "") or "",
                log.get("timestamp", "")[:19],
            ))
        self.status_label.configure(text=f"إجمالي السجلات: {len(logs)}")

    def _show_detail(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        log_id = int(sel[0])
        log = next((l for l in getattr(self, "_logs_cache", []) if l["id"] == log_id), None)
        if not log:
            return
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"تفاصيل العملية #{log_id}")
        dlg.geometry("540x400")
        dlg.grab_set()

        scroll = ctk.CTkScrollableFrame(dlg)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)
        _si = scroll.get_inner()

        items = [
            ("المستخدم", log.get("full_name", "")),
            ("العملية", log.get("action", "")),
            ("الجدول", log.get("table_name", "") or ""),
            ("رقم السجل", str(log.get("record_id", "") or "")),
            ("الوقت", log.get("timestamp", "")),
            ("القيم القديمة", log.get("old_values", "") or ""),
            ("القيم الجديدة", log.get("new_values", "") or ""),
        ]
        for label, val in items:
            row_frame = ctk.CTkFrame(_si, fg_color="transparent")
            row_frame.pack(fill="x", pady=3)
            ctk.CTkLabel(row_frame, text=label + ":",
                         font=ctk.CTkFont(weight="bold"), width=120).pack(side="right")
            ctk.CTkLabel(row_frame, text=str(val),
                         anchor="w", wraplength=350).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dlg, text="إغلاق", command=dlg.destroy).pack(pady=8)

    def _export(self):
        try:
            import openpyxl
            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx")],
                initialfile="audit_logs.xlsx", parent=self)
            if not path:
                return
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "سجل العمليات"
            ws.append(["#", "المستخدم", "العملية", "الجدول", "رقم السجل", "الوقت"])
            logs = getattr(self, "_logs_cache", [])
            for log in logs:
                ws.append([
                    log["id"], log.get("full_name", ""), log.get("action", ""),
                    log.get("table_name", "") or "", log.get("record_id", "") or "",
                    log.get("timestamp", ""),
                ])
            wb.save(path)
            messagebox.showinfo("تم", f"تم التصدير إلى:\n{path}", parent=self)
        except ImportError:
            messagebox.showerror("خطأ", "يرجى تثبيت openpyxl", parent=self)
        except Exception as e:
            messagebox.showerror("خطأ", str(e), parent=self)
