import customtkinter as ctk
from tkinter import messagebox, ttk
from models.customer import get_all_customers, get_customer_by_id, add_customer, update_customer, delete_customer, get_customer_purchases
from utils.helpers import get_setting


class CustomersScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        ctk.CTkLabel(toolbar, text="إدارة العملاء",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="right")
        btn_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_frame.pack(side="left")
        ctk.CTkButton(btn_frame, text="➕ عميل جديد", width=120,
                      command=self._add_dialog).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="✏️ تعديل", width=100,
                      fg_color="#059669", command=self._edit_dialog).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="🗑 حذف", width=100,
                      fg_color="#dc2626", command=self._delete).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="📋 مشتريات العميل", width=140,
                      fg_color="#7c3aed", command=self._view_purchases).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="🔄 تحديث", width=100,
                      fg_color="gray", command=self._load).pack(side="left", padx=4)

        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *a: self._load())
        ctk.CTkEntry(filter_frame, textvariable=self.search_var,
                     placeholder_text="🔍 بحث بالاسم أو الهاتف...",
                     width=260, height=36).pack(side="right", padx=4)

        table_frame = ctk.CTkFrame(self, corner_radius=10)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 16))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "name", "phone", "email", "address", "loyalty", "created")
        labels = {"id": "#", "name": "الاسم", "phone": "الهاتف", "email": "البريد",
                  "address": "العنوان", "loyalty": "نقاط الولاء", "created": "تاريخ التسجيل"}
        widths = {"id": 40, "name": 160, "phone": 110, "email": 150,
                  "address": 150, "loyalty": 80, "created": 120}

        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        ctk.configure_treeview(self.tree)
        for col in cols:
            self.tree.heading(col, text=labels[col], anchor="center")
            self.tree.column(col, width=widths.get(col, 100), anchor="center")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Double-1>", lambda e: self._edit_dialog())

        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self.status_label.grid(row=3, column=0, sticky="e", padx=20, pady=(0, 8))
        self._load()

    def _load(self):
        cust = get_all_customers(search=self.search_var.get().strip() or None)
        self.tree.delete(*self.tree.get_children())
        for _i_c, c in enumerate(cust):
            _row_tag = "evenrow" if _i_c % 2 == 0 else "oddrow"
            self.tree.insert("", "end", tags=(_row_tag,), iid=str(c["id"]), values=(
                c["id"], c["name"], c.get("phone", ""), c.get("email", ""),
                c.get("address", ""), c.get("loyalty_points", 0),
                c.get("created_at", "")[:10],
            ))
        self.status_label.configure(text=f"إجمالي العملاء: {len(cust)}")

    def _get_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("تحذير", "يرجى اختيار عميل أولاً")
            return None
        return int(sel[0])

    def _add_dialog(self):
        CustomerFormDialog(self, None, on_save=self._load)

    def _edit_dialog(self):
        cid = self._get_selected()
        if not cid:
            return
        c = get_customer_by_id(cid)
        CustomerFormDialog(self, c, on_save=self._load)

    def _delete(self):
        cid = self._get_selected()
        if not cid:
            return
        c = get_customer_by_id(cid)
        if messagebox.askyesno("تأكيد", f"حذف العميل: {c['name']}؟"):
            delete_customer(cid)
            self._load()

    def _view_purchases(self):
        cid = self._get_selected()
        if not cid:
            return
        c = get_customer_by_id(cid)
        purchases = get_customer_purchases(cid)
        CustomerPurchasesDialog(self, c, purchases)


class CustomerFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, customer_data, on_save):
        super().__init__(parent)
        self.data = customer_data
        self.on_save = on_save
        self.title("تعديل عميل" if customer_data else "إضافة عميل")
        self.geometry("460x400")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        if customer_data:
            self._populate()

    def _build(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=20)
        frame.grid_columnconfigure((0, 1), weight=1)

        fields = [
            ("الاسم *", "name", 0, 0, 2),
            ("الهاتف", "phone", 1, 0, 1),
            ("البريد الإلكتروني", "email", 1, 1, 1),
            ("العنوان", "address", 2, 0, 2),
        ]
        self.vars = {}
        for label, key, row, col, span in fields:
            ctk.CTkLabel(frame, text=label, anchor="e").grid(
                row=row * 2, column=col, columnspan=span, sticky="e", padx=6, pady=(8, 2))
            var = ctk.StringVar()
            ctk.CTkEntry(frame, textvariable=var, height=36, justify="right").grid(
                row=row * 2 + 1, column=col, columnspan=span, sticky="ew", padx=6, pady=(0, 4))
            self.vars[key] = var

        ctk.CTkLabel(frame, text="ملاحظات", anchor="e").grid(
            row=6, column=0, columnspan=2, sticky="e", padx=6, pady=(8, 2))
        self.notes_text = ctk.CTkTextbox(frame, height=60)
        self.notes_text.grid(row=7, column=0, columnspan=2, sticky="ew", padx=6)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=8, column=0, columnspan=2, pady=12)
        ctk.CTkButton(btn_frame, text="💾 حفظ", width=110, command=self._save).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="إلغاء", width=100, fg_color="gray",
                      command=self.destroy).pack(side="left", padx=8)

    def _populate(self):
        for key in ("name", "phone", "email", "address"):
            self.vars[key].set(self.data.get(key, "") or "")
        if self.data.get("notes"):
            self.notes_text.insert("1.0", self.data["notes"])

    def _save(self):
        name = self.vars["name"].get().strip()
        if not name:
            messagebox.showerror("خطأ", "الاسم مطلوب", parent=self)
            return
        data = {k: self.vars[k].get().strip() for k in ("name", "phone", "email", "address")}
        data["notes"] = self.notes_text.get("1.0", "end").strip()
        if self.data:
            update_customer(self.data["id"], data)
        else:
            add_customer(data)
        self.on_save()
        self.destroy()


class CustomerPurchasesDialog(ctk.CTkToplevel):
    def __init__(self, parent, customer, purchases):
        super().__init__(parent)
        self.title(f"مشتريات العميل: {customer['name']}")
        self.geometry("640x420")
        self.grab_set()
        ctk.CTkLabel(self, text=f"عدد الفواتير: {len(purchases)} | إجمالي: {sum(p.get('total',0) for p in purchases):.2f}",
                     font=ctk.CTkFont(size=13)).pack(pady=10)
        cols = ("invoice", "cashier", "total", "payment", "date")
        labels = {"invoice": "الفاتورة", "cashier": "الكاشير",
                  "total": "الإجمالي", "payment": "الدفع", "date": "التاريخ"}
        tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        for _i_col, col in enumerate(cols):
            _row_tag = "evenrow" if _i_col % 2 == 0 else "oddrow"
            tree.heading(col, text=labels[col])
            tree.column(col, width=120, anchor="center")
        for _i_p, p in enumerate(purchases):
            _row_tag = "evenrow" if _i_p % 2 == 0 else "oddrow"
            tree.insert("", "end", tags=(_row_tag,), values=(
                p.get("invoice_number", ""),
                p.get("cashier_name", ""),
                f"{p.get('total', 0):.2f}",
                p.get("payment_method", ""),
                p.get("sale_date", "")[:16],
            ))
        tree.pack(fill="both", expand=True, padx=16, pady=8)
        ctk.CTkButton(self, text="إغلاق", command=self.destroy).pack(pady=8)
