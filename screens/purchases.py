import customtkinter as ctk
from tkinter import messagebox, ttk
from models.purchase import create_purchase, get_all_purchases, get_purchase_by_id
from models.medicine import get_all_medicines
from models.supplier import get_all_suppliers
from utils.auth import get_current_user, has_permission
from utils.helpers import get_setting


class PurchasesScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        ctk.CTkLabel(toolbar, text="إدارة المشتريات",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="right")
        btn_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_frame.pack(side="left")
        if has_permission("create_purchases"):
            ctk.CTkButton(btn_frame, text="➕ فاتورة شراء جديدة", width=160,
                          command=self._new_purchase).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="👁 تفاصيل", width=100,
                      command=self._view_details).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="🔄 تحديث", width=100,
                      fg_color="gray", command=self._load).pack(side="left", padx=4)

        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *a: self._load())
        ctk.CTkEntry(filter_frame, textvariable=self.search_var,
                     placeholder_text="🔍 بحث...", width=220, height=36).pack(side="right", padx=4)
        self.date_from_var = ctk.StringVar()
        ctk.CTkEntry(filter_frame, textvariable=self.date_from_var,
                     placeholder_text="من YYYY-MM-DD", width=130, height=36).pack(side="right", padx=2)
        self.date_to_var = ctk.StringVar()
        ctk.CTkEntry(filter_frame, textvariable=self.date_to_var,
                     placeholder_text="إلى YYYY-MM-DD", width=130, height=36).pack(side="right", padx=2)
        ctk.CTkButton(filter_frame, text="بحث", width=70, command=self._load).pack(side="right", padx=4)

        table_frame = ctk.CTkFrame(self, corner_radius=10)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 8))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "invoice", "supplier", "user", "total", "paid", "payment", "date", "status")
        labels = {"id": "#", "invoice": "رقم الفاتورة", "supplier": "المورد",
                  "user": "المستخدم", "total": "الإجمالي", "paid": "المدفوع",
                  "payment": "الدفع", "date": "التاريخ", "status": "الحالة"}
        widths = {"id": 40, "invoice": 160, "supplier": 130, "user": 100,
                  "total": 90, "paid": 90, "payment": 80, "date": 130, "status": 70}

        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        ctk.configure_treeview(self.tree)
        for col in cols:
            self.tree.heading(col, text=labels[col], anchor="center")
            self.tree.column(col, width=widths.get(col, 80), anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Double-1>", lambda e: self._view_details())

        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12),
                                          text_color="gray")
        self.status_label.grid(row=3, column=0, sticky="e", padx=20, pady=(0, 12))
        self._load()

    def _load(self):
        purchases = get_all_purchases(
            search=self.search_var.get().strip() or None,
            date_from=self.date_from_var.get().strip() or None,
            date_to=self.date_to_var.get().strip() or None,
        )
        self.tree.delete(*self.tree.get_children())
        total_cost = 0
        for _i_p, p in enumerate(purchases):
            _row_tag = "evenrow" if _i_p % 2 == 0 else "oddrow"
            self.tree.insert("", "end", tags=(_row_tag,), iid=str(p["id"]), values=(
                p["id"], p.get("invoice_number", ""),
                p.get("supplier_name", "")[:16],
                p.get("user_name", "")[:12],
                f"{p.get('total', 0):.2f}",
                f"{p.get('paid_amount', 0):.2f}",
                p.get("payment_method", ""),
                p.get("purchase_date", "")[:16],
                p.get("status", ""),
            ))
            total_cost += p.get("total", 0)
        cur = get_setting("currency", "ج.م")
        self.status_label.configure(
            text=f"إجمالي الفواتير: {len(purchases)} | إجمالي التكلفة: {total_cost:.2f} {cur}")

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("تحذير", "يرجى اختيار فاتورة أولاً")
            return None
        return int(sel[0])

    def _view_details(self):
        pid = self._get_selected_id()
        if not pid:
            return
        purchase, items = get_purchase_by_id(pid)
        if purchase:
            PurchaseDetailDialog(self, purchase, items)

    def _new_purchase(self):
        NewPurchaseDialog(self, on_save=self._load)


class NewPurchaseDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save):
        super().__init__(parent)
        self.on_save = on_save
        self.cart_items = []
        self.title("فاتورة شراء جديدة")
        self.geometry("860x640")
        self.grab_set()
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))
        top.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(top, text="المورد *:", anchor="e").grid(row=0, column=3, sticky="e", padx=6)
        suppliers = get_all_suppliers()
        self.supplier_names = [s["name"] for s in suppliers]
        self.supplier_ids = [s["id"] for s in suppliers]
        self.supplier_var = ctk.StringVar(value=self.supplier_names[0] if self.supplier_names else "")
        ctk.CTkOptionMenu(top, values=self.supplier_names or ["—"],
                          variable=self.supplier_var, width=180).grid(
            row=0, column=2, padx=6, sticky="ew")

        ctk.CTkLabel(top, text="الدواء:", anchor="e").grid(row=0, column=1, sticky="e", padx=6)
        meds = get_all_medicines()
        self.med_names = [m["name"] for m in meds]
        self.med_ids = [m["id"] for m in meds]
        self.med_prices = [m.get("purchase_price", 0) for m in meds]
        self.med_var = ctk.StringVar(value=self.med_names[0] if self.med_names else "")
        ctk.CTkOptionMenu(top, values=self.med_names or ["—"],
                          variable=self.med_var, width=200).grid(
            row=0, column=0, padx=6, sticky="ew")

        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.grid(row=1, column=0, sticky="ew", padx=16, pady=4)
        row2.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        ctk.CTkLabel(row2, text="الكمية:", anchor="e").grid(row=0, column=4, sticky="e", padx=4)
        self.qty_var = ctk.StringVar(value="1")
        ctk.CTkEntry(row2, textvariable=self.qty_var, width=80, height=34, justify="center").grid(
            row=0, column=3, padx=4)

        ctk.CTkLabel(row2, text="سعر الشراء:", anchor="e").grid(row=0, column=2, sticky="e", padx=4)
        self.price_var = ctk.StringVar(value="0")
        ctk.CTkEntry(row2, textvariable=self.price_var, width=90, height=34, justify="center").grid(
            row=0, column=1, padx=4)

        ctk.CTkLabel(row2, text="الصلاحية:", anchor="e").grid(row=1, column=4, sticky="e", padx=4, pady=4)
        self.expiry_var = ctk.StringVar()
        ctk.CTkEntry(row2, textvariable=self.expiry_var,
                     placeholder_text="YYYY-MM-DD", width=130, height=34).grid(
            row=1, column=3, padx=4)

        ctk.CTkButton(row2, text="➕ إضافة للقائمة", width=150,
                      command=self._add_item).grid(row=0, column=0, padx=4)

        table_frame = ctk.CTkFrame(self, corner_radius=8)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=4)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("med", "qty", "price", "expiry", "total")
        labels = {"med": "الدواء", "qty": "الكمية", "price": "سعر الوحدة",
                  "expiry": "الصلاحية", "total": "الإجمالي"}
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=8)
        ctk.configure_treeview(self.tree)
        for col in cols:
            self.tree.heading(col, text=labels[col])
            self.tree.column(col, width=130, anchor="center")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.grid(row=3, column=0, sticky="ew", padx=16, pady=8)
        bot.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.total_label = ctk.CTkLabel(bot, text="الإجمالي: 0.00",
                                         font=ctk.CTkFont(size=14, weight="bold"))
        self.total_label.grid(row=0, column=3, padx=8, sticky="e")

        ctk.CTkLabel(bot, text="خصم:", anchor="e").grid(row=0, column=2, sticky="e")
        self.disc_var = ctk.StringVar(value="0")
        ctk.CTkEntry(bot, textvariable=self.disc_var, width=80, height=32, justify="center").grid(
            row=0, column=1, padx=4)

        ctk.CTkLabel(bot, text="دفع:", anchor="e").grid(row=0, column=0, sticky="e")
        self.paid_var = ctk.StringVar(value="0")
        ctk.CTkEntry(bot, textvariable=self.paid_var, width=90, height=32, justify="center").grid(
            row=0, column=0, padx=4, sticky="w")

        ctk.CTkLabel(bot, text="طريقة الدفع:").grid(row=1, column=2, sticky="e", pady=6)
        self.payment_var = ctk.StringVar(value="كاش")
        ctk.CTkOptionMenu(bot, values=["كاش", "آجل", "بطاقة"],
                          variable=self.payment_var, width=100).grid(row=1, column=1, padx=4)

        ctk.CTkLabel(bot, text="ملاحظات:").grid(row=1, column=0, sticky="e")
        self.notes_var = ctk.StringVar()
        ctk.CTkEntry(bot, textvariable=self.notes_var, width=200, height=32).grid(
            row=1, column=0, padx=4, sticky="w")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=4, column=0, pady=8)
        ctk.CTkButton(actions, text="🗑 حذف محدد", fg_color="#dc2626",
                      command=self._remove_item).pack(side="left", padx=8)
        ctk.CTkButton(actions, text="💾 حفظ الفاتورة", width=140,
                      command=self._save).pack(side="left", padx=8)
        ctk.CTkButton(actions, text="إلغاء", fg_color="gray",
                      command=self.destroy).pack(side="left", padx=8)

    def _add_item(self):
        med_name = self.med_var.get()
        if med_name not in self.med_names:
            return
        idx = self.med_names.index(med_name)
        try:
            qty = int(float(self.qty_var.get() or 1))
            price = float(self.price_var.get() or self.med_prices[idx])
        except ValueError:
            messagebox.showerror("خطأ", "قيمة غير صحيحة", parent=self)
            return
        if qty <= 0:
            return
        total = qty * price
        expiry = self.expiry_var.get().strip()
        self.cart_items.append({
            "medicine_id": self.med_ids[idx],
            "medicine_name": med_name,
            "quantity": qty,
            "unit_price": price,
            "total": total,
            "expiry_date": expiry,
        })
        _row_tag = "evenrow" if len(self.cart_items) % 2 == 0 else "oddrow"
        self.tree.insert("", "end", tags=(_row_tag,), values=(med_name, qty, f"{price:.2f}", expiry, f"{total:.2f}"))
        self._update_total()

    def _remove_item(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        self.cart_items.pop(idx)
        self.tree.delete(sel[0])
        self._update_total()

    def _update_total(self):
        total = sum(i["total"] for i in self.cart_items)
        cur = get_setting("currency", "ج.م")
        self.total_label.configure(text=f"الإجمالي: {total:.2f} {cur}")

    def _save(self):
        if not self.cart_items:
            messagebox.showwarning("تحذير", "القائمة فارغة", parent=self)
            return
        sup_name = self.supplier_var.get()
        if sup_name not in self.supplier_names:
            messagebox.showerror("خطأ", "يرجى اختيار مورد", parent=self)
            return
        sup_id = self.supplier_ids[self.supplier_names.index(sup_name)]
        subtotal = sum(i["total"] for i in self.cart_items)
        try:
            discount = float(self.disc_var.get() or 0)
            paid = float(self.paid_var.get() or 0)
        except ValueError:
            discount = paid = 0
        total = subtotal - discount
        user = get_current_user()
        payment_map = {"كاش": "cash", "آجل": "credit", "بطاقة": "card"}
        data = {
            "supplier_id": sup_id,
            "user_id": user["id"],
            "subtotal": subtotal,
            "discount": discount,
            "tax": 0,
            "total": total,
            "paid_amount": paid,
            "payment_method": payment_map.get(self.payment_var.get(), "cash"),
            "notes": self.notes_var.get().strip(),
        }
        try:
            create_purchase(data, self.cart_items)
            messagebox.showinfo("تم", "تم حفظ فاتورة الشراء بنجاح", parent=self)
            self.on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror("خطأ", str(e), parent=self)


class PurchaseDetailDialog(ctk.CTkToplevel):
    def __init__(self, parent, purchase, items):
        super().__init__(parent)
        self.title(f"تفاصيل فاتورة الشراء: {purchase.get('invoice_number','')}")
        self.geometry("620x480")
        self.grab_set()
        self._build(purchase, items)

    def _build(self, purchase, items):
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(fill="x", padx=20, pady=12)
        info.grid_columnconfigure((0, 1, 2, 3), weight=1)
        fields = [
            ("رقم الفاتورة", purchase.get("invoice_number", "")),
            ("المورد", purchase.get("supplier_name", "")),
            ("التاريخ", purchase.get("purchase_date", "")[:16]),
            ("المسؤول", purchase.get("user_name", "")),
            ("الإجمالي", f"{purchase.get('total', 0):.2f}"),
            ("المدفوع", f"{purchase.get('paid_amount', 0):.2f}"),
        ]
        for i, (label, val) in enumerate(fields):
            r, c = divmod(i, 4)
            sub = ctk.CTkFrame(info, fg_color="transparent")
            sub.grid(row=r, column=c, padx=8, pady=4, sticky="w")
            ctk.CTkLabel(sub, text=label + ":", text_color="gray").pack(anchor="w")
            ctk.CTkLabel(sub, text=str(val), font=ctk.CTkFont(weight="bold")).pack(anchor="w")

        cols = ("med", "qty", "price", "expiry", "total")
        labels = {"med": "الدواء", "qty": "الكمية", "price": "السعر",
                  "expiry": "الصلاحية", "total": "الإجمالي"}
        tree = ttk.Treeview(self, columns=cols, show="headings", height=10)
        for _i_col, col in enumerate(cols):
            _row_tag = "evenrow" if _i_col % 2 == 0 else "oddrow"
            tree.heading(col, text=labels[col])
            tree.column(col, width=110, anchor="center")
        for _i_item, item in enumerate(items):
            _row_tag = "evenrow" if _i_item % 2 == 0 else "oddrow"
            tree.insert("", "end", tags=(_row_tag,), values=(
                item.get("medicine_name", ""), item.get("quantity", 0),
                f"{item.get('unit_price', 0):.2f}", item.get("expiry_date", "") or "",
                f"{item.get('total', 0):.2f}",
            ))
        tree.pack(fill="both", expand=True, padx=20, pady=8)
        ctk.CTkButton(self, text="إغلاق", command=self.destroy).pack(pady=8)
