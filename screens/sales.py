import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
from models.sale import get_all_sales, get_sale_by_id, cancel_sale
from utils.auth import has_permission
from utils.helpers import get_setting
from utils.printing import generate_receipt_pdf
import os, subprocess, sys


class SalesScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        ctk.CTkLabel(toolbar, text="سجل المبيعات",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="right")
        btn_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_frame.pack(side="left")
        ctk.CTkButton(btn_frame, text="🖨 طباعة", width=100,
                      fg_color="#059669", command=self._print_selected).pack(side="left", padx=4)
        if has_permission("cancel_sales"):
            ctk.CTkButton(btn_frame, text="❌ إلغاء", width=100,
                          fg_color="#dc2626", command=self._cancel).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="👁 تفاصيل", width=100,
                      command=self._view_details).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="🔄 تحديث", width=100,
                      fg_color="gray", command=self._load).pack(side="left", padx=4)

        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))

        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *a: self._load())
        ctk.CTkEntry(filter_frame, textvariable=self.search_var,
                     placeholder_text="🔍 بحث برقم الفاتورة أو العميل...",
                     width=260, height=36).pack(side="right", padx=4)

        ctk.CTkLabel(filter_frame, text="من:", font=ctk.CTkFont(size=12)).pack(side="right", padx=4)
        self.date_from_var = ctk.StringVar()
        ctk.CTkEntry(filter_frame, textvariable=self.date_from_var,
                     placeholder_text="YYYY-MM-DD", width=120, height=36).pack(side="right", padx=2)

        ctk.CTkLabel(filter_frame, text="إلى:", font=ctk.CTkFont(size=12)).pack(side="right", padx=4)
        self.date_to_var = ctk.StringVar()
        ctk.CTkEntry(filter_frame, textvariable=self.date_to_var,
                     placeholder_text="YYYY-MM-DD", width=120, height=36).pack(side="right", padx=2)

        ctk.CTkButton(filter_frame, text="بحث", width=80,
                      command=self._load).pack(side="right", padx=4)

        table_frame = ctk.CTkFrame(self, corner_radius=10)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 8))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "invoice", "customer", "cashier", "items", "subtotal",
                "discount", "tax", "total", "payment", "date", "status")
        labels = {
            "id": "#", "invoice": "رقم الفاتورة", "customer": "العميل",
            "cashier": "الكاشير", "items": "الأصناف", "subtotal": "المجموع",
            "discount": "الخصم", "tax": "الضريبة", "total": "الإجمالي",
            "payment": "الدفع", "date": "التاريخ", "status": "الحالة"
        }
        widths = {"id": 40, "invoice": 140, "customer": 110, "cashier": 90,
                  "items": 60, "subtotal": 80, "discount": 65, "tax": 65,
                  "total": 90, "payment": 70, "date": 130, "status": 75}


        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        ctk.configure_treeview(self.tree)
        for col in cols:
            self.tree.heading(col, text=labels[col], anchor="center")
            self.tree.column(col, width=widths.get(col, 80), anchor="center")

        self.tree.tag_configure("cancelled", foreground="red")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Double-1>", lambda e: self._view_details())

        summary = ctk.CTkFrame(self, fg_color="transparent")
        summary.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.summary_label = ctk.CTkLabel(summary, text="", font=ctk.CTkFont(size=12),
                                           text_color="gray")
        self.summary_label.pack(side="right")

        self._load()

    def _load(self):
        from database.connection import get_connection
        sales = get_all_sales(
            search=self.search_var.get().strip() or None,
            date_from=self.date_from_var.get().strip() or None,
            date_to=self.date_to_var.get().strip() or None,
        )
        self.tree.delete(*self.tree.get_children())
        total_rev = 0
        for _i_s, s in enumerate(sales):
            _row_tag = "evenrow" if _i_s % 2 == 0 else "oddrow"
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM sale_items WHERE sale_id=?", (s["id"],))
            item_count = c.fetchone()[0]
            conn.close()
            tag = "cancelled" if s.get("status") == "cancelled" else ""
            status_label = "ملغي" if s.get("status") == "cancelled" else "معلق" if s.get("status") == "pending" else "مكتمل"
            self.tree.insert("", "end", iid=str(s["id"]), tags=(tag,), values=(
                s["id"], s.get("invoice_number", ""),
                (s.get("customer_name") or "نقدي")[:14],
                s.get("cashier_name", "")[:12],
                item_count,
                f"{s.get('subtotal', 0):.2f}",
                f"{s.get('discount', 0):.2f}",
                f"{s.get('tax', 0):.2f}",
                f"{s.get('total', 0):.2f}",
                s.get("payment_method", ""),
                s.get("sale_date", "")[:16],
                status_label,
            ))
            if s.get("status") != "cancelled":
                total_rev += s.get("total", 0)

        cur = get_setting("currency", "ج.م")
        self.summary_label.configure(
            text=f"إجمالي الفواتير: {len(sales)} | إجمالي الإيرادات: {total_rev:.2f} {cur}"
        )

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("تحذير", "يرجى اختيار فاتورة أولاً")
            return None
        return int(sel[0])

    def _view_details(self):
        sid = self._get_selected_id()
        if not sid:
            return
        sale, items = get_sale_by_id(sid)
        if not sale:
            return
        SaleDetailDialog(self, sale, items)

    def _cancel(self):
        sid = self._get_selected_id()
        if not sid:
            return
        sale, _ = get_sale_by_id(sid)
        if sale and sale.get("status") == "cancelled":
            messagebox.showwarning("تحذير", "هذه الفاتورة ملغاة بالفعل")
            return
        if messagebox.askyesno("تأكيد", f"إلغاء الفاتورة {sale.get('invoice_number','')}؟"):
            cancel_sale(sid)
            self._load()
            messagebox.showinfo("تم", "تم إلغاء الفاتورة")

    def _print_selected(self):
        sid = self._get_selected_id()
        if not sid:
            return
        sale, items = get_sale_by_id(sid)
        if not sale:
            return
        try:
            path = generate_receipt_pdf(sale, items)
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("خطأ", f"خطأ في الطباعة: {e}")


