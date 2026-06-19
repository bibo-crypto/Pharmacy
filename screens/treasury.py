import customtkinter as ctk
from tkinter import messagebox, ttk
from models.treasury import (get_treasury_transactions, add_treasury_transaction,
                              open_shift, close_shift, get_open_shift, get_all_shifts,
                              get_treasury_balance, add_expense, get_all_expenses)
from utils.auth import get_current_user
from utils.helpers import get_setting, format_currency
from datetime import datetime


class TreasuryScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        tabs = ctk.CTkTabview(self)
        tabs.grid(row=0, column=0, sticky="nsew", padx=20, pady=16)

        tab_overview = tabs.add("نظرة عامة")
        tab_shift = tabs.add("إدارة الوردية")
        tab_cash = tabs.add("حركات الخزينة")
        tab_expenses = tabs.add("المصروفات")
        tab_shifts_hist = tabs.add("سجل الورديات")

        self._build_overview(tab_overview)
        self._build_shift_tab(tab_shift)
        self._build_cash_tab(tab_cash)
        self._build_expenses_tab(tab_expenses)
        self._build_shifts_history(tab_shifts_hist)

    def _build_overview(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        balance = get_treasury_balance()
        cur = get_setting("currency", "ج.م")
        shift = get_open_shift()

        cards = ctk.CTkFrame(parent, fg_color="transparent")
        cards.pack(fill="x", pady=16)
        for i in range(3):
            cards.grid_columnconfigure(i, weight=1)

        self._stat_card(cards, "💰", "رصيد الخزينة", format_currency(balance), "#059669", 0)
        shift_status = f"مفتوحة - {shift.get('full_name','')}" if shift else "لا توجد وردية مفتوحة"
        self._stat_card(cards, "📋", "حالة الوردية", shift_status, "#2563eb" if shift else "gray", 1)

        from database.connection import get_connection
        conn = get_connection()
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT SUM(total) FROM sales WHERE status='completed' AND date(sale_date)=?", (today,))
        today_sales = c.fetchone()[0] or 0
        conn.close()
        self._stat_card(cards, "📊", "مبيعات اليوم", format_currency(today_sales), "#7c3aed", 2)

        recent_frame = ctk.CTkFrame(parent, corner_radius=10)
        recent_frame.pack(fill="both", expand=True, padx=4, pady=8)
        ctk.CTkLabel(recent_frame, text="آخر حركات الخزينة",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="e", padx=16, pady=(12, 6))
        cols = ("type", "amount", "desc", "user", "date")
        labels = {"type": "النوع", "amount": "المبلغ", "desc": "البيان",
                  "user": "المستخدم", "date": "التاريخ"}
        tree = ttk.Treeview(recent_frame, columns=cols, show="headings", height=10)
        for _i_col, col in enumerate(cols):
            _row_tag = "evenrow" if _i_col % 2 == 0 else "oddrow"
            tree.heading(col, text=labels[col])
            tree.column(col, width=130, anchor="center")
        tree.column("desc", width=200)
        transactions = get_treasury_transactions(limit=30)
        for _i_t, t in enumerate(transactions):
            _row_tag = "evenrow" if _i_t % 2 == 0 else "oddrow"
            tree.insert("", "end", tags=(_row_tag,), values=(
                t.get("transaction_type", ""),
                f"{t.get('amount', 0):.2f} {cur}",
                t.get("description", ""),
                t.get("user_name", ""),
                t.get("transaction_date", "")[:16],
            ))
        tree.pack(fill="both", expand=True, padx=8, pady=(0, 12))

    def _stat_card(self, parent, icon, label, value, color, col):
        card = ctk.CTkFrame(parent, corner_radius=12, height=100)
        card.grid(row=0, column=col, padx=8, sticky="ew")
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=26)).grid(row=0, column=0, pady=(12, 2))
        ctk.CTkLabel(card, text=str(value), font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=color, wraplength=180).grid(row=1, column=0)
        ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=11),
                     text_color="gray").grid(row=2, column=0, pady=(0, 8))

    def _build_shift_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)

        shift = get_open_shift()
        self.shift_status_label = ctk.CTkLabel(
            parent,
            text=f"الوردية الحالية: {'مفتوحة منذ ' + (shift.get('opened_at','')[:16] if shift else '')} | المسؤول: {shift.get('full_name','') if shift else '—'}" if shift else "لا توجد وردية مفتوحة حالياً",
            font=ctk.CTkFont(size=13),
            text_color="#059669" if shift else "gray"
        )
        self.shift_status_label.pack(pady=20)

        open_frame = ctk.CTkFrame(parent, corner_radius=10, width=400)
        open_frame.pack(pady=12)

        ctk.CTkLabel(open_frame, text="فتح وردية جديدة",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(16, 8))
        balance_frame = ctk.CTkFrame(open_frame, fg_color="transparent")
        balance_frame.pack(padx=40, fill="x")
        ctk.CTkLabel(balance_frame, text="رصيد الافتتاح:").pack(side="right")
        self.opening_balance_var = ctk.StringVar(value="0")
        ctk.CTkEntry(balance_frame, textvariable=self.opening_balance_var,
                     width=120, height=36, justify="center").pack(side="left", padx=8)
        ctk.CTkButton(open_frame, text="✅ فتح الوردية", width=160,
                      fg_color="#059669", command=self._open_shift).pack(pady=12)

        close_frame = ctk.CTkFrame(parent, corner_radius=10, width=400)
        close_frame.pack(pady=12)
        ctk.CTkLabel(close_frame, text="إغلاق الوردية",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(16, 8))
        closing_frame = ctk.CTkFrame(close_frame, fg_color="transparent")
        closing_frame.pack(padx=40, fill="x")
        ctk.CTkLabel(closing_frame, text="رصيد الإغلاق:").pack(side="right")
        self.closing_balance_var = ctk.StringVar(value="0")
        ctk.CTkEntry(closing_frame, textvariable=self.closing_balance_var,
                     width=120, height=36, justify="center").pack(side="left", padx=8)
        ctk.CTkLabel(close_frame, text="ملاحظات:").pack()
        self.shift_notes_var = ctk.StringVar()
        ctk.CTkEntry(close_frame, textvariable=self.shift_notes_var,
                     width=280, height=36).pack(pady=(4, 8))
        ctk.CTkButton(close_frame, text="🔒 إغلاق الوردية", width=160,
                      fg_color="#dc2626", command=self._close_shift).pack(pady=12)

    def _open_shift(self):
        if get_open_shift():
            messagebox.showwarning("تحذير", "يوجد وردية مفتوحة بالفعل", parent=self)
            return
        try:
            bal = float(self.opening_balance_var.get() or 0)
        except ValueError:
            bal = 0
        user = get_current_user()
        open_shift(user["id"], bal)
        messagebox.showinfo("تم", "تم فتح الوردية بنجاح", parent=self)
        self.refresh()

    def _close_shift(self):
        shift = get_open_shift()
        if not shift:
            messagebox.showwarning("تحذير", "لا توجد وردية مفتوحة", parent=self)
            return
        try:
            bal = float(self.closing_balance_var.get() or 0)
        except ValueError:
            bal = 0
        user = get_current_user()
        close_shift(shift["id"], user["id"], bal, self.shift_notes_var.get())
        messagebox.showinfo("تم", "تم إغلاق الوردية بنجاح", parent=self)
        self.refresh()

    def _build_cash_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        action_frame = ctk.CTkFrame(parent, corner_radius=10)
        action_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=8)
        action_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(action_frame, text="إضافة حركة خزينة",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=3, padx=16, pady=(12, 8))

        ctk.CTkLabel(action_frame, text="النوع:", anchor="e").grid(row=1, column=2, sticky="e", padx=8)
        self.cash_type_var = ctk.StringVar(value="إيراد")
        ctk.CTkOptionMenu(action_frame, values=["إيراد", "مصروف"],
                          variable=self.cash_type_var, width=120).grid(row=1, column=1, padx=8)

        ctk.CTkLabel(action_frame, text="المبلغ:", anchor="e").grid(row=2, column=2, sticky="e", padx=8, pady=4)
        self.cash_amount_var = ctk.StringVar(value="0")
        ctk.CTkEntry(action_frame, textvariable=self.cash_amount_var,
                     width=120, height=36, justify="center").grid(row=2, column=1, padx=8)

        ctk.CTkLabel(action_frame, text="البيان:", anchor="e").grid(row=3, column=2, sticky="e", padx=8)
        self.cash_desc_var = ctk.StringVar()
        ctk.CTkEntry(action_frame, textvariable=self.cash_desc_var,
                     width=220, height=36).grid(row=3, column=1, columnspan=2, padx=8, pady=4)

        ctk.CTkButton(action_frame, text="➕ إضافة", width=120,
                      command=self._add_cash_transaction).grid(row=4, column=0, columnspan=3, pady=12)

        table_frame = ctk.CTkFrame(parent, corner_radius=8)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=4)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cur = get_setting("currency", "ج.م")
        cols = ("type", "amount", "desc", "user", "date")
        labels = {"type": "النوع", "amount": f"المبلغ ({cur})", "desc": "البيان",
                  "user": "المستخدم", "date": "التاريخ"}
        self.cash_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        ctk.configure_treeview(self.cash_tree)
        for col in cols:
            self.cash_tree.heading(col, text=labels[col])
            self.cash_tree.column(col, width=130, anchor="center")
        self.cash_tree.column("desc", width=220)
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.cash_tree.yview)
        self.cash_tree.configure(yscrollcommand=vsb.set)
        self.cash_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._load_cash_transactions()

    def _load_cash_transactions(self):
        cur = get_setting("currency", "ج.م")
        transactions = get_treasury_transactions()
        self.cash_tree.delete(*self.cash_tree.get_children())
        for _i_t, t in enumerate(transactions):
            _row_tag = "evenrow" if _i_t % 2 == 0 else "oddrow"
            self.cash_tree.insert("", "end", tags=(_row_tag,), values=(
                t.get("transaction_type", ""),
                f"{t.get('amount', 0):.2f}",
                t.get("description", ""),
                t.get("user_name", ""),
                t.get("transaction_date", "")[:16],
            ))

    def _add_cash_transaction(self):
        t_type_map = {"إيراد": "income", "مصروف": "expense"}
        t_type = t_type_map.get(self.cash_type_var.get(), "income")
        try:
            amount = float(self.cash_amount_var.get() or 0)
        except ValueError:
            amount = 0
        if amount <= 0:
            messagebox.showwarning("تحذير", "يرجى إدخال مبلغ صحيح", parent=self)
            return
        desc = self.cash_desc_var.get().strip() or "حركة يدوية"
        user = get_current_user()
        add_treasury_transaction(t_type, amount, desc, user["id"])
        messagebox.showinfo("تم", "تم إضافة الحركة بنجاح", parent=self)
        self.cash_amount_var.set("0")
        self.cash_desc_var.set("")
        self._load_cash_transactions()

    def _build_expenses_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        form = ctk.CTkFrame(parent, corner_radius=10)
        form.grid(row=0, column=0, sticky="ew", padx=4, pady=8)
        form.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(form, text="إضافة مصروف جديد",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=3, padx=16, pady=(12, 8))

        ctk.CTkLabel(form, text="العنوان *:", anchor="e").grid(row=1, column=2, sticky="e", padx=8)
        self.exp_title_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.exp_title_var, width=200, height=36).grid(
            row=1, column=1, padx=8)

        ctk.CTkLabel(form, text="المبلغ *:", anchor="e").grid(row=2, column=2, sticky="e", padx=8, pady=4)
        self.exp_amount_var = ctk.StringVar(value="0")
        ctk.CTkEntry(form, textvariable=self.exp_amount_var, width=120, height=36,
                     justify="center").grid(row=2, column=1, padx=8)

        ctk.CTkLabel(form, text="الفئة:", anchor="e").grid(row=1, column=0, sticky="e", padx=8)
        self.exp_cat_var = ctk.StringVar(value="عام")
        ctk.CTkOptionMenu(form, values=["عام", "إيجار", "رواتب", "كهرباء", "ماء",
                                         "صيانة", "تسويق", "أخرى"],
                          variable=self.exp_cat_var, width=130).grid(row=1, column=0, sticky="w", padx=8)

        ctk.CTkLabel(form, text="ملاحظات:", anchor="e").grid(row=3, column=2, sticky="e", padx=8)
        self.exp_notes_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self.exp_notes_var, width=300, height=36).grid(
            row=3, column=1, columnspan=2, padx=8, pady=4)

        ctk.CTkButton(form, text="➕ إضافة مصروف", width=160,
                      fg_color="#dc2626", command=self._add_expense).grid(
            row=4, column=0, columnspan=3, pady=12)

        table_frame = ctk.CTkFrame(parent, corner_radius=8)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=4)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "title", "amount", "category", "user", "date")
        labels = {"id": "#", "title": "العنوان", "amount": "المبلغ",
                  "category": "الفئة", "user": "المستخدم", "date": "التاريخ"}
        self.exp_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        ctk.configure_treeview(self.exp_tree)
        for col in cols:
            self.exp_tree.heading(col, text=labels[col])
            self.exp_tree.column(col, width=120, anchor="center")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.exp_tree.yview)
        self.exp_tree.configure(yscrollcommand=vsb.set)
        self.exp_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self._load_expenses()

    def _add_expense(self):
        title = self.exp_title_var.get().strip()
        if not title:
            messagebox.showwarning("تحذير", "يرجى إدخال عنوان المصروف", parent=self)
            return
        try:
            amount = float(self.exp_amount_var.get() or 0)
        except ValueError:
            amount = 0
        if amount <= 0:
            messagebox.showwarning("تحذير", "يرجى إدخال مبلغ صحيح", parent=self)
            return
        user = get_current_user()
        add_expense(title, amount, self.exp_cat_var.get(), self.exp_notes_var.get(), user["id"])
        messagebox.showinfo("تم", "تم إضافة المصروف بنجاح", parent=self)
        self.exp_title_var.set("")
        self.exp_amount_var.set("0")
        self.exp_notes_var.set("")
        self._load_expenses()

    def _load_expenses(self):
        expenses = get_all_expenses()
        self.exp_tree.delete(*self.exp_tree.get_children())
        cur = get_setting("currency", "ج.م")
        for _i_e, e in enumerate(expenses):
            _row_tag = "evenrow" if _i_e % 2 == 0 else "oddrow"
            self.exp_tree.insert("", "end", tags=(_row_tag,), values=(
                e["id"], e.get("title", ""), f"{e.get('amount', 0):.2f} {cur}",
                e.get("category", ""), e.get("user_name", ""),
                e.get("expense_date", "")[:16],
            ))

    def _build_shifts_history(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        cols = ("id", "user", "opening", "closing", "sales", "expenses", "status", "opened", "closed")
        labels = {"id": "#", "user": "المستخدم", "opening": "رصيد الافتتاح",
                  "closing": "رصيد الإغلاق", "sales": "إجمالي المبيعات",
                  "expenses": "إجمالي المصروفات", "status": "الحالة",
                  "opened": "وقت الفتح", "closed": "وقت الإغلاق"}
        tree = ttk.Treeview(parent, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=labels[col])
            tree.column(col, width=100, anchor="center")
        vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        shifts = get_all_shifts()
        cur = get_setting("currency", "ج.م")
        for _i_s, s in enumerate(shifts):
            _row_tag = "evenrow" if _i_s % 2 == 0 else "oddrow"
            tree.insert("", "end", tags=(_row_tag,), values=(
                s["id"], s.get("user_name", ""),
                f"{s.get('opening_balance', 0):.2f}",
                f"{s.get('closing_balance', 0) or 0:.2f}",
                f"{s.get('total_sales', 0):.2f}",
                f"{s.get('total_expenses', 0):.2f}",
                "مفتوحة" if s.get("status") == "open" else "مغلقة",
                s.get("opened_at", "")[:16],
                (s.get("closed_at", "") or "")[:16],
            ))
        ctk.CTkButton(parent, text="🔄 تحديث", fg_color="gray",
                      command=lambda: self.refresh()).grid(row=1, column=0, pady=4)

    def refresh(self):
        for w in self.winfo_children():
            w.destroy()
        self._build()
