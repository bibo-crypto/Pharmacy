import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
from models.medicine import get_medicine_by_barcode, get_all_medicines
from models.sale import create_sale, create_pending_sale
from models.customer import get_all_customers
from utils.auth import get_current_user, has_permission
from utils.helpers import get_setting, format_currency
from utils.printing import generate_receipt_pdf, print_receipt
import os, subprocess, sys


class POSScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.cart_items = []
        self.selected_customer = None
        self.barcode_entry = None
        self._global_key_binding = None
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=16)
        left.grid_rowconfigure(3, weight=1)
        left.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(self, corner_radius=10, width=360)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 16), pady=16)
        right.grid_propagate(False)
        right.grid_columnconfigure(0, weight=1)

        self._build_left(left)
        self._build_right(right)

        # ربط الاختصارات على مستوى الـ Frame فقط (ليس bind_all)
        # سنستخدم bind على النافذة الجذر عند ظهور هذه الشاشة
        self.after(100, self._setup_keybindings)

    def _setup_keybindings(self):
        """تسجيل اختصارات لوحة المفاتيح على النافذة الجذر مع تتبعها لإلغائها عند الخروج"""
        try:
            root = self.winfo_toplevel()
            # نستخدم tag مميز لهذه الشاشة تحديداً
            self._global_key_binding = root.bind("<KeyPress>", self._on_global_keypress, add=True)
        except Exception:
            pass

    def _teardown_keybindings(self):
        """إلغاء تسجيل الاختصارات عند مغادرة الشاشة"""
        try:
            root = self.winfo_toplevel()
            if self._global_key_binding:
                root.unbind("<KeyPress>", self._global_key_binding)
                self._global_key_binding = None
        except Exception:
            pass

    def destroy(self):
        self._teardown_keybindings()
        super().destroy()

    def _build_left(self, parent):
        # ── شريط البحث ──
        search_frame = ctk.CTkFrame(parent, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        search_frame.grid_columnconfigure((0, 2), weight=1)

        ctk.CTkLabel(search_frame, text="🖥 نقطة البيع",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=4, sticky="e", padx=(8, 16))

        ctk.CTkLabel(search_frame, text="باركود:",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=3, sticky="e", padx=4)
        self.barcode_var = ctk.StringVar()
        self.barcode_entry = ctk.CTkEntry(
            search_frame, textvariable=self.barcode_var,
            placeholder_text="📷 امسح أو أدخل الباركود...",
            width=200, height=40, font=ctk.CTkFont(size=14))
        self.barcode_entry.grid(row=0, column=2, padx=4, sticky="w")
        self.barcode_entry.bind("<Return>", self._scan_barcode)

        ctk.CTkLabel(search_frame, text="بحث بالاسم:",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=1, sticky="e", padx=4)
        self.med_search_var = ctk.StringVar()
        self.med_search_var.trace("w", lambda *a: self._search_medicines())
        self.med_entry = ctk.CTkEntry(
            search_frame, textvariable=self.med_search_var,
            placeholder_text="🔍 بحث باسم الدواء...", width=200, height=40)
        self.med_entry.grid(row=0, column=0, padx=4, sticky="w")

        self.barcode_entry.focus()

        # ── قائمة المخزون ──
        inventory_frame = ctk.CTkFrame(parent, fg_color="transparent")
        inventory_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 4))
        inventory_frame.grid_rowconfigure(1, weight=1)
        inventory_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(inventory_frame, text="الأدوية المتاحة في المخزون",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, sticky="e", pady=(0, 4))

        list_frame = ctk.CTkFrame(inventory_frame, fg_color="transparent")
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        med_cols = ("name", "barcode", "quantity", "price")
        med_labels = {"name": "الدواء", "barcode": "الباركود",
                      "quantity": "المخزون", "price": "السعر"}
        med_widths = {"name": 230, "barcode": 150, "quantity": 90, "price": 90}


        self.meds_tree = ttk.Treeview(list_frame, columns=med_cols,
                                      show="headings", selectmode="browse", height=7)
        ctk.configure_treeview(self.meds_tree)
        for col in med_cols:
            self.meds_tree.heading(col, text=med_labels[col], anchor="center")
            self.meds_tree.column(col, width=med_widths.get(col, 80), anchor="center")

        vsb_med = ttk.Scrollbar(list_frame, orient="vertical", command=self.meds_tree.yview)
        self.meds_tree.configure(yscrollcommand=vsb_med.set)
        self.meds_tree.grid(row=0, column=0, sticky="nsew")
        vsb_med.grid(row=0, column=1, sticky="ns")
        self.meds_tree.bind("<Double-1>", self._select_from_inventory)
        self.meds_tree.bind("<Return>", self._select_from_inventory)
        self.meds_tree_data = []

        # ── سلة المشتريات ──
        ctk.CTkLabel(parent, text="🛒 سلة المشتريات",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=12, pady=(8, 2))

        cart_frame = ctk.CTkFrame(parent, fg_color="transparent")
        cart_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=4)
        cart_frame.grid_rowconfigure(0, weight=1)
        cart_frame.grid_columnconfigure(0, weight=1)

        cols = ("name", "unit_price", "quantity", "discount", "total")
        col_labels = {"name": "الدواء", "unit_price": "السعر",
                      "quantity": "الكمية", "discount": "خصم", "total": "الإجمالي"}
        widths = {"name": 220, "unit_price": 85, "quantity": 75, "discount": 75, "total": 95}

        self.cart_tree = ttk.Treeview(cart_frame, columns=cols, show="headings",
                                      selectmode="browse", height=13)
        ctk.configure_treeview(self.cart_tree)
        for col in cols:
            self.cart_tree.heading(col, text=col_labels[col], anchor="center")
            self.cart_tree.column(col, width=widths.get(col, 80), anchor="center")

        vsb = ttk.Scrollbar(cart_frame, orient="vertical", command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=vsb.set)
        self.cart_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.cart_tree.bind("<Double-1>", lambda e: self._edit_qty())
        # الاختصارات تُعالج في _on_global_keypress فقط لتجنب التنفيذ المزدوج

        # ── أزرار السلة ──
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=12, pady=6)

        ctk.CTkButton(actions, text="❌ حذف صنف [Del]", width=140,
                      fg_color="#dc2626", hover_color="#b91c1c",
                      command=self._remove_item).pack(side="right", padx=4)
        ctk.CTkButton(actions, text="✏️ تعديل الكمية [+]", width=145,
                      fg_color="#d97706", hover_color="#b45309",
                      command=self._edit_qty).pack(side="right", padx=4)
        ctk.CTkButton(actions, text="🗑 مسح الكل", width=110,
                      fg_color="gray", command=self._clear_cart).pack(side="right", padx=4)

        self._load_inventory_tree()

    def _build_right(self, parent):
        ctk.CTkLabel(parent, text="ملخص الفاتورة",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(16, 8), sticky="e")

        # ── العميل ──
        customer_frame = ctk.CTkFrame(parent, fg_color="transparent")
        customer_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        ctk.CTkLabel(customer_frame, text="العميل:",
                     font=ctk.CTkFont(size=12)).pack(side="right")
        self.customer_var = ctk.StringVar(value="عميل نقدي")
        customers = [("عميل نقدي", None)] + [(c["name"], c["id"]) for c in get_all_customers()]
        self.customer_data = customers
        ctk.CTkOptionMenu(customer_frame,
                          values=[c[0] for c in customers],
                          variable=self.customer_var,
                          command=self._on_customer_change,
                          width=200).pack(side="left", padx=4)

        sep = ctk.CTkFrame(parent, height=1, fg_color="gray60")
        sep.grid(row=2, column=0, sticky="ew", padx=12, pady=6)

        # ── ملخص الأرقام ──
        totals_frame = ctk.CTkFrame(parent, fg_color="transparent")
        totals_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=4)
        totals_frame.grid_columnconfigure(1, weight=1)

        self.lbl_subtotal = self._total_row(totals_frame, "المجموع الفرعي:", 0)
        self.lbl_discount = self._total_row(totals_frame, "الخصم:", 1)
        self.lbl_tax = self._total_row(totals_frame, "الضريبة:", 2)
        self.lbl_total = self._total_row(totals_frame, "الإجمالي:", 3, bold=True, size=15)

        sep2 = ctk.CTkFrame(parent, height=1, fg_color="gray60")
        sep2.grid(row=4, column=0, sticky="ew", padx=12, pady=6)

        # ── الخصم ──
        disc_frame = ctk.CTkFrame(parent, fg_color="transparent")
        disc_frame.grid(row=5, column=0, sticky="ew", padx=12, pady=4)
        ctk.CTkLabel(disc_frame, text="خصم إضافي:",
                     font=ctk.CTkFont(size=12)).pack(side="right")
        self.discount_var = ctk.StringVar(value="0")
        self.discount_var.trace("w", lambda *a: self._recalculate())
        ctk.CTkEntry(disc_frame, textvariable=self.discount_var,
                     width=80, height=32, justify="center").pack(side="right", padx=4)
        self.disc_type_var = ctk.StringVar(value="مبلغ")
        ctk.CTkOptionMenu(disc_frame, values=["مبلغ", "نسبة %"],
                          variable=self.disc_type_var, width=80,
                          command=lambda v: self._recalculate()).pack(side="right", padx=4)

        # ── الضريبة ──
        tax_frame = ctk.CTkFrame(parent, fg_color="transparent")
        tax_frame.grid(row=6, column=0, sticky="ew", padx=12, pady=4)
        ctk.CTkLabel(tax_frame, text="ضريبة %:",
                     font=ctk.CTkFont(size=12)).pack(side="right")
        self.tax_var = ctk.StringVar(value=get_setting("tax_rate", "0"))
        self.tax_var.trace("w", lambda *a: self._recalculate())
        ctk.CTkEntry(tax_frame, textvariable=self.tax_var,
                     width=80, height=32, justify="center").pack(side="right", padx=4)

        sep3 = ctk.CTkFrame(parent, height=1, fg_color="gray60")
        sep3.grid(row=7, column=0, sticky="ew", padx=12, pady=6)

        # ── اختيار طريقة الإرسال ──
        mode_frame = ctk.CTkFrame(parent, fg_color=("gray90", "#1e293b"))
        mode_frame.grid(row=8, column=0, sticky="ew", padx=12, pady=4)
        ctk.CTkLabel(mode_frame, text="طريقة إتمام البيع:",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(
            anchor="e", padx=10, pady=(8, 4))
        self.sale_mode_var = ctk.StringVar(value="send_cashier")
        ctk.CTkRadioButton(mode_frame, text="إرسال للكاشير  [Shift+S]",
                            variable=self.sale_mode_var,
                            value="send_cashier").pack(anchor="e", padx=16, pady=2)
        ctk.CTkRadioButton(mode_frame, text="إتمام مباشر  [Shift+W]",
                            variable=self.sale_mode_var,
                            value="direct").pack(anchor="e", padx=16, pady=(2, 8))

        # ── المبلغ المدفوع (للإتمام المباشر) ──
        self.direct_pay_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.direct_pay_frame.grid(row=9, column=0, sticky="ew", padx=12, pady=2)
        ctk.CTkLabel(self.direct_pay_frame, text="المبلغ المدفوع:",
                     font=ctk.CTkFont(size=12)).pack(side="right")
        self.paid_var = ctk.StringVar(value="0")
        self.paid_var.trace("w", lambda *a: self._update_change())
        ctk.CTkEntry(self.direct_pay_frame, textvariable=self.paid_var,
                     width=120, height=36, justify="center",
                     font=ctk.CTkFont(size=14)).pack(side="right", padx=4)

        # ── طريقة الدفع ──
        pay_method_frame = ctk.CTkFrame(parent, fg_color="transparent")
        pay_method_frame.grid(row=10, column=0, sticky="ew", padx=12, pady=2)
        ctk.CTkLabel(pay_method_frame, text="طريقة الدفع:",
                     font=ctk.CTkFont(size=12)).pack(side="right")
        self.payment_var = ctk.StringVar(value="كاش")
        ctk.CTkOptionMenu(pay_method_frame, values=["كاش", "بطاقة", "مختلط"],
                          variable=self.payment_var, width=120).pack(side="right", padx=4)

        # ── الباقي ──
        change_frame = ctk.CTkFrame(parent, fg_color="transparent")
        change_frame.grid(row=11, column=0, sticky="ew", padx=16, pady=4)
        change_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(change_frame, text="الباقي:",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="e")
        self.change_label = ctk.CTkLabel(change_frame, text="0.00",
                                          font=ctk.CTkFont(size=18, weight="bold"),
                                          text_color="#059669")
        self.change_label.grid(row=0, column=1, sticky="w", padx=8)

        # ── زر الإتمام ──
        self.confirm_btn = ctk.CTkButton(
            parent, text="✅ إتمام الفاتورة", height=52,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#10b981", hover_color="#059669",
            command=self._confirm_sale)
        self.confirm_btn.grid(row=12, column=0, sticky="ew", padx=12, pady=(12, 16))

        self.last_sale = None
        self.sale_mode_var.trace("w", lambda *a: self._on_mode_change())
        self._on_mode_change()

    def _on_mode_change(self):
        mode = self.sale_mode_var.get()
        if mode == "direct":
            self.direct_pay_frame.grid()
            self.confirm_btn.configure(text="✅ إتمام البيع مباشرة  [Shift+W]",
                                        fg_color="#2563eb", hover_color="#1d4ed8")
        else:
            self.direct_pay_frame.grid_remove()
            self.confirm_btn.configure(text="📤 إرسال للكاشير  [Shift+S]",
                                        fg_color="#10b981", hover_color="#059669")

    def _total_row(self, parent, label, row, bold=False, size=12):
        ctk.CTkLabel(parent, text=label,
                     font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"),
                     anchor="e").grid(row=row, column=0, sticky="e", pady=3)
        lbl = ctk.CTkLabel(parent, text="0.00",
                            font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"),
                            anchor="w")
        lbl.grid(row=row, column=1, sticky="w", padx=8, pady=3)
        return lbl

    def _on_customer_change(self, value):
        for name, cid in self.customer_data:
            if name == value:
                self.selected_customer = cid
                break

    def _scan_barcode(self, event=None):
        barcode = self.barcode_var.get().strip()
        if not barcode:
            return
        med = get_medicine_by_barcode(barcode)
        if med:
            self._add_to_cart(med)
            self.barcode_var.set("")
        else:
            messagebox.showwarning("تحذير", f"لا يوجد دواء بالباركود: {barcode}", parent=self)
            self.barcode_var.set("")
        # دائماً نعيد التركيز لحقل الباركود بعد المسح
        self.after(50, lambda: self.barcode_entry.focus())

    def _search_medicines(self):
        q = self.med_search_var.get().strip()
        self._load_inventory_tree(q if len(q) >= 1 else None)

    def _load_inventory_tree(self, query=None):
        self.meds_tree.delete(*self.meds_tree.get_children())
        self.meds_tree_data = []
        meds = get_all_medicines(search=query or None)[:200]
        for _i_m, m in enumerate(meds):
            _row_tag = "evenrow" if _i_m % 2 == 0 else "oddrow"
            qty = m.get("quantity", 0)
            tag = "ok" if qty > m.get("min_quantity", 5) else ("low" if qty > 0 else "out")
            self.meds_tree.insert("", "end", iid=str(m["id"]), tags=(tag,), values=(
                m["name"],
                m.get("barcode") or "",
                qty,
                f"{m.get('selling_price', 0):.2f}",
            ))
            self.meds_tree_data.append(m)
        self.meds_tree.tag_configure("low", foreground="#b45309")
        self.meds_tree.tag_configure("out", foreground="#dc2626")

    def _select_from_inventory(self, event=None):
        sel = self.meds_tree.selection()
        if not sel:
            return
        med_id = int(sel[0])
        med = next((item for item in self.meds_tree_data if item["id"] == med_id), None)
        if med:
            self._add_to_cart(med)
            self.med_search_var.set("")
            self._load_inventory_tree()

    def _add_to_cart(self, med):
        if med.get("quantity", 0) <= 0:
            messagebox.showwarning("تحذير",
                                   f"الدواء '{med['name']}' غير متوفر في المخزون", parent=self)
            return
        for item in self.cart_items:
            if item["medicine_id"] == med["id"]:
                if item["quantity"] >= med["quantity"]:
                    messagebox.showwarning("تحذير", "الكمية المطلوبة تتجاوز المتاح في المخزون",
                                           parent=self)
                    return
                item["quantity"] += 1
                item["total"] = round(item["quantity"] * item["unit_price"] - item.get("discount", 0), 2)
                self._refresh_cart()
                self._select_last_cart_row()
                return
        self.cart_items.append({
            "medicine_id": med["id"],
            "name": med["name"],
            "unit": med.get("unit", ""),
            "unit_price": med.get("selling_price", 0),
            "quantity": 1,
            "discount": 0,
            "total": med.get("selling_price", 0),
            "available": med.get("quantity", 0),
        })
        self._refresh_cart()
        self._select_last_cart_row()

    def _refresh_cart(self):
        self.cart_tree.delete(*self.cart_tree.get_children())
        for _i_item, item in enumerate(self.cart_items):
            _row_tag = "evenrow" if _i_item % 2 == 0 else "oddrow"
            self.cart_tree.insert("", "end", tags=(_row_tag,), values=(
                item["name"],
                f"{item['unit_price']:.2f}",
                item["quantity"],
                f"{item.get('discount', 0):.2f}",
                f"{item['total']:.2f}",
            ))
        self._recalculate()

    def _select_last_cart_row(self):
        items = self.cart_tree.get_children()
        if items:
            last = items[-1]
            self.cart_tree.selection_set(last)
            self.cart_tree.see(last)
            self.cart_tree.focus_set()
            self.cart_tree.focus(last)
            return last
        return None

    def _recalculate(self):
        subtotal = sum(item["total"] for item in self.cart_items)
        try:
            disc_val = float(self.discount_var.get() or 0)
        except ValueError:
            disc_val = 0
        disc_type = self.disc_type_var.get()
        if disc_type == "نسبة %":
            discount = round(subtotal * disc_val / 100, 2)
        else:
            discount = disc_val
        discount = min(discount, subtotal)

        after_disc = subtotal - discount
        try:
            tax_pct = float(self.tax_var.get() or 0)
        except ValueError:
            tax_pct = 0
        tax = round(after_disc * tax_pct / 100, 2)
        total = round(after_disc + tax, 2)

        cur = get_setting("currency", "ج.م")
        self.lbl_subtotal.configure(text=f"{subtotal:.2f} {cur}")
        self.lbl_discount.configure(text=f"{discount:.2f} {cur}")
        self.lbl_tax.configure(text=f"{tax:.2f} {cur}")
        self.lbl_total.configure(text=f"{total:.2f} {cur}")
        self._current_total = total
        self._current_subtotal = subtotal
        self._current_discount = discount
        self._current_tax = tax

        try:
            current_paid = float(self.paid_var.get() or 0)
            if current_paid == 0 or abs(current_paid - total) < 0.01:
                self.paid_var.set(f"{total:.2f}")
        except ValueError:
            self.paid_var.set(f"{total:.2f}")
        self._update_change()

    def _update_change(self):
        try:
            paid = float(self.paid_var.get() or 0)
        except ValueError:
            paid = 0
        total = getattr(self, "_current_total", 0)
        change = round(paid - total, 2)
        self.change_label.configure(
            text=f"{change:.2f}",
            text_color="#059669" if change >= 0 else "#dc2626")

    def _remove_item(self):
        sel = self.cart_tree.selection()
        if sel:
            idx = self.cart_tree.index(sel[0])
        elif self.cart_items:
            idx = len(self.cart_items) - 1
        else:
            return
        self.cart_items.pop(idx)
        self._refresh_cart()

    def _is_typing_in_entry(self, widget):
        if widget is None:
            return False
        cls = widget.winfo_class().lower()
        return "entry" in cls or "text" in cls

    def _on_global_keypress(self, event=None):
        """اختصارات لوحة المفاتيح - تعمل فقط عندما تكون شاشة POS نشطة"""
        if not self.winfo_exists():
            return
        # تأكد أن الـ frame نفسه موجود (لم يُحذف بعد الانتقال لشاشة أخرى)
        try:
            self.winfo_toplevel()
        except Exception:
            return

        widget = getattr(event, 'widget', None)
        keysym = (event.keysym or "").lower()

        # Shift+W → إتمام مباشر أو إرسال للكاشير (حسب الوضع المختار)
        if keysym in ["w", "arabic_tah"] and (event.state & 0x0001):
            self._confirm_sale()
            return "break"

        # Shift+S → إرسال للكاشير دائماً
        if keysym in ["s", "arabic_seen"] and (event.state & 0x0001):
            self.sale_mode_var.set("send_cashier")
            self._send_to_cashier()
            return "break"

        # + أو NumPad+ → تعديل الكمية (لا يعمل عند الكتابة في حقول نصية)
        if event.char == "+" or keysym == "kp_add":
            if not self._is_typing_in_entry(widget):
                if self.cart_items:
                    if not self.cart_tree.selection():
                        self._select_last_cart_row()
                    self._edit_qty()
                return "break"

        # Delete → حذف الصنف المحدد فقط (لا يعمل في حقول نصية)
        if keysym == "delete":
            if not self._is_typing_in_entry(widget):
                # تنفّذ فقط إذا كان التركيز على سلة المشتريات
                focused = self.focus_get() if hasattr(self, "focus_get") else widget
                try:
                    focused_cls = focused.winfo_class().lower() if focused else ""
                except Exception:
                    focused_cls = ""
                if "treeview" in focused_cls or widget == self.cart_tree:
                    self._remove_item()

    def _edit_qty(self):
        sel = self.cart_tree.selection()
        if not sel:
            return
        idx = self.cart_tree.index(sel[0])
        item = self.cart_items[idx]

        dlg = ctk.CTkToplevel(self)
        dlg.title("تعديل الكمية والخصم")
        dlg.geometry("300x260")
        dlg.grab_set()
        dlg.resizable(False, False)

        ctk.CTkLabel(dlg, text=f"الدواء: {item['name']}",
                     wraplength=260, font=ctk.CTkFont(size=13)).pack(pady=(16, 8))

        ctk.CTkLabel(dlg, text="الكمية:").pack()
        qty_var = ctk.StringVar(value=str(item["quantity"]))
        qty_entry = ctk.CTkEntry(dlg, textvariable=qty_var, height=36,
                                  justify="center", font=ctk.CTkFont(size=16))
        qty_entry.pack(padx=30, fill="x")

        ctk.CTkLabel(dlg, text="خصم الصنف (مبلغ):").pack(pady=(8, 0))
        disc_var = ctk.StringVar(value=str(item.get("discount", 0)))
        ctk.CTkEntry(dlg, textvariable=disc_var, height=36,
                      justify="center").pack(padx=30, fill="x")

        def confirm():
            try:
                new_qty = int(qty_var.get())
                new_disc = float(disc_var.get() or 0)
                if new_qty <= 0:
                    self.cart_items.pop(idx)
                elif new_qty > item["available"]:
                    messagebox.showwarning("تحذير",
                                           f"المتاح فقط: {item['available']}", parent=dlg)
                    return
                else:
                    item["quantity"] = new_qty
                    item["discount"] = max(0, new_disc)
                    item["total"] = round(new_qty * item["unit_price"] - item["discount"], 2)
                self._refresh_cart()
                dlg.destroy()
            except ValueError:
                messagebox.showerror("خطأ", "يرجى إدخال أرقام صحيحة", parent=dlg)

        ctk.CTkButton(dlg, text="تأكيد", command=confirm).pack(pady=12)
        dlg.bind("<Return>", lambda e: confirm())
        qty_entry.focus_set()
        qty_entry.select_range(0, "end")

    def _clear_cart(self):
        if self.cart_items and messagebox.askyesno("تأكيد", "مسح جميع الأصناف؟", parent=self):
            self.cart_items = []
            self._refresh_cart()

    def _confirm_sale(self):
        if not self.cart_items:
            messagebox.showwarning("تحذير", "السلة فارغة", parent=self)
            return
        mode = self.sale_mode_var.get()
        if mode == "send_cashier":
            self._send_to_cashier()
        else:
            self._complete_direct_sale()

    def _send_to_cashier(self):
        if not self.cart_items:
            messagebox.showwarning("تحذير", "السلة فارغة", parent=self)
            return
        user = get_current_user()
        sale_data = self._build_sale_data(user["id"])
        items = self._build_items()
        try:
            sale_id = create_pending_sale(sale_data, items)
            from models.sale import get_sale_by_id
            sale_record, _ = get_sale_by_id(sale_id)
            inv_num = sale_record.get("invoice_number", "") if sale_record else ""
            messagebox.showinfo("تم الإرسال",
                                f"✅ تم إرسال الفاتورة {inv_num} إلى الكاشير", parent=self)
            self._new_invoice()
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ: {e}", parent=self)

    def _complete_direct_sale(self):
        try:
            paid = float(self.paid_var.get() or 0)
        except ValueError:
            messagebox.showwarning("تحذير", "يرجى إدخال مبلغ مدفوع صحيح", parent=self)
            return
        total = getattr(self, "_current_total", 0)
        if round(paid - total, 2) < 0:
            messagebox.showwarning("تحذير", "المبلغ المدفوع أقل من الإجمالي", parent=self)
            return

        payment_map = {"كاش": "cash", "بطاقة": "card", "مختلط": "mixed"}
        user = get_current_user()
        sale_data = self._build_sale_data(user["id"])
        sale_data["paid_amount"] = paid
        sale_data["change_amount"] = round(paid - total, 2)
        sale_data["payment_method"] = payment_map.get(self.payment_var.get(), "cash")
        items = self._build_items()
        try:
            sale_id = create_sale(sale_data, items)
            from models.sale import get_sale_by_id
            sale_record, sale_items = get_sale_by_id(sale_id)
            self.last_sale = (sale_record, sale_items)
            if messagebox.askyesno("طباعة", "هل تريد طباعة الفاتورة؟", parent=self):
                self._do_print(sale_record, sale_items)
            messagebox.showinfo("تم", "✅ تم إتمام الفاتورة بنجاح", parent=self)
            self._new_invoice()
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ: {e}", parent=self)

    def _build_sale_data(self, user_id):
        return {
            "customer_id": self.selected_customer,
            "user_id": user_id,
            "subtotal": getattr(self, "_current_subtotal", 0),
            "discount": getattr(self, "_current_discount", 0),
            "discount_type": "percent" if self.disc_type_var.get() == "نسبة %" else "amount",
            "tax": getattr(self, "_current_tax", 0),
            "total": getattr(self, "_current_total", 0),
        }

    def _build_items(self):
        return [{"medicine_id": i["medicine_id"], "quantity": i["quantity"],
                  "unit_price": i["unit_price"], "discount": i.get("discount", 0),
                  "total": i["total"]} for i in self.cart_items]

    def _do_print(self, sale, items):
        try:
            path = generate_receipt_pdf(sale, items)
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("خطأ", f"خطأ في الطباعة: {e}", parent=self)

    def _new_invoice(self):
        self.cart_items = []
        self.discount_var.set("0")
        self.tax_var.set(get_setting("tax_rate", "0"))
        self.customer_var.set("عميل نقدي")
        self.selected_customer = None
        self.paid_var.set("0")
        self._refresh_cart()
        self._load_inventory_tree()
        self.after(50, lambda: self.barcode_entry.focus())