class SaleDetailDialog(ctk.CTkToplevel):
    def __init__(self, parent, sale, items):
        super().__init__(parent)
        self.sale = sale
        self.items = items
        self.title(f"تفاصيل الفاتورة: {sale.get('invoice_number', '')}")
        self.geometry("700x520")
        self.grab_set()
        self._build()

    def _build(self):
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(fill="x", padx=20, pady=(16, 8))
        info.grid_columnconfigure((0, 1, 2, 3), weight=1)

        fields = [
            ("رقم الفاتورة", self.sale.get("invoice_number", "")),
            ("التاريخ", self.sale.get("sale_date", "")[:16]),
            ("الكاشير", self.sale.get("cashier_name", "")),
            ("العميل", self.sale.get("customer_name") or "نقدي"),
            ("طريقة الدفع", self.sale.get("payment_method", "")),
            ("الحالة", "ملغي" if self.sale.get("status") == "cancelled" else "معلق" if self.sale.get("status") == "pending" else "مكتمل"),
        ]
        for i, (label, value) in enumerate(fields):
            r, c = divmod(i, 4)
            sub = ctk.CTkFrame(info, fg_color="transparent")
            sub.grid(row=r, column=c, padx=8, pady=4, sticky="w")
            ctk.CTkLabel(sub, text=label + ":", font=ctk.CTkFont(size=11),
                         text_color="gray").pack(anchor="w")
            ctk.CTkLabel(sub, text=str(value), font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")

        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=20, pady=8)

        cols = ("name", "qty", "price", "discount", "total")
        labels = {"name": "الدواء", "qty": "الكمية", "price": "السعر",
                  "discount": "الخصم", "total": "الإجمالي"}
        tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10)
        for _i_col, col in enumerate(cols):
            _row_tag = "evenrow" if _i_col % 2 == 0 else "oddrow"
            tree.heading(col, text=labels[col])
            tree.column(col, width=120, anchor="center")
        for _i_item, item in enumerate(self.items):
            _row_tag = "evenrow" if _i_item % 2 == 0 else "oddrow"
            tree.insert("", "end", tags=(_row_tag,), values=(
                item.get("medicine_name", ""),
                item.get("quantity", 0),
                f"{item.get('unit_price', 0):.2f}",
                f"{item.get('discount', 0):.2f}",
                f"{item.get('total', 0):.2f}",
            ))
        tree.pack(fill="both", expand=True)

        totals = ctk.CTkFrame(self, fg_color="transparent")
        totals.pack(fill="x", padx=20, pady=8)
        cur = get_setting("currency", "ج.م")
        for label, val in [("المجموع الفرعي", self.sale.get("subtotal", 0)),
                           ("الخصم", self.sale.get("discount", 0)),
                           ("الضريبة", self.sale.get("tax", 0)),
                           ("الإجمالي", self.sale.get("total", 0))]:
            ctk.CTkLabel(totals, text=f"{label}: {val:.2f} {cur}",
                         font=ctk.CTkFont(size=12, weight="bold")).pack(side="right", padx=12)

        ctk.CTkButton(self, text="إغلاق", command=self.destroy).pack(pady=8)
