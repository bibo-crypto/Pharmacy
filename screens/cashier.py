import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
from models.sale import get_pending_sales, get_sale_by_id, complete_pending_sale
from utils.helpers import get_setting, format_currency
from utils.printing import generate_receipt_pdf, print_receipt
import os, subprocess, sys


class CashierScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.selected_sale_id = None
        self.sale = None
        self.sale_items = []
        self._refresh_job = None
        self._build()
        self._load_pending_sales()
        self._schedule_auto_refresh()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=16)
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(self, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=16)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._build_left(left)
        self._build_right(right)

    def _build_left(self, parent):
        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        ctk.CTkLabel(toolbar, text="💵 شاشة الكاشير",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="right")

        # عداد الفواتير المعلقة
        self.pending_count_lbl = ctk.CTkLabel(toolbar, text="",
                                               font=ctk.CTkFont(size=12),
                                               text_color="#d97706")
        self.pending_count_lbl.pack(side="left", padx=8)

        search_frame = ctk.CTkFrame(parent, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *a: self._load_pending_sales())
        ctk.CTkEntry(search_frame, textvariable=self.search_var,
                     placeholder_text="🔍 بحث برقم الفاتورة أو العميل...",
                     width=260, height=36).pack(side="right", padx=(0, 8))

        table_frame = ctk.CTkFrame(parent, fg_color="transparent")
        table_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(4, 12))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "invoice", "customer", "cashier", "total", "time")
        labels = {
            "id": "#", "invoice": "رقم الفاتورة", "customer": "العميل",
            "cashier": "المحرر", "total": "الإجمالي", "time": "الوقت"
        }
        widths = {"id": 40, "invoice": 130, "customer": 110,
                  "cashier": 100, "total": 90, "time": 80}


        self.pending_tree = ttk.Treeview(table_frame, columns=cols,
                                          show="headings", selectmode="browse")
        ctk.configure_treeview(self.pending_tree)
        for col in cols:
            self.pending_tree.heading(col, text=labels[col], anchor="center")
            self.pending_tree.column(col, width=widths.get(col, 80), anchor="center")
        self.pending_tree.bind("<<TreeviewSelect>>", lambda e: self._select_pending())
        self.pending_tree.bind("<Double-1>", lambda e: self._select_pending())

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.pending_tree.yview)
        self.pending_tree.configure(yscrollcommand=vsb.set)
        self.pending_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # رسالة بدون فواتير
        self.no_pending_lbl = ctk.CTkLabel(parent,
                                            text="✅ لا توجد فواتير معلقة حالياً",
                                            font=ctk.CTkFont(size=13),
                                            text_color="gray")
        self.no_pending_lbl.grid(row=3, column=0, pady=4)
        self.no_pending_lbl.grid_remove()

    def _build_right(self, parent):
        # ── عنوان ──
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        ctk.CTkLabel(header, text="تفاصيل الفاتورة",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="right")

        info_frame = ctk.CTkFrame(parent, fg_color="transparent")
        info_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        info_frame.grid_rowconfigure(2, weight=1)
        info_frame.grid_columnconfigure(0, weight=1)

        # بيانات الفاتورة
        details = ctk.CTkFrame(info_frame, fg_color=("gray90", "#1e293b"), corner_radius=8)
        details.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        details.grid_columnconfigure((0, 1), weight=1)
        self.invoice_label = ctk.CTkLabel(details, text="رقم الفاتورة: -",
                                           font=ctk.CTkFont(size=12))
        self.invoice_label.grid(row=0, column=1, sticky="e", padx=12, pady=4)
        self.customer_label = ctk.CTkLabel(details, text="العميل: -",
                                            font=ctk.CTkFont(size=12))
        self.customer_label.grid(row=0, column=0, sticky="w", padx=12, pady=4)
        self.cashier_label = ctk.CTkLabel(details, text="المحرر: -",
                                           font=ctk.CTkFont(size=12))
        self.cashier_label.grid(row=1, column=1, sticky="e", padx=12, pady=4)
        self.date_label = ctk.CTkLabel(details, text="التاريخ: -",
                                        font=ctk.CTkFont(size=12))
        self.date_label.grid(row=1, column=0, sticky="w", padx=12, pady=4)

        # جدول الأصناف
        items_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        items_frame.grid(row=1, column=0, sticky="nsew", pady=4)
        items_frame.grid_rowconfigure(0, weight=1)
        items_frame.grid_columnconfigure(0, weight=1)

        cols = ("name", "qty", "price", "total")
        labels = {"name": "الدواء", "qty": "الكمية", "price": "السعر", "total": "الإجمالي"}
        widths = {"name": 180, "qty": 70, "price": 90, "total": 90}

        self.items_tree = ttk.Treeview(items_frame, columns=cols, show="headings", height=10)
        ctk.configure_treeview(self.items_tree)
        for col in cols:
            self.items_tree.heading(col, text=labels[col], anchor="center")
            self.items_tree.column(col, width=widths.get(col, 80), anchor="center")
        vsb_items = ttk.Scrollbar(items_frame, orient="vertical", command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=vsb_items.set)
        self.items_tree.grid(row=0, column=0, sticky="nsew")
        vsb_items.grid(row=0, column=1, sticky="ns")

        # ملخص الأرقام
        summary = ctk.CTkFrame(parent, fg_color="transparent")
        summary.grid(row=2, column=0, sticky="ew", padx=12, pady=4)
        summary.grid_columnconfigure(1, weight=1)
        self.lbl_subtotal = self._total_row(summary, "المجموع الفرعي:", 0)
        self.lbl_discount = self._total_row(summary, "الخصم:", 1)
        self.lbl_tax = self._total_row(summary, "الضريبة:", 2)
        self.lbl_total = self._total_row(summary, "الإجمالي:", 3, bold=True, size=15)

        # طريقة الدفع
        payment_frame = ctk.CTkFrame(parent, fg_color="transparent")
        payment_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=4)
        payment_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(payment_frame, text="طريقة الدفع:",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="e")
        self.payment_var = ctk.StringVar(value="كاش")
        ctk.CTkOptionMenu(payment_frame, values=["كاش", "بطاقة", "مختلط"],
                          variable=self.payment_var, width=130).grid(
            row=0, column=1, sticky="w", padx=8)

        # المبلغ المدفوع
        paid_frame = ctk.CTkFrame(parent, fg_color="transparent")
        paid_frame.grid(row=4, column=0, sticky="ew", padx=12, pady=4)
        paid_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(paid_frame, text="المبلغ المدفوع:",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="e")
        self.paid_var = ctk.StringVar(value="0")
        self.paid_var.trace("w", lambda *a: self._update_change())
        self.paid_entry = ctk.CTkEntry(paid_frame, textvariable=self.paid_var,
                                        width=150, height=40, justify="center",
                                        font=ctk.CTkFont(size=16, weight="bold"))
        self.paid_entry.grid(row=0, column=1, sticky="w", padx=8)

        # الباقي
        change_frame = ctk.CTkFrame(parent, fg_color="transparent")
        change_frame.grid(row=5, column=0, sticky="ew", padx=12, pady=4)
        change_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(change_frame, text="الباقي:",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="e")
        self.change_label = ctk.CTkLabel(change_frame, text="0.00",
                                          font=ctk.CTkFont(size=22, weight="bold"),
                                          text_color="#059669")
        self.change_label.grid(row=0, column=1, sticky="w", padx=8)

        # أزرار
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.grid(row=6, column=0, sticky="ew", padx=12, pady=(12, 16))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(actions, text="✅ إتمام البيع", height=46,
                      font=ctk.CTkFont(size=15, weight="bold"),
                      fg_color="#2563eb", hover_color="#1d4ed8",
                      command=self._complete_sale).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(actions, text="🖨 طباعة الفاتورة", height=46,
                      font=ctk.CTkFont(size=13),
                      fg_color="#059669", hover_color="#047857",
                      command=lambda: self._print_receipt()).grid(row=0, column=1, padx=4, sticky="ew")

        # مؤشر التحديث التلقائي
        self.refresh_indicator = ctk.CTkLabel(parent, text="🔄 تحديث تلقائي كل 3 ثوانٍ",
                                               font=ctk.CTkFont(size=10),
                                               text_color="gray")
        self.refresh_indicator.grid(row=7, column=0, pady=(0, 8))

    def _total_row(self, parent, label, row, bold=False, size=12):
        ctk.CTkLabel(parent, text=label,
                     font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"),
                     anchor="e").grid(row=row, column=0, sticky="e", pady=3)
        lbl = ctk.CTkLabel(parent, text="0.00",
                            font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"),
                            anchor="w")
        lbl.grid(row=row, column=1, sticky="w", padx=8, pady=3)
        return lbl

    def _load_pending_sales(self, keep_selection=False, silent=False):
        self.pending_tree.delete(*self.pending_tree.get_children())
        sales = get_pending_sales(search=self.search_var.get().strip() or None)

        if sales:
            self.no_pending_lbl.grid_remove()
            self.pending_count_lbl.configure(
                text=f"معلقة: {len(sales)}")
        else:
            self.no_pending_lbl.grid()
            self.pending_count_lbl.configure(text="")

        for _i_s, s in enumerate(sales):
            _row_tag = "evenrow" if _i_s % 2 == 0 else "oddrow"
            time_str = s.get("sale_date", "")[-8:-3] if s.get("sale_date") else ""
            self.pending_tree.insert("", "end", tags=(_row_tag,), iid=str(s["id"]), values=(
                s["id"], s.get("invoice_number", ""),
                s.get("customer_name") or "نقدي",
                s.get("cashier_name", ""),
                f"{s.get('total', 0):.2f}",
                time_str,
            ))

        children = self.pending_tree.get_children()
        if children:
            if keep_selection and self.selected_sale_id and                self.pending_tree.exists(str(self.selected_sale_id)):
                self.pending_tree.selection_set(str(self.selected_sale_id))
                if not silent:
                    self._select_pending()
            else:
                self.pending_tree.selection_set(children[0])
                if not silent:
                    self._select_pending()
        else:
            self.sale = None
            self.sale_items = []
            self.selected_sale_id = None
            if not silent:
                self._refresh_details()

    def _schedule_auto_refresh(self):
        self.cancel_auto_refresh()
        self._refresh_job = self.after(3000, self._auto_refresh)

    def _auto_refresh(self):
        self._load_pending_sales(keep_selection=True, silent=True)
        self._schedule_auto_refresh()

    def cancel_auto_refresh(self):
        if self._refresh_job:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
            self._refresh_job = None

    def destroy(self):
        self.cancel_auto_refresh()
        super().destroy()

    def _select_pending(self):
        sel = self.pending_tree.selection()
        if not sel:
            return
        self.selected_sale_id = int(sel[0])
        sale, items = get_sale_by_id(self.selected_sale_id)
        if not sale:
            return
        self.sale = sale
        self.sale_items = items
        self._refresh_details()

    def _refresh_details(self):
        if not self.sale:
            self.invoice_label.configure(text="رقم الفاتورة: -")
            self.customer_label.configure(text="العميل: -")
            self.cashier_label.configure(text="المحرر: -")
            self.date_label.configure(text="التاريخ: -")
            self.items_tree.delete(*self.items_tree.get_children())
            self.lbl_subtotal.configure(text="0.00")
            self.lbl_discount.configure(text="0.00")
            self.lbl_tax.configure(text="0.00")
            self.lbl_total.configure(text="0.00")
            self.paid_var.set("0")
            self.change_label.configure(text="0.00", text_color="#059669")
            return

        self.invoice_label.configure(text=f"رقم الفاتورة: {self.sale.get('invoice_number','')}")
        self.customer_label.configure(text=f"العميل: {self.sale.get('customer_name') or 'نقدي'}")
        self.cashier_label.configure(text=f"المحرر: {self.sale.get('cashier_name','')}")
        self.date_label.configure(text=f"التاريخ: {self.sale.get('sale_date','')[:16]}")

        self.items_tree.delete(*self.items_tree.get_children())
        for _i_item, item in enumerate(self.sale_items):
            _row_tag = "evenrow" if _i_item % 2 == 0 else "oddrow"
            self.items_tree.insert("", "end", tags=(_row_tag,), values=(
                item.get("medicine_name", ""),
                item.get("quantity", 0),
                f"{item.get('unit_price', 0):.2f}",
                f"{item.get('total', 0):.2f}",
            ))

        cur = get_setting("currency", "ج.م")
        self.lbl_subtotal.configure(text=f"{self.sale.get('subtotal', 0):.2f} {cur}")
        self.lbl_discount.configure(text=f"{self.sale.get('discount', 0):.2f} {cur}")
        self.lbl_tax.configure(text=f"{self.sale.get('tax', 0):.2f} {cur}")
        self.lbl_total.configure(text=f"{self.sale.get('total', 0):.2f} {cur}")

        # تعبئة المبلغ المدفوع فقط إذا تغيّرت الفاتورة أو كان الحقل لا يزال فارغاً/صفراً
        invoice_id = self.sale.get("id")
        try:
            current_paid = float(self.paid_var.get() or 0)
        except ValueError:
            current_paid = 0
        if getattr(self, "_last_invoice_id", None) != invoice_id or current_paid == 0:
            self._last_invoice_id = invoice_id
            self.paid_var.set(f"{self.sale.get('total', 0):.2f}")
            self.after(100, lambda: self.paid_entry.focus_set())
        self._update_change()

    def _update_change(self):
        try:
            paid = float(self.paid_var.get() or 0)
        except ValueError:
            paid = 0
        total = float(self.sale.get("total", 0)) if self.sale else 0
        change = round(paid - total, 2)
        self.change_label.configure(
            text=f"{change:.2f}",
            text_color="#059669" if change >= 0 else "#dc2626")

    def _complete_sale(self):
        if not self.sale or self.sale.get("status") != "pending":
            messagebox.showwarning("تحذير", "يرجى اختيار فاتورة معلقة أولاً", parent=self)
            return

        try:
            paid = float(self.paid_var.get() or 0)
        except ValueError:
            messagebox.showwarning("تحذير", "يرجى إدخال مبلغ مدفوع صحيح", parent=self)
            return

        total = float(self.sale.get("total", 0))
        if self.payment_var.get() == "كاش" and round(paid - total, 2) < 0:
            messagebox.showwarning("تحذير",
                                   f"المبلغ المدفوع ({paid:.2f}) أقل من الإجمالي ({total:.2f})",
                                   parent=self)
            return

        payment_map = {"كاش": "cash", "بطاقة": "card", "مختلط": "mixed"}
        payment_data = {
            "paid_amount": paid,
            "payment_method": payment_map.get(self.payment_var.get(), "cash"),
            "user_id": self.sale.get("user_id"),
        }

        try:
            complete_pending_sale(self.selected_sale_id, payment_data)
            completed_sale, completed_items = get_sale_by_id(self.selected_sale_id)
            if not completed_sale:
                raise ValueError("تعذر تحميل الفاتورة المكتملة")

            if messagebox.askyesno("طباعة", "هل تريد طباعة الفاتورة؟", parent=self):
                self._print_receipt(completed_sale, completed_items)

            messagebox.showinfo("تم", "✅ تم إتمام الفاتورة بنجاح", parent=self)
            self.selected_sale_id = None
            self.sale = None
            self.sale_items = []
            self._load_pending_sales()
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء إتمام الفاتورة:\n{e}", parent=self)

    def _print_receipt(self, sale=None, items=None):
        sale = sale or self.sale
        items = items or self.sale_items
        if not sale:
            messagebox.showwarning("تحذير", "لا توجد فاتورة محددة", parent=self)
            return
        if sale.get("status") != "completed":
            messagebox.showwarning("تحذير",
                                   "لا يمكن طباعة فاتورة لم تُكتمل بعد", parent=self)
            return
        try:
            path = print_receipt(sale, items)
            if not path:
                raise RuntimeError("تعذر إنشاء ملف الفاتورة")
        except Exception as e:
            messagebox.showerror("خطأ", f"خطأ في الطباعة: {e}", parent=self)
