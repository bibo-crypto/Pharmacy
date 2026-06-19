import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
from models.medicine import (get_all_medicines, get_medicine_by_id,
                              add_medicine, update_medicine, delete_medicine,
                              get_categories, add_category)
from utils.auth import has_permission
from utils.helpers import validate_barcode, is_barcode_unique


class MedicinesScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.selected_id = None
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))

        ctk.CTkLabel(toolbar, text="إدارة الأدوية",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="right")

        btn_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_frame.pack(side="left")

        if has_permission("add_medicines"):
            ctk.CTkButton(btn_frame, text="➕ إضافة دواء", width=130,
                          command=self._add_dialog).pack(side="left", padx=4)
        if has_permission("edit_medicines"):
            ctk.CTkButton(btn_frame, text="✏️ تعديل", width=100,
                          fg_color="#059669", hover_color="#047857",
                          command=self._edit_dialog).pack(side="left", padx=4)
        if has_permission("delete_medicines"):
            ctk.CTkButton(btn_frame, text="🗑 حذف", width=100,
                          fg_color="#dc2626", hover_color="#b91c1c",
                          command=self._delete).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="🔄 تحديث", width=100,
                      fg_color="gray", command=self._load_data).pack(side="left", padx=4)

        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 6))

        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *a: self._load_data())
        ctk.CTkEntry(filter_frame, textvariable=self.search_var,
                     placeholder_text="🔍 بحث باسم أو باركود...",
                     width=260, height=36).pack(side="right", padx=4)

        cats = [("الكل", None)] + [(c["name"], c["id"]) for c in get_categories()]
        self.cat_names = [c[0] for c in cats]
        self.cat_ids = [c[1] for c in cats]
        self.cat_var = ctk.StringVar(value="الكل")
        ctk.CTkOptionMenu(filter_frame, values=self.cat_names,
                          variable=self.cat_var,
                          command=lambda v: self._load_data(),
                          width=150).pack(side="right", padx=4)

        self.low_stock_var = ctk.BooleanVar()
        ctk.CTkCheckBox(filter_frame, text="مخزون منخفض فقط",
                        variable=self.low_stock_var,
                        command=self._load_data).pack(side="right", padx=8)

        table_frame = ctk.CTkFrame(self, corner_radius=10)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        cols = ("id", "barcode", "name", "category", "quantity", "min_qty",
                "sell_price", "buy_price", "expiry", "location")
        col_labels = {
            "id": "#", "barcode": "باركود", "name": "اسم الدواء",
            "category": "الفئة", "quantity": "الكمية", "min_qty": "الحد الأدنى",
            "sell_price": "سعر البيع", "buy_price": "سعر الشراء",
            "expiry": "تاريخ الصلاحية", "location": "الموقع"
        }
        widths = {"id": 40, "barcode": 110, "name": 180, "category": 100,
                  "quantity": 65, "min_qty": 65, "sell_price": 80,
                  "buy_price": 80, "expiry": 100, "location": 80}


        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings",
                                  selectmode="browse")
        ctk.configure_treeview(self.tree)
        for col in cols:
            self.tree.heading(col, text=col_labels[col],
                              anchor="center",
                              command=lambda c=col: self._sort(c))
            self.tree.column(col, width=widths.get(col, 80), anchor="center")

        # الألوان تُضبط بواسطة configure_treeview حسب الوضع dark/light
        # لا نعيد تعريفها هنا لتجنب تجاوز إعدادات الثيم

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", lambda e: self._edit_dialog())
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.status_label = ctk.CTkLabel(self, text="", text_color="gray",
                                          font=ctk.CTkFont(size=12))
        self.status_label.grid(row=3, column=0, sticky="e", padx=20, pady=(0, 8))

        self._load_data()

    def _load_data(self):
        search = self.search_var.get().strip()
        cat_name = self.cat_var.get()
        cat_id = None
        if cat_name != "الكل":
            idx = self.cat_names.index(cat_name)
            cat_id = self.cat_ids[idx]
        low_stock = self.low_stock_var.get()

        meds = get_all_medicines(search=search or None,
                                  category_id=cat_id,
                                  low_stock=low_stock)
        self.tree.delete(*self.tree.get_children())
        for _i_m, m in enumerate(meds):
            _row_tag = "evenrow" if _i_m % 2 == 0 else "oddrow"
            qty = m.get("quantity", 0)
            min_qty = m.get("min_quantity", 5)
            tag = "out" if qty == 0 else ("low" if qty <= min_qty else "ok")
            self.tree.insert("", "end", iid=str(m["id"]), tags=(tag,), values=(
                m["id"],
                m.get("barcode") or "",
                m["name"],
                m.get("category_name") or "",
                qty,
                min_qty,
                f"{m.get('selling_price', 0):.2f}",
                f"{m.get('purchase_price', 0):.2f}",
                m.get("expiry_date") or "",
                m.get("location") or "",
            ))
        self.status_label.configure(text=f"إجمالي: {len(meds)} دواء")
        self.selected_id = None

    def _on_select(self, event):
        sel = self.tree.selection()
        self.selected_id = int(sel[0]) if sel else None

    def _sort(self, col):
        pass

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("تحذير", "يرجى اختيار دواء أولاً")
            return None
        return int(sel[0])

    def _add_dialog(self):
        MedicineFormDialog(self, None, on_save=self._load_data)

    def _edit_dialog(self):
        mid = self._get_selected_id()
        if not mid:
            return
        med = get_medicine_by_id(mid)
        MedicineFormDialog(self, med, on_save=self._load_data)

    def _delete(self):
        mid = self._get_selected_id()
        if not mid:
            return
        med = get_medicine_by_id(mid)
        if messagebox.askyesno("تأكيد الحذف",
                               f"هل أنت متأكد من حذف الدواء:\n{med['name']}؟"):
            delete_medicine(mid)
            self._load_data()
            messagebox.showinfo("تم", "تم حذف الدواء بنجاح")


class MedicineFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, medicine_data, on_save):
        super().__init__(parent)
        self.medicine_data = medicine_data
        self.on_save = on_save
        is_edit = medicine_data is not None
        self.title("تعديل دواء" if is_edit else "إضافة دواء جديد")
        self.geometry("620x680")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        if is_edit:
            self._populate()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        _si = scroll.get_inner()
        _si.grid_columnconfigure((0, 1), weight=1)

        fields = [
            ("اسم الدواء *", "name", 0, 0, 2, True),
            ("الاسم العلمي", "generic_name", 1, 0, 1, False),
            ("باركود", "barcode", 1, 1, 1, False),
        ]

        self.vars = {}
        for label, key, row, col, colspan, required in fields:
            ctk.CTkLabel(_si, text=label, anchor="e").grid(
                row=row * 2, column=col, columnspan=colspan,
                sticky="e", padx=8, pady=(8, 2))
            var = ctk.StringVar()
            entry = ctk.CTkEntry(_si, textvariable=var, height=36, justify="right")
            entry.grid(row=row * 2 + 1, column=col, columnspan=colspan,
                       sticky="ew", padx=8, pady=(0, 4))
            self.vars[key] = var

        ctk.CTkLabel(_si, text="الفئة", anchor="e").grid(
            row=4, column=0, sticky="e", padx=8, pady=(8, 2))
        cats = get_categories()
        self.cat_names = [c["name"] for c in cats]
        self.cat_ids = [c["id"] for c in cats]
        self.cat_var = ctk.StringVar(value=self.cat_names[0] if self.cat_names else "")
        ctk.CTkOptionMenu(_si, values=self.cat_names or ["—"],
                          variable=self.cat_var).grid(
            row=5, column=0, sticky="ew", padx=8, pady=(0, 4))

        ctk.CTkLabel(_si, text="الوحدة", anchor="e").grid(
            row=4, column=1, sticky="e", padx=8, pady=(8, 2))
        self.vars["unit"] = ctk.StringVar(value="قطعة")
        ctk.CTkOptionMenu(_si, values=["قطعة", "علبة", "زجاجة", "كرتون", "شريط", "حقنة", "أمبول"],
                          variable=self.vars["unit"]).grid(
            row=5, column=1, sticky="ew", padx=8, pady=(0, 4))

        num_fields = [
            ("سعر الشراء", "purchase_price", 6, 0),
            ("سعر البيع *", "selling_price", 6, 1),
            ("الكمية", "quantity", 7, 0),
            ("الحد الأدنى", "min_quantity", 7, 1),
        ]
        for label, key, row, col in num_fields:
            ctk.CTkLabel(_si, text=label, anchor="e").grid(
                row=row * 2, column=col, sticky="e", padx=8, pady=(8, 2))
            var = ctk.StringVar(value="0")
            ctk.CTkEntry(_si, textvariable=var, height=36, justify="right").grid(
                row=row * 2 + 1, column=col, sticky="ew", padx=8, pady=(0, 4))
            self.vars[key] = var

        ctk.CTkLabel(_si, text="تاريخ الصلاحية (YYYY-MM-DD)", anchor="e").grid(
            row=16, column=0, sticky="e", padx=8, pady=(8, 2))
        self.vars["expiry_date"] = ctk.StringVar()
        ctk.CTkEntry(_si, textvariable=self.vars["expiry_date"],
                     height=36, justify="right").grid(
            row=17, column=0, sticky="ew", padx=8, pady=(0, 4))

        ctk.CTkLabel(_si, text="الموقع في الصيدلية", anchor="e").grid(
            row=16, column=1, sticky="e", padx=8, pady=(8, 2))
        self.vars["location"] = ctk.StringVar()
        ctk.CTkEntry(_si, textvariable=self.vars["location"],
                     height=36, justify="right").grid(
            row=17, column=1, sticky="ew", padx=8, pady=(0, 4))

        self.prescription_var = ctk.BooleanVar()
        ctk.CTkCheckBox(_si, text="يستلزم وصفة طبية",
                        variable=self.prescription_var).grid(
            row=18, column=0, columnspan=2, sticky="e", padx=8, pady=8)

        ctk.CTkLabel(_si, text="ملاحظات", anchor="e").grid(
            row=19, column=0, columnspan=2, sticky="e", padx=8, pady=(8, 2))
        self.desc_text = ctk.CTkTextbox(_si, height=70)
        self.desc_text.grid(row=20, column=0, columnspan=2,
                             sticky="ew", padx=8, pady=(0, 12))

        btn_frame = ctk.CTkFrame(_si, fg_color="transparent")
        btn_frame.grid(row=21, column=0, columnspan=2, pady=8)
        ctk.CTkButton(btn_frame, text="💾 حفظ", width=120,
                      command=self._save).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="إلغاء", width=100,
                      fg_color="gray", command=self.destroy).pack(side="left", padx=8)

    def _populate(self):
        m = self.medicine_data
        self.vars["name"].set(m.get("name", ""))
        self.vars["generic_name"].set(m.get("generic_name", "") or "")
        self.vars["barcode"].set(m.get("barcode", "") or "")
        self.vars["unit"].set(m.get("unit", "قطعة"))
        self.vars["purchase_price"].set(str(m.get("purchase_price", 0)))
        self.vars["selling_price"].set(str(m.get("selling_price", 0)))
        self.vars["quantity"].set(str(m.get("quantity", 0)))
        self.vars["min_quantity"].set(str(m.get("min_quantity", 5)))
        self.vars["expiry_date"].set(m.get("expiry_date", "") or "")
        self.vars["location"].set(m.get("location", "") or "")
        self.prescription_var.set(bool(m.get("requires_prescription", 0)))
        if m.get("description"):
            self.desc_text.insert("1.0", m["description"])
        cat_name = m.get("category_name", "")
        if cat_name and cat_name in self.cat_names:
            self.cat_var.set(cat_name)

    def _save(self):
        name = self.vars["name"].get().strip()
        if not name:
            messagebox.showerror("خطأ", "اسم الدواء مطلوب", parent=self)
            return

        barcode = self.vars["barcode"].get().strip() or None
        if barcode:
            if not validate_barcode(barcode):
                messagebox.showerror("خطأ", "الباركود غير صحيح (4-30 حرف/رقم)", parent=self)
                return
            exclude_id = self.medicine_data["id"] if self.medicine_data else None
            if not is_barcode_unique(barcode, exclude_id):
                messagebox.showerror("خطأ", "الباركود مستخدم بالفعل", parent=self)
                return

        cat_id = None
        if self.cat_var.get() and self.cat_names:
            idx = self.cat_names.index(self.cat_var.get())
            cat_id = self.cat_ids[idx]

        try:
            data = {
                "name": name,
                "generic_name": self.vars["generic_name"].get().strip(),
                "barcode": barcode,
                "category_id": cat_id,
                "unit": self.vars["unit"].get(),
                "purchase_price": float(self.vars["purchase_price"].get() or 0),
                "selling_price": float(self.vars["selling_price"].get() or 0),
                "quantity": int(float(self.vars["quantity"].get() or 0)),
                "min_quantity": int(float(self.vars["min_quantity"].get() or 5)),
                "expiry_date": self.vars["expiry_date"].get().strip() or None,
                "location": self.vars["location"].get().strip(),
                "description": self.desc_text.get("1.0", "end").strip(),
                "requires_prescription": int(self.prescription_var.get()),
            }
        except ValueError as e:
            messagebox.showerror("خطأ", f"قيمة غير صحيحة: {e}", parent=self)
            return

        if self.medicine_data:
            update_medicine(self.medicine_data["id"], data)
            messagebox.showinfo("تم", "تم تحديث الدواء بنجاح", parent=self)
        else:
            add_medicine(data)
            messagebox.showinfo("تم", "تم إضافة الدواء بنجاح", parent=self)

        self.on_save()
        self.destroy()
