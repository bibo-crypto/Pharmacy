import customtkinter as ctk
from tkinter import messagebox, ttk
from models.medicine import get_all_medicines, get_medicine_by_id, get_expiring_medicines
from database.connection import get_connection
from utils.auth import get_current_user
from utils.helpers import get_setting
from datetime import datetime


class InventoryScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        tabs = ctk.CTkTabview(self)
        tabs.grid(row=0, column=0, sticky="nsew", padx=20, pady=16)
        self.grid_rowconfigure(0, weight=1)

        tab_stock = tabs.add("المخزون الحالي")
        tab_low = tabs.add("مخزون منخفض")
        tab_expiry = tabs.add("قاربت على الانتهاء")
        tab_adjust = tabs.add("تعديل المخزون")
        tab_history = tabs.add("سجل التعديلات")

        self._build_stock_tab(tab_stock)
        self._build_low_tab(tab_low)
        self._build_expiry_tab(tab_expiry)
        self._build_adjust_tab(tab_adjust)
        self._build_history_tab(tab_history)

    def _build_stock_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        filter_frame = ctk.CTkFrame(parent, fg_color="transparent")
        filter_frame.grid(row=0, column=0, sticky="ew", pady=8)
        self.stock_search = ctk.StringVar()
        self.stock_search.trace("w", lambda *a: self._load_stock())
        ctk.CTkEntry(filter_frame, textvariable=self.stock_search,
                     placeholder_text="🔍 بحث...", width=260, height=36).pack(side="right", padx=4)
        ctk.CTkButton(filter_frame, text="🔄 تحديث", fg_color="gray",
                      command=self._load_stock).pack(side="left", padx=4)

        table_frame = ctk.CTkFrame(parent, corner_radius=8)
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "barcode", "name", "category", "unit", "qty", "min_qty", "price", "expiry")
        labels = {"id": "#", "barcode": "باركود", "name": "الدواء", "category": "الفئة",
                  "unit": "الوحدة", "qty": "الكمية", "min_qty": "الحد الأدنى",
                  "price": "سعر البيع", "expiry": "الصلاحية"}

        self.stock_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        ctk.configure_treeview(self.stock_tree)
        for col in cols:
            self.stock_tree.heading(col, text=labels[col], anchor="center")
            self.stock_tree.column(col, width=90, anchor="center")
        self.stock_tree.column("name", width=180)
        # ألوان low/out تُضبط في configure_treeview
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=vsb.set)
        self.stock_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.stock_status = ctk.CTkLabel(parent, text="", text_color="gray")
        self.stock_status.grid(row=2, column=0, sticky="e", pady=4)
        self._load_stock()

    def _load_stock(self):
        meds = get_all_medicines(search=self.stock_search.get().strip() or None)
        self.stock_tree.delete(*self.stock_tree.get_children())
        for _i_m, m in enumerate(meds):
            _row_tag = "evenrow" if _i_m % 2 == 0 else "oddrow"
            qty = m.get("quantity", 0)
            min_qty = m.get("min_quantity", 5)
            tag = "out" if qty == 0 else ("low" if qty <= min_qty else "")
            self.stock_tree.insert("", "end", tags=(tag,), values=(
                m["id"], m.get("barcode", ""), m["name"],
                m.get("category_name", ""), m.get("unit", ""),
                qty, min_qty, f"{m.get('selling_price', 0):.2f}",
                m.get("expiry_date", "") or "",
            ))
        total_val = sum(m.get("quantity", 0) * m.get("selling_price", 0) for m in meds)
        cur = get_setting("currency", "ج.م")
        self.stock_status.configure(text=f"إجمالي الأصناف: {len(meds)} | قيمة المخزون: {total_val:.2f} {cur}")

    def _build_low_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        table_frame = ctk.CTkFrame(parent, corner_radius=8)
        table_frame.grid(row=0, column=0, sticky="nsew", pady=8)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        cols = ("id", "name", "quantity", "min_quantity", "supplier")
        labels = {"id": "#", "name": "الدواء", "quantity": "الكمية الحالية",
                  "min_quantity": "الحد الأدنى", "supplier": "المورد"}
        self.low_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        ctk.configure_treeview(self.low_tree)
        for col in cols:
            self.low_tree.heading(col, text=labels[col])
            self.low_tree.column(col, width=140, anchor="center")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.low_tree.yview)
        self.low_tree.configure(yscrollcommand=vsb.set)
        self.low_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        ctk.CTkButton(parent, text="🔄 تحديث", fg_color="gray",
                      command=self._load_low).grid(row=1, column=0, pady=6)
        self._load_low()

    def _load_low(self):
        meds = get_all_medicines(low_stock=True)
        self.low_tree.delete(*self.low_tree.get_children())
        for _i_m, m in enumerate(meds):
            _row_tag = "evenrow" if _i_m % 2 == 0 else "oddrow"
            self.low_tree.insert("", "end", tags=(_row_tag,), values=(
                m["id"], m["name"], m.get("quantity", 0),
                m.get("min_quantity", 5), m.get("supplier_name", ""),
            ))

    def _build_expiry_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        filter_frame = ctk.CTkFrame(parent, fg_color="transparent")
        filter_frame.grid(row=0, column=0, sticky="ew", pady=6)
        ctk.CTkLabel(filter_frame, text="عرض الأدوية التي تنتهي خلال:").pack(side="right", padx=4)
        self.days_var = ctk.StringVar(value="30")
        ctk.CTkEntry(filter_frame, textvariable=self.days_var, width=60, height=32).pack(side="right", padx=4)
        ctk.CTkLabel(filter_frame, text="يوم").pack(side="right")
        ctk.CTkButton(filter_frame, text="بحث", width=80,
                      command=self._load_expiry).pack(side="right", padx=8)

        table_frame = ctk.CTkFrame(parent, corner_radius=8)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=4)
        parent.grid_rowconfigure(1, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        cols = ("id", "name", "quantity", "expiry_date", "location")
        labels = {"id": "#", "name": "الدواء", "quantity": "الكمية",
                  "expiry_date": "تاريخ الانتهاء", "location": "الموقع"}
        self.expiry_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        ctk.configure_treeview(self.expiry_tree)
        for col in cols:
            self.expiry_tree.heading(col, text=labels[col])
            self.expiry_tree.column(col, width=140, anchor="center")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.expiry_tree.yview)
        self.expiry_tree.configure(yscrollcommand=vsb.set)
        self.expiry_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._load_expiry()

    def _load_expiry(self):
        try:
            days = int(self.days_var.get() or 30)
        except ValueError:
            days = 30
        meds = get_expiring_medicines(days)
        self.expiry_tree.delete(*self.expiry_tree.get_children())
        for _i_m, m in enumerate(meds):
            _row_tag = "evenrow" if _i_m % 2 == 0 else "oddrow"
            self.expiry_tree.insert("", "end", tags=(_row_tag,), values=(
                m["id"], m["name"], m.get("quantity", 0),
                m.get("expiry_date", ""), m.get("location", ""),
            ))

    def _build_adjust_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="ew", pady=16)
        frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(frame, text="تعديل المخزون",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, pady=10)

        meds = get_all_medicines()
        self.adj_med_names = [m["name"] for m in meds]
        self.adj_med_ids = [m["id"] for m in meds]

        ctk.CTkLabel(frame, text="الدواء:", anchor="e").grid(row=1, column=1, sticky="e", padx=8, pady=(8, 2))
        self.adj_med_var = ctk.StringVar(value=self.adj_med_names[0] if self.adj_med_names else "")
        ctk.CTkOptionMenu(frame, values=self.adj_med_names or ["—"],
                          variable=self.adj_med_var, width=220).grid(
            row=2, column=1, padx=8, sticky="ew")

        ctk.CTkLabel(frame, text="نوع التعديل:", anchor="e").grid(row=1, column=0, sticky="e", padx=8)
        self.adj_type_var = ctk.StringVar(value="إضافة")
        ctk.CTkOptionMenu(frame, values=["إضافة", "خصم", "تصحيح"],
                          variable=self.adj_type_var, width=150).grid(row=2, column=0, padx=8)

        ctk.CTkLabel(frame, text="الكمية:", anchor="e").grid(row=3, column=1, sticky="e", padx=8, pady=(8, 2))
        self.adj_qty_var = ctk.StringVar(value="0")
        ctk.CTkEntry(frame, textvariable=self.adj_qty_var, height=36,
                     justify="center", width=100).grid(row=4, column=1, padx=8, sticky="w")

        ctk.CTkLabel(frame, text="السبب:", anchor="e").grid(row=3, column=0, sticky="e", padx=8)
        self.adj_reason_var = ctk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.adj_reason_var, height=36, width=200).grid(
            row=4, column=0, padx=8, sticky="ew")

        ctk.CTkButton(frame, text="تطبيق التعديل", width=180, height=40,
                      command=self._apply_adjustment).grid(
            row=5, column=0, columnspan=2, pady=16)

        self.adj_status = ctk.CTkLabel(frame, text="", text_color="green")
        self.adj_status.grid(row=6, column=0, columnspan=2)

    def _apply_adjustment(self):
        med_name = self.adj_med_var.get()
        if med_name not in self.adj_med_names:
            messagebox.showwarning("تحذير", "يرجى اختيار دواء", parent=self)
            return
        idx = self.adj_med_names.index(med_name)
        med_id = self.adj_med_ids[idx]
        try:
            qty = int(float(self.adj_qty_var.get() or 0))
        except ValueError:
            messagebox.showerror("خطأ", "كمية غير صحيحة", parent=self)
            return
        med = get_medicine_by_id(med_id)
        adj_type = self.adj_type_var.get()
        if adj_type == "إضافة":
            new_qty = med["quantity"] + qty
        elif adj_type == "خصم":
            new_qty = max(0, med["quantity"] - qty)
        else:
            new_qty = qty
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE medicines SET quantity=? WHERE id=?", (new_qty, med_id))
        user = get_current_user()
        c.execute("""
            INSERT INTO inventory_adjustments
            (medicine_id, adjustment_type, quantity_before, quantity_after, reason, user_id)
            VALUES (?,?,?,?,?,?)
        """, (med_id, adj_type, med["quantity"], new_qty, self.adj_reason_var.get(), user["id"]))
        conn.commit()
        conn.close()
        self.adj_status.configure(text=f"✅ تم تعديل مخزون {med_name}: {med['quantity']} ← {new_qty}")
        self._load_stock()

    def _build_history_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        table_frame = ctk.CTkFrame(parent, corner_radius=8)
        table_frame.grid(row=0, column=0, sticky="nsew", pady=8)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        cols = ("id", "medicine", "type", "before", "after", "reason", "user", "date")
        labels = {"id": "#", "medicine": "الدواء", "type": "النوع",
                  "before": "قبل", "after": "بعد", "reason": "السبب",
                  "user": "المستخدم", "date": "التاريخ"}
        self.hist_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        ctk.configure_treeview(self.hist_tree)
        for col in cols:
            self.hist_tree.heading(col, text=labels[col])
            self.hist_tree.column(col, width=100, anchor="center")
        self.hist_tree.column("medicine", width=160)
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=vsb.set)
        self.hist_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        ctk.CTkButton(parent, text="🔄 تحديث", fg_color="gray",
                      command=self._load_history).grid(row=1, column=0, pady=6)
        self._load_history()

    def _load_history(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT ia.*, m.name as medicine_name, u.full_name as user_name
            FROM inventory_adjustments ia
            JOIN medicines m ON ia.medicine_id = m.id
            JOIN users u ON ia.user_id = u.id
            ORDER BY ia.adjustment_date DESC LIMIT 200
        """)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        self.hist_tree.delete(*self.hist_tree.get_children())
        for _i_r, r in enumerate(rows):
            _row_tag = "evenrow" if _i_r % 2 == 0 else "oddrow"
            self.hist_tree.insert("", "end", tags=(_row_tag,), values=(
                r["id"], r.get("medicine_name", ""), r.get("adjustment_type", ""),
                r.get("quantity_before", 0), r.get("quantity_after", 0),
                r.get("reason", ""), r.get("user_name", ""),
                r.get("adjustment_date", "")[:16],
            ))
