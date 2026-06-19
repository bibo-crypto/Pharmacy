import customtkinter as ctk
from tkinter import messagebox
from utils.auth import login
from utils.helpers import get_setting


class LoginScreen(ctk.CTkFrame):
    def __init__(self, parent, on_success):
        super().__init__(parent, fg_color="transparent")
        self.on_success = on_success
        self._build()

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(self, corner_radius=16, width=420)
        card.grid(row=0, column=0)
        card.grid_propagate(False)
        card.configure(width=420, height=480)

        pharmacy_name = get_setting("pharmacy_name", "صيدلية الأمل")

        ctk.CTkLabel(card, text="💊", font=ctk.CTkFont(size=48)).pack(pady=(40, 5))
        ctk.CTkLabel(card, text=pharmacy_name,
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(0, 4))
        ctk.CTkLabel(card, text="نظام إدارة الصيدلية",
                     font=ctk.CTkFont(size=14), text_color="gray").pack(pady=(0, 30))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=40)

        from utils.auth import load_last_username
        last_user = load_last_username()

        ctk.CTkLabel(form, text="اسم المستخدم", anchor="e",
                     font=ctk.CTkFont(size=13)).pack(fill="x", pady=(0, 4))
        self.username_var = ctk.StringVar(value=last_user)
        self.username_entry = ctk.CTkEntry(form, textvariable=self.username_var,
                                           height=40, font=ctk.CTkFont(size=14),
                                           justify="right")
        self.username_entry.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(form, text="كلمة المرور", anchor="e",
                     font=ctk.CTkFont(size=13)).pack(fill="x", pady=(0, 4))
        self.password_var = ctk.StringVar(value="")   # لا نملأ الباسورد تلقائياً
        self.password_entry = ctk.CTkEntry(form, textvariable=self.password_var,
                                           show="●", height=40,
                                           font=ctk.CTkFont(size=14), justify="right")
        self.password_entry.pack(fill="x", pady=(0, 24))

        self.login_btn = ctk.CTkButton(
            form, text="تسجيل الدخول", height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._do_login, corner_radius=10)
        self.login_btn.pack(fill="x")

        self.error_label = ctk.CTkLabel(card, text="", text_color="red",
                                        font=ctk.CTkFont(size=12))
        self.error_label.pack(pady=(12, 0))

        self.password_entry.bind("<Return>", lambda e: self._do_login())
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        self.username_entry.focus()

    def _do_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        if not username or not password:
            self.error_label.configure(text="يرجى إدخال اسم المستخدم وكلمة المرور")
            return
        self.login_btn.configure(state="disabled", text="جاري التحقق...")
        self.after(100, lambda: self._check_login(username, password))

    def _check_login(self, username, password):
        user = login(username, password)
        if user:
            self.error_label.configure(text="")
            self.on_success(user)
        else:
            self.error_label.configure(text="❌ اسم المستخدم أو كلمة المرور غير صحيحة")
            self.login_btn.configure(state="normal", text="تسجيل الدخول")
            self.password_var.set("")
            self.password_entry.focus()
