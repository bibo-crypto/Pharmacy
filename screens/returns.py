import customtkinter as ctk
from tkinter import messagebox, ttk
from models.returns import (create_sales_return, create_purchase_return,
                             get_all_sales_returns, get_all_purchase_returns)
from models.sale import get_all_sales, get_sale_by_id
from models.purchase import get_all_purchases, get_purchase_by_id
from utils.helpers import get_setting


class ReturnsScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        tabs = ctk.CTkTabview(self)
        tabs.grid(row=0, column=0, sticky="nsew", padx=20, pady=16)

        tab_sale_ret = tabs.add("مرتجع مبيعات")
        tab_pur_ret  = tabs.add("مرتجع مشتريات")
        tab_history  = tabs.add("سجل المرتجعات")

        self._build_sales_return_tab(tab_sale_ret)
        self._build_purchase_return_tab(tab_pur_ret)
        self._build_history_tab(tab_history)

    # ──────────────────────────────────────────
    # تاب: مرتجع مبيعات
    # ──────────────────────────────────────────
    def _build_sales_return_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        search_frame = ctk.CTkFrame(parent, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="ew", pady=8)
        ctk.CTkLabel(search_frame, text="بحث عن فاتورة بيع:",
                     font=ctk.CTkFont(size=13)).pack(side="right", padx=8)
        self.sale_search_var = ctk.StringVar()
        ctk.CTkEntry(search_frame, textvariable=self.sale_search_var,
                     placeholder_text="رقم الفاتورة...", width=200, height=36).pack(
            side="right", padx=4)
        ctk.CTkButton(search_frame, text="بحث", width=80,
                      command=self._load_sales).pack(side="right", padx=4)

        sales_frame = ctk.CTkFrame(parent, corner_radius=8)
        sales_frame.grid(row=1, column=0, sticky="nsew", pady=4)
        sales_frame.grid_rowconfigure(0, weight=1)
        sales_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "invoice", "customer", "total", "date")
        labels = {"id": "#", "invoice": "رقم الفاتورة", "customer": "العميل",
                  "total": "الإجمالي", "date": "التاريخ"}
        self.sales_tree = ttk.Treeview(sales_frame, columns=cols, show="headings", height=6)
        ctk.configure_treeview(self.sales_tree)
        for col in cols:
            self.sales_tree.heading(col, text=labels[col])
            self.sales_tree.column(col, width=130, anchor="center")
        vsb = ttk.Scrollbar(sales_frame, orient="vertical", command=self.sales_tree.yview)
        self.sales_tree.configure(yscrollcommand=vsb.set)
        self.sales_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.sales_tree.bind("<<TreeviewSelect>>", self._on_sale_select)

        items_frame = ctk.CTkFrame(parent, corner_radius=8)
        items_frame.grid(row=2, column=0, sticky="ew", pady=4)
        items_frame.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=0)

        ctk.CTkLabel(items_frame, text="أصناف الفاتورة:",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="e", padx=12, pady=4)

        cols2 = ("name", "qty", "price", "total", "return_qty")
        labels2 = {"name": "الدواء", "qty": "الكمية", "price": "السعر",
                   "total": "الإجمالي", "return_qty": "كمية الإرجاع"}
        self.return_items_tree = ttk.Treeview(items_frame, columns=cols2,
                                               show="headings", height=5)
        ctk.configure_treeview(self.return_items_tree)
        for col in cols2:
            self.return_items_tree.heading(col, text=labels2[col])
            self.return_items_tree.column(col, width=120, anchor="center")
        self.return_items_tree.pack(fill="x", padx=8, pady=4)

        reason_frame = ctk.CTkFrame(parent, fg_color="transparent")
        reason_frame.grid(row=3, column=0, sticky="ew", pady=4)
        ctk.CTkLabel(reason_frame, text="سبب الإرجاع:").pack(side="right", padx=8)
        self.sale_return_reason = ctk.StringVar()
        ctk.CTkEntry(reason_frame, textvariable=self.sale_return_reason,
                     width=300, height=36, justify="right").pack(side="right", padx=4)

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.grid(row=4, column=0, pady=8)
        ctk.CTkButton(btn_frame, text="↩ إرجاع الصنف المحدد", width=180,
                      fg_color="#d97706", command=self._return_selected_item).pack(
            side="left", padx=8)
        ctk.CTkButton(btn_frame, text="↩ إرجاع الفاتورة كاملة", width=180,
                      fg_color="#dc2626", command=self._return_full_invoice).pack(
            side="left", padx=8)

        self._current_sale_items = []
        self._current_sale_id = None
        self._load_sales()

    def _load_sales(self):
        sales = get_all_sales(search=self.sale_search_var.get().strip() or None)
        self.sales_tree.delete(*self.sales_tree.get_children())
        for _i_s, s in enumerate(sales):
            _row_tag = "evenrow" if _i_s % 2 == 0 else "oddrow"
            # نعرض المكتملة فقط (لا الملغاة ولا المعلقة)
            if s.get("status") == "completed":
                self.sales_tree.insert("", "end", tags=(_row_tag,), iid=str(s["id"]), values=(
                    s["id"], s.get("invoice_number", ""),
                    (s.get("customer_name") or "نقدي")[:14],
                    f"{s.get('total', 0):.2f}",
                    s.get("sale_date", "")[:16],
                ))

    def _on_sale_select(self, event):
        sel = self.sales_tree.selection()
        if not sel:
            return
        sale_id = int(sel[0])
        sale, items = get_sale_by_id(sale_id)
        self._current_sale_id = sale_id
        self._current_sale_items = items
        self.return_items_tree.delete(*self.return_items_tree.get_children())
        for _i_item, item in enumerate(items):
            _row_tag = "evenrow" if _i_item % 2 == 0 else "oddrow"
            if item.get("quantity", 0) > 0:
                self.return_items_tree.insert("", "end", tags=(_row_tag,), iid=str(item["id"]), values=(
                    item.get("medicine_name", ""),
                    item.get("quantity", 0),
                    f"{item.get('unit_price', 0):.2f}",
                    f"{item.get('total', 0):.2f}",
                    item.get("quantity", 0),
                ))

    def _return_selected_item(self):
        if not self._current_sale_id:
            messagebox.showwarning("تحذير", "يرجى اختيار فاتورة أولاً", parent=self)
            return
        sel = self.return_items_tree.selection()
        if not sel:
            messagebox.showwarning("تحذير", "يرجى اختيار صنف أولاً", parent=self)
            return
        item_id = int(sel[0])
        item = next((i for i in self._current_sale_items if i["id"] == item_id), None)
        if not item:
            return
        if item["quantity"] > 1:
            self._open_return_qty_dialog(item, is_purchase=False)
        else:
            self._execute_return(item, 1, is_purchase=False)

    def _return_full_invoice(self):
        if not self._current_sale_id or not self._current_sale_items:
            messagebox.showwarning("تحذير", "يرجى اختيار فاتورة أولاً", parent=self)
            return
        reason = self.sale_return_reason.get().strip() or "إرجاع كامل"
        if not messagebox.askyesno("تأكيد", "إرجاع الفاتورة كاملة؟", parent=self):
            return
        return_items = [{
            "medicine_id": item["medicine_id"],
            "quantity": item["quantity"],
            "amount": item["total"],
        } for item in self._current_sale_items]
        try:
            create_sales_return(self._current_sale_id, return_items, reason)
            messagebox.showinfo("تم", "تم إرجاع الفاتورة كاملة بنجاح", parent=self)
            self._load_sales()
            self.return_items_tree.delete(*self.return_items_tree.get_children())
            self._current_sale_id = None
            self._current_sale_items = []
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ: {e}", parent=self)

    # ──────────────────────────────────────────
    # تاب: مرتجع مشتريات
    # ──────────────────────────────────────────
    def _build_purchase_return_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        search_frame = ctk.CTkFrame(parent, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="ew", pady=8)
        ctk.CTkLabel(search_frame, text="بحث عن فاتورة شراء:").pack(side="right", padx=8)
        self.pur_search_var = ctk.StringVar()
        ctk.CTkEntry(search_frame, textvariable=self.pur_search_var,
                     width=200, height=36).pack(side="right", padx=4)
        ctk.CTkButton(search_frame, text="بحث", width=80,
                      command=self._load_purchases).pack(side="right", padx=4)

        purchases_frame = ctk.CTkFrame(parent, corner_radius=8)
        purchases_frame.grid(row=1, column=0, sticky="nsew", pady=4)
        purchases_frame.grid_rowconfigure(0, weight=1)
        purchases_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "invoice", "supplier", "total", "date")
        labels = {"id": "#", "invoice": "رقم الفاتورة", "supplier": "المورد",
                  "total": "الإجمالي", "date": "التاريخ"}
        self.pur_tree = ttk.Treeview(purchases_frame, columns=cols, show="headings", height=6)
        ctk.configure_treeview(self.pur_tree)
        for col in cols:
            self.pur_tree.heading(col, text=labels[col])
            self.pur_tree.column(col, width=130, anchor="center")
        vsb = ttk.Scrollbar(purchases_frame, orient="vertical", command=self.pur_tree.yview)
        self.pur_tree.configure(yscrollcommand=vsb.set)
        self.pur_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.pur_tree.bind("<<TreeviewSelect>>", self._on_purchase_select)

        items_frame = ctk.CTkFrame(parent, corner_radius=8)
        items_frame.grid(row=2, column=0, sticky="ew", pady=4)
        ctk.CTkLabel(items_frame, text="أصناف الفاتورة:",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="e", padx=12, pady=4)
        cols2 = ("name", "qty", "price", "total")
        labels2 = {"name": "الدواء", "qty": "الكمية", "price": "السعر", "total": "الإجمالي"}
        self.pur_items_tree = ttk.Treeview(items_frame, columns=cols2,
                                            show="headings", height=4)
        ctk.configure_treeview(self.pur_items_tree)
        for col in cols2:
            self.pur_items_tree.heading(col, text=labels2[col])
            self.pur_items_tree.column(col, width=140, anchor="center")
        self.pur_items_tree.pack(fill="x", padx=8, pady=4)

        reason_frame = ctk.CTkFrame(parent, fg_color="transparent")
        reason_frame.grid(row=3, column=0, sticky="ew", pady=4)
        ctk.CTkLabel(reason_frame, text="سبب الإرجاع:").pack(side="right", padx=8)
        self.pur_reason_var = ctk.StringVar()
        ctk.CTkEntry(reason_frame, textvariable=self.pur_reason_var, width=300, height=36,
                     justify="right").pack(side="right", padx=4)

        ctk.CTkButton(parent, text="↩ إرجاع الصنف المحدد للمورد", width=220,
                      fg_color="#dc2626", command=self._return_purchase_item).grid(
            row=4, column=0, pady=8)

        self._current_purchase_id = None
        self._current_purchase_items = []
        self._current_supplier_id = None
        self._load_purchases()

    def _load_purchases(self):
        purchases = get_all_purchases(search=self.pur_search_var.get().strip() or None)
        self.pur_tree.delete(*self.pur_tree.get_children())
        for _i_p, p in enumerate(purchases):
            _row_tag = "evenrow" if _i_p % 2 == 0 else "oddrow"
            self.pur_tree.insert("", "end", tags=(_row_tag,), iid=str(p["id"]), values=(
                p["id"], p.get("invoice_number", ""),
                p.get("supplier_name", "")[:16],
                f"{p.get('total', 0):.2f}",
                p.get("purchase_date", "")[:16],
            ))

    def _on_purchase_select(self, event):
        sel = self.pur_tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        purchase, items = get_purchase_by_id(pid)
        self._current_purchase_id = pid
        self._current_purchase_items = items
        self._current_supplier_id = purchase.get("supplier_id") if purchase else None
        self.pur_items_tree.delete(*self.pur_items_tree.get_children())
        for _i_item, item in enumerate(items):
            _row_tag = "evenrow" if _i_item % 2 == 0 else "oddrow"
            if item.get("quantity", 0) > 0:
                self.pur_items_tree.insert("", "end", tags=(_row_tag,), iid=str(item["id"]), values=(
                    item.get("medicine_name", ""), item.get("quantity", 0),
                    f"{item.get('unit_price', 0):.2f}", f"{item.get('total', 0):.2f}",
                ))

    def _return_purchase_item(self):
        if not self._current_purchase_id:
            messagebox.showwarning("تحذير", "يرجى اختيار فاتورة أولاً", parent=self)
            return
        sel = self.pur_items_tree.selection()
        if not sel:
            messagebox.showwarning("تحذير", "يرجى اختيار صنف أولاً", parent=self)
            return
        item_id = int(sel[0])
        item = next((i for i in self._current_purchase_items if i["id"] == item_id), None)
        if not item:
            return
        if item["quantity"] > 1:
            self._open_return_qty_dialog(item, is_purchase=True)
        else:
            self._execute_return(item, 1, is_purchase=True)

    # ──────────────────────────────────────────
    # مشترك: نافذة تحديد الكمية + تنفيذ الإرجاع
    # ──────────────────────────────────────────
    def _open_return_qty_dialog(self, item, is_purchase):
        dlg = ctk.CTkToplevel(self)
        dlg.title("تحديد الكمية المرتجعة")
        dlg.geometry("320x220")
        dlg.grab_set()
        dlg.resizable(False, False)

        ctk.CTkLabel(dlg, text=f"إرجاع: {item.get('medicine_name', 'صنف')}",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(15, 5))
        ctk.CTkLabel(dlg, text=f"الكمية المتاحة في الفاتورة: {item['quantity']}").pack()

        qty_var = ctk.StringVar(value=str(item["quantity"]))
        entry = ctk.CTkEntry(dlg, textvariable=qty_var, width=100,
                              justify="center", font=ctk.CTkFont(size=16))
        entry.pack(pady=10)
        entry.focus_set()
        entry.select_range(0, "end")

        def confirm():
            try:
                qty = int(qty_var.get().strip() or 0)
                if qty <= 0 or qty > item["quantity"]:
                    messagebox.showerror("خطأ",
                                         f"يرجى إدخال كمية بين 1 و {item['quantity']}",
                                         parent=dlg)
                    return
                self._execute_return(item, qty, is_purchase)
                dlg.destroy()
            except ValueError:
                messagebox.showerror("خطأ", "يرجى إدخال رقم صحيح", parent=dlg)

        ctk.CTkButton(dlg, text="تأكيد الإرجاع", command=confirm).pack(pady=10)
        dlg.bind("<Return>", lambda e: confirm())

    def _execute_return(self, item, qty, is_purchase):
        reason = (
            self.pur_reason_var.get() if is_purchase else self.sale_return_reason.get()
        ).strip() or "لم يحدد"
        return_items = [{
            "medicine_id": item["medicine_id"],
            "quantity": qty,
            "amount": round(qty * item["unit_price"], 2),
        }]
        try:
            if is_purchase:
                create_purchase_return(
                    self._current_purchase_id, self._current_supplier_id,
                    return_items, reason)
                messagebox.showinfo(
                    "تم", f"تم إرجاع {qty} من {item.get('medicine_name','')} للمورد",
                    parent=self)
                self._load_purchases()
                self.pur_items_tree.delete(*self.pur_items_tree.get_children())
            else:
                create_sales_return(self._current_sale_id, return_items, reason)
                messagebox.showinfo(
                    "تم", f"تم إرجاع {qty} من {item.get('medicine_name','')}",
                    parent=self)
                self._load_sales()
                self.return_items_tree.delete(*self.return_items_tree.get_children())
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء الإرجاع: {e}", parent=self)

    # ──────────────────────────────────────────
    # تاب: سجل المرتجعات
    # ──────────────────────────────────────────
    def _build_history_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        tabs2 = ctk.CTkTabview(parent)
        tabs2.grid(row=0, column=0, sticky="nsew")
        parent.grid_rowconfigure(0, weight=1)

        tab_s = tabs2.add("مرتجعات المبيعات")
        tab_p = tabs2.add("مرتجعات المشتريات")

        self._build_sales_returns_hist(tab_s)
        self._build_purchase_returns_hist(tab_p)

    def _build_sales_returns_hist(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        cols = ("id", "invoice", "user", "reason", "amount", "date")
        labels = {"id": "#", "invoice": "رقم الفاتورة", "user": "المستخدم",
                  "reason": "السبب", "amount": "المبلغ", "date": "التاريخ"}
        self.sales_hist_tree = ttk.Treeview(parent, columns=cols, show="headings")
        ctk.configure_treeview(self.sales_hist_tree)
        for col in cols:
            self.sales_hist_tree.heading(col, text=labels[col])
            self.sales_hist_tree.column(col, width=120, anchor="center")
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.sales_hist_tree.yview)
        self.sales_hist_tree.configure(yscrollcommand=vsb.set)
        self.sales_hist_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        ctk.CTkButton(parent, text="🔄 تحديث", fg_color="gray", width=90,
                      command=self._reload_sales_hist).grid(row=1, column=0, pady=4)
        self._reload_sales_hist()

    def _reload_sales_hist(self):
        """تحديث سجل مرتجعات المبيعات من قاعدة البيانات (يجلب بيانات حديثة)"""
        self.sales_hist_tree.delete(*self.sales_hist_tree.get_children())
        for _i_r, r in enumerate(get_all_sales_returns()):
            _row_tag = "evenrow" if _i_r % 2 == 0 else "oddrow"
            self.sales_hist_tree.insert("", "end", tags=(_row_tag,), values=(
                r["id"], r.get("invoice_number", ""), r.get("user_name", ""),
                r.get("return_reason", ""), f"{r.get('total_return_amount', 0):.2f}",
                r.get("return_date", "")[:16],
            ))

    def _build_purchase_returns_hist(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        cols = ("id", "invoice", "supplier", "user", "reason", "amount", "date")
        labels = {"id": "#", "invoice": "رقم الفاتورة", "supplier": "المورد",
                  "user": "المستخدم", "reason": "السبب", "amount": "المبلغ", "date": "التاريخ"}
        self.pur_hist_tree = ttk.Treeview(parent, columns=cols, show="headings")
        ctk.configure_treeview(self.pur_hist_tree)
        for col in cols:
            self.pur_hist_tree.heading(col, text=labels[col])
            self.pur_hist_tree.column(col, width=100, anchor="center")
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.pur_hist_tree.yview)
        self.pur_hist_tree.configure(yscrollcommand=vsb.set)
        self.pur_hist_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        ctk.CTkButton(parent, text="🔄 تحديث", fg_color="gray", width=90,
                      command=self._reload_purchase_hist).grid(row=1, column=0, pady=4)
        self._reload_purchase_hist()

    def _reload_purchase_hist(self):
        """تحديث سجل مرتجعات المشتريات من قاعدة البيانات (يجلب بيانات حديثة)"""
        self.pur_hist_tree.delete(*self.pur_hist_tree.get_children())
        for _i_r, r in enumerate(get_all_purchase_returns()):
            _row_tag = "evenrow" if _i_r % 2 == 0 else "oddrow"
            self.pur_hist_tree.insert("", "end", tags=(_row_tag,), values=(
                r["id"], r.get("invoice_number", ""), r.get("supplier_name", ""),
                r.get("user_name", ""), r.get("reason", ""),
                f"{r.get('total_amount', 0):.2f}", r.get("return_date", "")[:16],
            ))
