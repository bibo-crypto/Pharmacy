import customtkinter as ctk
from database.connection import get_connection
from utils.helpers import get_setting, format_currency
from utils.auth import get_current_user
from datetime import datetime


class DashboardScreen(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        user = get_current_user()
        greeting = f"مرحباً، {user['full_name']} 👋" if user else "مرحباً"
        date_str = self._format_arabic_date(datetime.now())

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        ctk.CTkLabel(header, text=greeting,
                     font=ctk.CTkFont(size=22, weight="bold")).pack(side="right")
        ctk.CTkLabel(header, text=date_str,
                     font=ctk.CTkFont(size=13), text_color="gray").pack(side="left")

        stats = self._get_stats()

        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        for i in range(4):
            cards_frame.grid_columnconfigure(i, weight=1)

        card_data = [
            ("💰", "مبيعات اليوم", format_currency(stats["today_sales"]), "#2563eb"),
            ("📦", "الأدوية", str(stats["total_medicines"]), "#059669"),
            ("⚠️", "مخزون منخفض", str(stats["low_stock"]), "#d97706"),
            ("👥", "العملاء", str(stats["total_customers"]), "#7c3aed"),
        ]
        for i, (icon, label, value, color) in enumerate(card_data):
            self._stat_card(cards_frame, icon, label, value, color, i)

        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        row2.grid_columnconfigure(0, weight=1)
        row2.grid_columnconfigure(1, weight=1)

        self._recent_sales_widget(row2, stats["recent_sales"])
        self._alerts_widget(row2, stats["low_stock_meds"], stats["expiring_meds"])

        row3 = ctk.CTkFrame(self, fg_color="transparent")
        row3.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        row3.grid_columnconfigure(0, weight=1)
        self._monthly_summary(row3, stats)

    def _stat_card(self, parent, icon, label, value, color, col):
        card = ctk.CTkFrame(parent, corner_radius=12, height=110)
        card.grid(row=0, column=col, padx=6, pady=4, sticky="ew")
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=30)).grid(row=0, column=0, pady=(16, 2))
        ctk.CTkLabel(card, text=value,
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=color).grid(row=1, column=0)
        ctk.CTkLabel(card, text=label,
                     font=ctk.CTkFont(size=12), text_color="gray").grid(row=2, column=0, pady=(0, 10))

    def _recent_sales_widget(self, parent, recent_sales):
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        ctk.CTkLabel(frame, text="آخر المبيعات",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="e", padx=16, pady=(14, 8))

        headers = ["الفاتورة", "العميل", "الإجمالي", "الوقت"]
        hf = ctk.CTkFrame(frame, fg_color=("gray85", "gray25"))
        hf.pack(fill="x", padx=10)
        for h in headers:
            ctk.CTkLabel(hf, text=h, font=ctk.CTkFont(size=11, weight="bold"),
                         width=80, anchor="center").pack(side="right", padx=4, pady=4)

        for sale in recent_sales[:8]:
            rf = ctk.CTkFrame(frame, fg_color="transparent", height=32)
            rf.pack(fill="x", padx=10)
            rf.pack_propagate(False)
            time_str = sale.get("sale_date", "")[-8:-3] if sale.get("sale_date") else ""
            for val in [sale.get("invoice_number", "")[:12],
                        (sale.get("customer_name") or "نقدي")[:12],
                        format_currency(sale.get("total", 0)),
                        time_str]:
                ctk.CTkLabel(rf, text=val, font=ctk.CTkFont(size=11),
                             width=80, anchor="center").pack(side="right", padx=4)

        if not recent_sales:
            ctk.CTkLabel(frame, text="لا توجد مبيعات اليوم",
                         text_color="gray").pack(pady=20)

    def _alerts_widget(self, parent, low_stock, expiring):
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.grid(row=0, column=1, padx=(8, 0), sticky="nsew")

        ctk.CTkLabel(frame, text="⚠️ تنبيهات",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="e", padx=16, pady=(14, 8))

        if low_stock:
            ctk.CTkLabel(frame, text="مخزون منخفض:",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#d97706").pack(anchor="e", padx=16)
            for m in low_stock[:5]:
                ctk.CTkLabel(frame,
                             text=f"  • {m['name']} ({m['quantity']} متبقي)",
                             font=ctk.CTkFont(size=11)).pack(anchor="e", padx=20)

        if expiring:
            ctk.CTkLabel(frame, text="قريبة الانتهاء:",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#dc2626").pack(anchor="e", padx=16, pady=(8, 0))
            for m in expiring[:5]:
                ctk.CTkLabel(frame,
                             text=f"  • {m['name']} ({m.get('expiry_date', '')[:10]})",
                             font=ctk.CTkFont(size=11)).pack(anchor="e", padx=20)

        if not low_stock and not expiring:
            ctk.CTkLabel(frame, text="✅ لا توجد تنبيهات",
                         text_color="green").pack(pady=30)

    def _monthly_summary(self, parent, stats):
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(frame, text="ملخص الشهر الحالي",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="e", padx=16, pady=(14, 8))

        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(0, 16))
        for i in range(4):
            inner.grid_columnconfigure(i, weight=1)

        items = [
            ("إجمالي المبيعات", format_currency(stats["month_sales"]), "#2563eb"),
            ("إجمالي المشتريات", format_currency(stats["month_purchases"]), "#dc2626"),
            ("المرتجعات", format_currency(stats["month_returns"]), "#d97706"),
            ("رصيد الخزينة", format_currency(stats["treasury_balance"]), "#059669"),
        ]
        for i, (label, value, color) in enumerate(items):
            sub = ctk.CTkFrame(inner, fg_color="transparent")
            sub.grid(row=0, column=i, padx=10)
            ctk.CTkLabel(sub, text=value,
                         font=ctk.CTkFont(size=18, weight="bold"),
                         text_color=color).pack()
            ctk.CTkLabel(sub, text=label,
                         font=ctk.CTkFont(size=11), text_color="gray").pack()

    def _format_arabic_date(self, dt):
        weekdays = {
            0: "الاثنين",
            1: "الثلاثاء",
            2: "الأربعاء",
            3: "الخميس",
            4: "الجمعة",
            5: "السبت",
            6: "الأحد",
        }
        months = {
            1: "يناير",
            2: "فبراير",
            3: "مارس",
            4: "أبريل",
            5: "مايو",
            6: "يونيو",
            7: "يوليو",
            8: "أغسطس",
            9: "سبتمبر",
            10: "أكتوبر",
            11: "نوفمبر",
            12: "ديسمبر",
        }
        return f"{weekdays[dt.weekday()]}، {dt.day:02d} {months[dt.month]} {dt.year}"

    def _get_stats(self) -> dict:
        conn = get_connection()
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        month_start = datetime.now().strftime("%Y-%m-01")

        c.execute("SELECT SUM(total) FROM sales WHERE status='completed' AND date(sale_date)=?", (today,))
        today_sales = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(*) FROM medicines WHERE is_active=1")
        total_medicines = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM medicines WHERE is_active=1 AND quantity <= min_quantity")
        low_stock = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM customers WHERE is_active=1")
        total_customers = c.fetchone()[0]

        c.execute("""
            SELECT s.invoice_number, c.name as customer_name, s.total, s.sale_date
            FROM sales s LEFT JOIN customers c ON s.customer_id=c.id
            WHERE s.status='completed' ORDER BY s.sale_date DESC LIMIT 10
        """)
        recent_sales = [dict(r) for r in c.fetchall()]

        c.execute("""
            SELECT name, quantity FROM medicines
            WHERE is_active=1 AND quantity <= min_quantity
            ORDER BY quantity LIMIT 8
        """)
        low_stock_meds = [dict(r) for r in c.fetchall()]

        c.execute("""
            SELECT name, expiry_date FROM medicines
            WHERE is_active=1 AND expiry_date IS NOT NULL AND expiry_date != ''
              AND date(expiry_date) <= date('now', '+30 days') AND quantity > 0
            ORDER BY expiry_date LIMIT 5
        """)
        expiring_meds = [dict(r) for r in c.fetchall()]

        c.execute("SELECT SUM(total) FROM sales WHERE status='completed' AND date(sale_date)>=?", (month_start,))
        month_sales = c.fetchone()[0] or 0

        c.execute("SELECT SUM(total) FROM purchases WHERE date(purchase_date)>=?", (month_start,))
        month_purchases = c.fetchone()[0] or 0

        c.execute("SELECT SUM(total_return_amount) FROM sales_returns WHERE date(return_date)>=?", (month_start,))
        month_returns = c.fetchone()[0] or 0

        c.execute("""
            SELECT SUM(CASE WHEN transaction_type IN ('income','opening') THEN amount ELSE 0 END) -
                   SUM(CASE WHEN transaction_type='expense' THEN amount ELSE 0 END) FROM treasury
        """)
        treasury_balance = c.fetchone()[0] or 0

        conn.close()
        return {
            "today_sales": today_sales,
            "total_medicines": total_medicines,
            "low_stock": low_stock,
            "total_customers": total_customers,
            "recent_sales": recent_sales,
            "low_stock_meds": low_stock_meds,
            "expiring_meds": expiring_meds,
            "month_sales": month_sales,
            "month_purchases": month_purchases,
            "month_returns": month_returns,
            "treasury_balance": treasury_balance,
        }

    def refresh(self):
        for widget in self.winfo_children():
            widget.destroy()
        self._build()
