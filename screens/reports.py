import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog
from database.connection import get_connection
from utils.helpers import get_setting, format_currency
from datetime import datetime, timedelta


class ReportsScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        tabs = ctk.CTkTabview(self)
        tabs.grid(row=0, column=0, sticky="nsew", padx=20, pady=16)

        self._build_sales_report(tabs.add("تقرير المبيعات"))
        self._build_inventory_report(tabs.add("تقرير المخزون"))
        self._build_financial_report(tabs.add("التقرير المالي"))
        self._build_medicine_report(tabs.add("أكثر الأدوية مبيعاً"))
        self._build_customer_report(tabs.add("تقرير العملاء"))

    def _date_filter(self, parent, row=0):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=0, sticky="ew", pady=8)
        ctk.CTkLabel(f, text="من:").pack(side="right", padx=4)
        from_var = ctk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        ctk.CTkEntry(f, textvariable=from_var, width=130, height=34).pack(side="right", padx=2)
        ctk.CTkLabel(f, text="إلى:").pack(side="right", padx=4)
        to_var = ctk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ctk.CTkEntry(f, textvariable=to_var, width=130, height=34).pack(side="right", padx=2)
        return f, from_var, to_var

    def _build_sales_report(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        f, self.sales_from, self.sales_to = self._date_filter(parent, row=0)
        ctk.CTkButton(f, text="تحديث التقرير", command=self._load_sales_report).pack(side="right", padx=8)
        ctk.CTkButton(f, text="📥 تصدير Excel", fg_color="#059669",
                      command=self._export_sales_excel).pack(side="left", padx=8)

        summary = ctk.CTkFrame(parent, fg_color="transparent")
        summary.grid(row=1, column=0, sticky="ew", pady=4)
        for i in range(4):
            summary.grid_columnconfigure(i, weight=1)
        self.sales_sum_labels = {}
        for i, (key, label) in enumerate([("count", "عدد الفواتير"), ("revenue", "الإيرادات"),
                                           ("discount", "إجمالي الخصومات"), ("avg", "متوسط الفاتورة")]):
            sub = ctk.CTkFrame(summary, corner_radius=8, height=70)
            sub.grid(row=0, column=i, padx=6, sticky="ew")
            sub.grid_propagate(False)
            ctk.CTkLabel(sub, text=label, font=ctk.CTkFont(size=11), text_color="gray").pack(pady=(10, 2))
            lbl = ctk.CTkLabel(sub, text="—", font=ctk.CTkFont(size=14, weight="bold"))
            lbl.pack()
            self.sales_sum_labels[key] = lbl

        table_frame = ctk.CTkFrame(parent, corner_radius=8)
        table_frame.grid(row=2, column=0, sticky="nsew", pady=4)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("date", "count", "revenue", "discount", "net")
        labels = {"date": "التاريخ", "count": "عدد الفواتير", "revenue": "الإيرادات",
                  "discount": "الخصومات", "net": "الصافي"}
        self.sales_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        ctk.configure_treeview(self.sales_tree)
        for col in cols:
            self.sales_tree.heading(col, text=labels[col])
            self.sales_tree.column(col, width=140, anchor="center")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.sales_tree.yview)
        self.sales_tree.configure(yscrollcommand=vsb.set)
        self.sales_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._load_sales_report()

    def _load_sales_report(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT date(sale_date) as day,
                   COUNT(*) as cnt,
                   SUM(subtotal) as revenue,
                   SUM(discount) as discount,
                   SUM(total) as net
            FROM sales
            WHERE status='completed'
              AND date(sale_date) >= ? AND date(sale_date) <= ?
            GROUP BY day ORDER BY day DESC
        """, (self.sales_from.get(), self.sales_to.get()))
        rows = c.fetchall()
        conn.close()

        cur = get_setting("currency", "ج.م")
        self.sales_tree.delete(*self.sales_tree.get_children())
        total_cnt = total_rev = total_disc = 0
        for _i_row, row in enumerate(rows):
            _row_tag = "evenrow" if _i_row % 2 == 0 else "oddrow"
            self.sales_tree.insert("", "end", tags=(_row_tag,), values=(
                row[0], row[1],
                f"{row[2] or 0:.2f} {cur}",
                f"{row[3] or 0:.2f} {cur}",
                f"{row[4] or 0:.2f} {cur}",
            ))
            total_cnt += row[1]
            total_rev += row[2] or 0
            total_disc += row[3] or 0

        self.sales_sum_labels["count"].configure(text=str(total_cnt))
        self.sales_sum_labels["revenue"].configure(text=f"{total_rev:.2f} {cur}")
        self.sales_sum_labels["discount"].configure(text=f"{total_disc:.2f} {cur}")
        avg = total_rev / total_cnt if total_cnt > 0 else 0
        self.sales_sum_labels["avg"].configure(text=f"{avg:.2f} {cur}")

    def _export_sales_excel(self):
        try:
            import openpyxl
            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx")],
                initialfile="sales_report.xlsx",
                parent=self)
            if not path:
                return
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
                SELECT s.invoice_number, c.name, s.subtotal, s.discount, s.tax, s.total,
                       s.payment_method, s.sale_date, u.full_name
                FROM sales s
                JOIN users u ON s.user_id = u.id
                LEFT JOIN customers c ON s.customer_id = c.id
                WHERE s.status='completed'
                  AND date(s.sale_date) >= ? AND date(s.sale_date) <= ?
                ORDER BY s.sale_date DESC
            """, (self.sales_from.get(), self.sales_to.get()))
            rows = c.fetchall()
            conn.close()
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "تقرير المبيعات"
            headers = ["رقم الفاتورة", "العميل", "المجموع الفرعي", "الخصم", "الضريبة",
                       "الإجمالي", "طريقة الدفع", "التاريخ", "الكاشير"]
            ws.append(headers)
            for row in rows:
                ws.append(list(row))
            wb.save(path)
            messagebox.showinfo("تم", f"تم التصدير إلى:\n{path}", parent=self)
        except ImportError:
            messagebox.showerror("خطأ", "يرجى تثبيت openpyxl: pip install openpyxl", parent=self)
        except Exception as e:
            messagebox.showerror("خطأ", str(e), parent=self)

    def _build_inventory_report(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", pady=8)
        ctk.CTkButton(ctrl, text="🔄 تحديث", command=self._load_inventory_report).pack(side="right", padx=8)
        ctk.CTkButton(ctrl, text="📥 تصدير", fg_color="#059669",
                      command=self._export_inventory).pack(side="left", padx=8)
        ctk.CTkLabel(ctrl, text="تصفية:",).pack(side="right", padx=4)
        self.inv_filter_var = ctk.StringVar(value="الكل")
        ctk.CTkOptionMenu(ctrl, values=["الكل", "مخزون منخفض", "نفذ المخزون", "قارب الانتهاء"],
                          variable=self.inv_filter_var,
                          command=lambda v: self._load_inventory_report()).pack(side="right", padx=4)

        table_frame = ctk.CTkFrame(parent, corner_radius=8)
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "name", "category", "qty", "min_qty", "sell_price", "buy_price",
                "stock_value", "expiry")
        labels = {"id": "#", "name": "الدواء", "category": "الفئة", "qty": "الكمية",
                  "min_qty": "الحد الأدنى", "sell_price": "سعر البيع",
                  "buy_price": "سعر الشراء", "stock_value": "قيمة المخزون", "expiry": "الصلاحية"}
        self.inv_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        ctk.configure_treeview(self.inv_tree)
        for col in cols:
            self.inv_tree.heading(col, text=labels[col])
            self.inv_tree.column(col, width=100, anchor="center")
        self.inv_tree.column("name", width=180)
        # ألوان low/out تُضبط في configure_treeview
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.inv_tree.yview)
        self.inv_tree.configure(yscrollcommand=vsb.set)
        self.inv_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.inv_status = ctk.CTkLabel(parent, text="", text_color="gray")
        self.inv_status.grid(row=2, column=0, sticky="e", pady=4)
        self._load_inventory_report()

    def _load_inventory_report(self):
        conn = get_connection()
        c = conn.cursor()
        query = """
            SELECT m.id, m.name, cat.name as category, m.quantity, m.min_quantity,
                   m.selling_price, m.purchase_price,
                   m.quantity * m.purchase_price as stock_value, m.expiry_date
            FROM medicines m
            LEFT JOIN categories cat ON m.category_id = cat.id
            WHERE m.is_active=1
        """
        filt = self.inv_filter_var.get()
        if filt == "مخزون منخفض":
            query += " AND m.quantity <= m.min_quantity AND m.quantity > 0"
        elif filt == "نفذ المخزون":
            query += " AND m.quantity = 0"
        elif filt == "قارب الانتهاء":
            query += " AND m.expiry_date IS NOT NULL AND date(m.expiry_date) <= date('now', '+30 days')"
        query += " ORDER BY m.name"
        c.execute(query)
        rows = c.fetchall()
        conn.close()
        cur = get_setting("currency", "ج.م")
        self.inv_tree.delete(*self.inv_tree.get_children())
        total_val = 0
        for _i_row, row in enumerate(rows):
            _row_tag = "evenrow" if _i_row % 2 == 0 else "oddrow"
            qty = row[3] or 0
            min_qty = row[4] or 5
            tag = "out" if qty == 0 else ("low" if qty <= min_qty else "")
            self.inv_tree.insert("", "end", tags=(tag,), values=(
                row[0], row[1], row[2] or "", qty, min_qty,
                f"{row[5] or 0:.2f}", f"{row[6] or 0:.2f}",
                f"{row[7] or 0:.2f} {cur}", row[8] or "",
            ))
            total_val += row[7] or 0
        self.inv_status.configure(text=f"إجمالي الأصناف: {len(rows)} | قيمة المخزون الكلية: {total_val:.2f} {cur}")

    def _export_inventory(self):
        try:
            import openpyxl
            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")],
                initialfile="inventory_report.xlsx", parent=self)
            if not path:
                return
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
                SELECT m.name, cat.name, m.quantity, m.min_quantity,
                       m.selling_price, m.purchase_price,
                       m.quantity * m.purchase_price as stock_value, m.expiry_date
                FROM medicines m
                LEFT JOIN categories cat ON m.category_id = cat.id
                WHERE m.is_active=1 ORDER BY m.name
            """)
            rows = c.fetchall()
            conn.close()
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "المخزون"
            ws.append(["الدواء", "الفئة", "الكمية", "الحد الأدنى",
                       "سعر البيع", "سعر الشراء", "قيمة المخزون", "الصلاحية"])
            for row in rows:
                ws.append(list(row))
            wb.save(path)
            messagebox.showinfo("تم", f"تم التصدير إلى:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("خطأ", str(e), parent=self)

    def _build_financial_report(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        f, self.fin_from, self.fin_to = self._date_filter(parent, row=0)
        ctk.CTkButton(f, text="تحديث", command=self._load_financial).pack(side="right", padx=8)

        self.fin_frame = ctk.CTkFrame(parent, corner_radius=10)
        self.fin_frame.grid(row=1, column=0, sticky="nsew", pady=8)
        self._load_financial()

    def _load_financial(self):
        conn = get_connection()
        c = conn.cursor()
        df = self.fin_from.get()
        dt = self.fin_to.get()
        c.execute("SELECT SUM(total) FROM sales WHERE status='completed' AND date(sale_date)>=? AND date(sale_date)<=?", (df, dt))
        sales_rev = c.fetchone()[0] or 0
        c.execute("SELECT SUM(total) FROM purchases WHERE date(purchase_date)>=? AND date(purchase_date)<=?", (df, dt))
        purchase_cost = c.fetchone()[0] or 0
        c.execute("SELECT SUM(amount) FROM expenses WHERE date(expense_date)>=? AND date(expense_date)<=?", (df, dt))
        expenses = c.fetchone()[0] or 0
        c.execute("SELECT SUM(total_return_amount) FROM sales_returns WHERE date(return_date)>=? AND date(return_date)<=?", (df, dt))
        returns = c.fetchone()[0] or 0
        conn.close()

        profit = sales_rev - purchase_cost - expenses - returns
        cur = get_setting("currency", "ج.م")

        for w in self.fin_frame.winfo_children():
            w.destroy()

        items = [
            ("💰 إجمالي المبيعات", sales_rev, "#2563eb"),
            ("📦 تكلفة المشتريات", purchase_cost, "#dc2626"),
            ("💸 المصروفات", expenses, "#d97706"),
            ("↩ المرتجعات", returns, "#7c3aed"),
            ("📊 صافي الربح", profit, "#059669" if profit >= 0 else "#dc2626"),
        ]

        self.fin_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        for i, (label, val, color) in enumerate(items):
            card = ctk.CTkFrame(self.fin_frame, corner_radius=10, height=100)
            card.grid(row=0, column=i, padx=8, pady=20, sticky="ew")
            card.grid_propagate(False)
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=11),
                         text_color="gray", wraplength=130).grid(row=0, column=0, pady=(12, 2))
            ctk.CTkLabel(card, text=f"{val:.2f} {cur}",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=color, wraplength=160).grid(row=1, column=0, pady=(0, 8))

    def _build_medicine_report(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        f, self.med_from, self.med_to = self._date_filter(parent, row=0)
        ctk.CTkButton(f, text="تحديث", command=self._load_medicine_report).pack(side="right", padx=8)

        table_frame = ctk.CTkFrame(parent, corner_radius=8)
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("rank", "name", "total_qty", "total_revenue", "transactions")
        labels = {"rank": "#", "name": "الدواء", "total_qty": "الكمية المباعة",
                  "total_revenue": "الإيرادات", "transactions": "عدد المعاملات"}
        self.med_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        ctk.configure_treeview(self.med_tree)
        for col in cols:
            self.med_tree.heading(col, text=labels[col])
            self.med_tree.column(col, width=140, anchor="center")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.med_tree.yview)
        self.med_tree.configure(yscrollcommand=vsb.set)
        self.med_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._load_medicine_report()

    def _load_medicine_report(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT m.name,
                   SUM(si.quantity) as total_qty,
                   SUM(si.total) as total_revenue,
                   COUNT(DISTINCT si.sale_id) as transactions
            FROM sale_items si
            JOIN medicines m ON si.medicine_id = m.id
            JOIN sales s ON si.sale_id = s.id
            WHERE s.status='completed'
              AND date(s.sale_date) >= ? AND date(s.sale_date) <= ?
            GROUP BY m.id
            ORDER BY total_qty DESC
            LIMIT 50
        """, (self.med_from.get(), self.med_to.get()))
        rows = c.fetchall()
        conn.close()
        cur = get_setting("currency", "ج.م")
        self.med_tree.delete(*self.med_tree.get_children())
        for i, row in enumerate(rows, 1):
            _row_tag = "evenrow" if i % 2 == 0 else "oddrow"
            self.med_tree.insert("", "end", tags=(_row_tag,), values=(
                i, row[0], row[1] or 0,
                f"{row[2] or 0:.2f} {cur}", row[3] or 0,
            ))

    def _build_customer_report(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        f, self.cust_from, self.cust_to = self._date_filter(parent, row=0)
        ctk.CTkButton(f, text="تحديث", command=self._load_customer_report).pack(side="right", padx=8)

        table_frame = ctk.CTkFrame(parent, corner_radius=8)
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("rank", "name", "phone", "purchases_count", "total_spent", "last_visit")
        labels = {"rank": "#", "name": "العميل", "phone": "الهاتف",
                  "purchases_count": "عدد المشتريات", "total_spent": "إجمالي الإنفاق",
                  "last_visit": "آخر زيارة"}
        self.cust_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        ctk.configure_treeview(self.cust_tree)
        for col in cols:
            self.cust_tree.heading(col, text=labels[col])
            self.cust_tree.column(col, width=130, anchor="center")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.cust_tree.yview)
        self.cust_tree.configure(yscrollcommand=vsb.set)
        self.cust_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._load_customer_report()

    def _load_customer_report(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT c.name, c.phone,
                   COUNT(s.id) as purchases_count,
                   SUM(s.total) as total_spent,
                   MAX(s.sale_date) as last_visit
            FROM customers c
            JOIN sales s ON s.customer_id = c.id
            WHERE s.status='completed'
              AND date(s.sale_date) >= ? AND date(s.sale_date) <= ?
            GROUP BY c.id
            ORDER BY total_spent DESC LIMIT 50
        """, (self.cust_from.get(), self.cust_to.get()))
        rows = c.fetchall()
        conn.close()
        cur = get_setting("currency", "ج.م")
        self.cust_tree.delete(*self.cust_tree.get_children())
        for i, row in enumerate(rows, 1):
            _row_tag = "evenrow" if i % 2 == 0 else "oddrow"
            self.cust_tree.insert("", "end", tags=(_row_tag,), values=(
                i, row[0], row[1] or "",
                row[2] or 0, f"{row[3] or 0:.2f} {cur}",
                (row[4] or "")[:16],
            ))
