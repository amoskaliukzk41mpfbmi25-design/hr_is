# src/admin_main_window.py
from tkinter import ttk
import customtkinter as ctk
import db_manager as db

# Перевикористаємо ту ж вкладку "Довідники" з HR-вікна
# (там має бути оголошений клас DirectoriesTab)
from hr_main_window import DirectoriesTab


class UsersTab(ctk.CTkFrame):
    """Вкладка 'Користувачі' для адміністратора: перегляд облікових записів (каркас)."""
    def __init__(self, master):
        super().__init__(master)
        self.pack_propagate(False)

        # Верхня панель: пошук + фільтр ролі + кнопки
        toolbar = ctk.CTkFrame(self, corner_radius=8)
        toolbar.pack(fill="x", padx=10, pady=(10, 6))

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            toolbar, textvariable=self.search_var, width=320,
            placeholder_text="Пошук (логін, роль)"
        )
        self.search_entry.pack(side="left", padx=(8, 6), pady=8)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh())

        ctk.CTkLabel(toolbar, text="Роль:").pack(side="left", padx=(12, 4))
        self.role_var = ctk.StringVar(value="Усі")
        self.role_menu = ctk.CTkOptionMenu(
            toolbar,
            values=["Усі", "admin", "hr", "manager", "employee"],
            variable=self.role_var,
            width=140,
            command=lambda _: self.refresh()
        )
        self.role_menu.pack(side="left", padx=4, pady=8)

        self.btn_refresh = ctk.CTkButton(toolbar, text="🔄 Оновити", width=140, command=self.refresh)
        self.btn_refresh.pack(side="right", padx=8, pady=8)

        self.btn_clear_role = ctk.CTkButton(toolbar, text="👁 Показати всі", width=140,
                                    command=lambda: (self.role_var.set("Усі"), self.refresh()))
        self.btn_clear_role.pack(side="right", padx=8, pady=8)


        # Другий рядок: (кнопки дій — додамо пізніше)
        actions = ctk.CTkFrame(self, corner_radius=8)
        actions.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(actions, text="Дії з користувачами (будуть додані: Додати / Редагувати / Деактивувати / Скинути пароль)").pack(
            side="left", padx=10, pady=6
        )

        # Таблиця
        table_wrap = ctk.CTkFrame(self, corner_radius=8)
        table_wrap.pack(fill="both", expand=True, padx=10, pady=(6, 10))

        self.scroll_y = ctk.CTkScrollbar(table_wrap); self.scroll_y.pack(side="right", fill="y")
        self.scroll_x = ctk.CTkScrollbar(table_wrap, orientation="horizontal"); self.scroll_x.pack(side="bottom", fill="x")

        self.columns = ("username", "role", "full_name", "department", "position", "is_active", "created_at")

        self.tree = ttk.Treeview(table_wrap, columns=self.columns, show="headings", height=20)
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        self.tree.configure(yscrollcommand=self.scroll_y.set, xscrollcommand=self.scroll_x.set)
        self.scroll_y.configure(command=self.tree.yview)
        self.scroll_x.configure(command=self.tree.xview)

        self.tree.heading("username",  text="Логін")
        self.tree.heading("role",      text="Роль")
        self.tree.heading("full_name", text="ПІБ")
        self.tree.heading("department",text="Відділення")
        self.tree.heading("position",  text="Посада")
        self.tree.heading("is_active", text="Активний")
        self.tree.heading("created_at",text="Створено")

        self.tree.column("username",   width=200, anchor="w")
        self.tree.column("role",       width=120, anchor="center")
        self.tree.column("full_name",  width=240, anchor="w")
        self.tree.column("department", width=200, anchor="w")
        self.tree.column("position",   width=180, anchor="w")
        self.tree.column("is_active",  width=100, anchor="center")
        self.tree.column("created_at", width=160, anchor="center")

        self.refresh()

    def refresh(self):
        q = (self.search_var.get() or "").strip().lower()
        role_filter = self.role_var.get()

        users = db.get_users()
        rows = []
        for u in users:
            if role_filter != "Усі" and (u.get("role") or "") != role_filter:
                continue
            hay = f"{u.get('username','')} {u.get('role','')} {u.get('full_name','')}".lower()
            if q and q not in hay:
                continue
            rows.append({
                "id": u["id"],
                "username": u.get("username") or "",
                "role": u.get("role") or "",
                "full_name": u.get("full_name") or "",
                "department": u.get("department_name") or "",
                "position": u.get("position_name") or "",
                "is_active": "так" if (u.get("is_active") == 1) else "ні",
                "created_at": (u.get("created_at") or "")[:19],
            })

        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for r in rows:
            self.tree.insert(
                "", "end", iid=str(r["id"]),
                values=(r["username"], r["role"], r["full_name"], r["department"], r["position"], r["is_active"], r["created_at"])
            )



class AdminMainWindow(ctk.CTkToplevel):
    """Головне вікно адміністратора: Користувачі, Довідники, Налаштування (каркас)."""
    def __init__(self, master, current_user: dict):
        super().__init__(master)
        self.current_user = current_user

        self.title("HR-IS — Адміністратор")
        self.state("zoomed")  # для Windows — відкриє розгорнутим


        # Центруємо поверх вікна логіну
        self.update_idletasks()
        px, py = master.winfo_rootx(), master.winfo_rooty()
        pw, ph = master.winfo_width(), master.winfo_height()
        w, h = 1280, 800
        x = px + max(0, (pw - w) // 2); y = py + max(0, (ph - h) // 3)
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Верхній бар (заголовок + користувач)
        top = ctk.CTkFrame(self, corner_radius=0)
        top.pack(fill="x", padx=0, pady=0)
        title_font = ctk.CTkFont(size=18, weight="bold")
        ctk.CTkLabel(top, text="Панель адміністратора", font=title_font).pack(side="left", padx=16, pady=10)
        ctk.CTkLabel(top, text=f"Ви увійшли як: {current_user.get('username','admin')} (admin)").pack(side="right", padx=16)

        # Tabview з трьома вкладками
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.users_tab = self.tabview.add("Користувачі")
        self.directories_tab = self.tabview.add("Довідники")
        self.settings_tab = self.tabview.add("Налаштування")

        # Вкладка "Користувачі"
        UsersTab(self.users_tab).pack(fill="both", expand=True)

        # Вкладка "Довідники" — перевикористовуємо існуючий компонент
        DirectoriesTab(self.directories_tab).pack(fill="both", expand=True)

        # Вкладка "Налаштування" — поки заглушка
        ctk.CTkLabel(self.settings_tab, text="Розділ у розробці (резервні копії, безпека, аудит тощо).",
                     font=ctk.CTkFont(size=14)).pack(pady=40)

        # Активна вкладка за замовчанням — Користувачі
        self.tabview.set("Користувачі")


    def _on_close(self):
        """Закриваємо Toplevel і головний прихований root, щоб процес завершився коректно."""
        try:
            self.destroy()
        finally:
            try:
                if self.master:  # це наш прихований root
                    self.master.destroy()
            except Exception:
                pass



if __name__ == "__main__":
    import customtkinter as ctk
    root = ctk.CTk()
    root.withdraw()
    AdminMainWindow(root, current_user={"username": "admin", "role": "admin"})
    root.mainloop()   # ← головний цикл на root
