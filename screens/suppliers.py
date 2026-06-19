import customtkinter as ctk
from tkinter import messagebox, ttk
from models.supplier import get_all_suppliers, get_supplier_by_id, add_supplier, update_supplier, delete_supplier


class SuppliersScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        ctk.CTkLabel(toolbar, text="إدارة الموردين",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="right")
        btn_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_frame.pack(side="left")
        ctk.CTkButton(btn_frame, text="➕ مورد جديد", width=120, command=self._add_dialog).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="✏️ تعديل", width=100, fg_color="#059669",
                      command=self._edit_dialog).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="🗑 حذف", width=100, fg_color="#dc2626",
                      command=self._delete).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="🔄 تحديث", width=100, fg_color="gray",
                      command=self._load).pack(side="left", padx=4)

        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *a: self._load())
        ctk.CTkEntry(filter_frame, textvariable=self.search_var,
                     placeholder_text="🔍 بحث...", width=260, height=36).pack(side="right", padx=4)

        table_frame = ctk.CTkFrame(self, corner_radius=10)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 16))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "name", "contact", "phone", "email", "address", "created")
        labels = {"id": "#", "name": "الاسم", "contact": "المسؤول",
                  "phone": "الهاتف", "email": "البريد", "address": "العنوان", "created": "التاريخ"}
        widths = {"id": 40, "name": 160, "contact": 120, "phone": 110,
                  "email": 150, "address": 150, "created": 100}

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
        suppliers = get_all_suppliers(search=self.search_var.get().strip() or None)
        self.tree.delete(*self.tree.get_children())
        for _i_s, s in enumerate(suppliers):
            _row_tag = "evenrow" if _i_s % 2 == 0 else "oddrow"
            self.tree.insert("", "end", tags=(_row_tag,), iid=str(s["id"]), values=(
                s["id"], s["name"], s.get("contact_person", ""), s.get("phone", ""),
                s.get("email", ""), s.get("address", ""), s.get("created_at", "")[:10],
            ))
        self.status_label.configure(text=f"إجمالي الموردين: {len(suppliers)}")

    def _get_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("تحذير", "يرجى اختيار مورد أولاً")
            return None
        return int(sel[0])

    def _add_dialog(self):
        SupplierFormDialog(self, None, on_save=self._load)

    def _edit_dialog(self):
        sid = self._get_selected()
        if not sid:
            return
        s = get_supplier_by_id(sid)
        SupplierFormDialog(self, s, on_save=self._load)

    def _delete(self):
        sid = self._get_selected()
        if not sid:
            return
        s = get_supplier_by_id(sid)
        if messagebox.askyesno("تأكيد", f"حذف المورد: {s['name']}؟"):
            delete_supplier(sid)
            self._load()


class SupplierFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, supplier_data, on_save):
        super().__init__(parent)
        self.data = supplier_data
        self.on_save = on_save
        self.title("تعديل مورد" if supplier_data else "إضافة مورد")
        self.geometry("480x420")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        if supplier_data:
            self._populate()

    def _build(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=20)
        frame.grid_columnconfigure((0, 1), weight=1)

        fields = [
            ("الاسم *", "name", 0, 0, 2),
            ("المسؤول", "contact_person", 1, 0, 1),
            ("الهاتف", "phone", 1, 1, 1),
            ("البريد الإلكتروني", "email", 2, 0, 1),
            ("العنوان", "address", 2, 1, 1),
        ]
        self.vars = {}
        for label, key, row, col, span in fields:
            ctk.CTkLabel(frame, text=label, anchor="e").grid(
                row=row * 2, column=col, columnspan=span, sticky="e", padx=6, pady=(8, 2))
            var = ctk.StringVar()
            ctk.CTkEntry(frame, textvariable=var, height=36, justify="right").grid(
                row=row * 2 + 1, column=col, columnspan=span, sticky="ew", padx=6)
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
        for key in ("name", "contact_person", "phone", "email", "address"):
            self.vars[key].set(self.data.get(key, "") or "")
        if self.data.get("notes"):
            self.notes_text.insert("1.0", self.data["notes"])

    def _save(self):
        name = self.vars["name"].get().strip()
        if not name:
            messagebox.showerror("خطأ", "الاسم مطلوب", parent=self)
            return
        data = {k: self.vars[k].get().strip() for k in ("name", "contact_person", "phone", "email", "address")}
        data["notes"] = self.notes_text.get("1.0", "end").strip()
        if self.data:
            update_supplier(self.data["id"], data)
        else:
            add_supplier(data)
        self.on_save()
        self.destroy()
