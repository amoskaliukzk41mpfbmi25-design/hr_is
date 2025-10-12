import customtkinter as ctk
import sqlite3
from tkinter import messagebox

# === Налаштування теми ===
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

DB_PATH = r"D:/Projects/hr_is/data/hr_system.db"  # перевір, що шлях вірний для твоєї структури

def authenticate(username: str, password: str):
    """
    Повертає кортеж (ok: bool, role: str | None, err: str | None)
    ok=True  -> знайдено користувача з таким логіном/паролем
    ok=False -> помилка (err містить текст)
    """
    if not username or not password:
        return False, None, "Введіть логін і пароль."

    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute(
            "SELECT role FROM users WHERE username = ? AND password = ?",
            (username.strip(), password.strip())
        )
        row = cur.fetchone()
        con.close()
    except Exception as e:
        return False, None, f"Помилка БД: {e}"

    if row is None:
        return False, None, "Невірний логін або пароль."
    return True, row[0], None


# === Вікно авторизації ===
app = ctk.CTk()
app.title("Авторизація | HR System")

# Максимізоване звичайне вікно (з рамкою)
app.minsize(1024, 700)
app.state("zoomed")
app.after(0, lambda: app.state("zoomed"))

# Заголовок
title_label = ctk.CTkLabel(
    app,
    text="Вхід до системи",
    font=ctk.CTkFont(size=28, weight="bold")
)
title_label.pack(pady=(60, 20))

# Поля вводу
entry_username = ctk.CTkEntry(app, placeholder_text="Логін", width=360)
entry_username.pack(pady=10)
entry_password = ctk.CTkEntry(app, placeholder_text="Пароль", show="*", width=360)
entry_password.pack(pady=10)

# Повідомлення (рядок підказок/помилок)
status_label = ctk.CTkLabel(app, text="", text_color="red")
status_label.pack(pady=(6, 0))

def do_login():
    status_label.configure(text="")  # очистити попередній статус
    username = entry_username.get()
    password = entry_password.get()

    ok, role, err = authenticate(username, password)
    if not ok:
        status_label.configure(text=err or "Помилка авторизації.")
        return

    # Дозволяємо доступ лише HR та Admin
    if role in ("hr", "admin"):
        # Відкриваємо головне вікно залежно від ролі
        app.destroy()  # закриваємо вікно авторизації

        if role == "admin":
            from admin_main_window import AdminMainWindow
            AdminMainWindow(None, current_user={"username": username, "role": role}).mainloop()
        else:
            from hr_main_window import HRMainWindow
            HRMainWindow(None, current_user={"username": username, "role": role}).mainloop()

    else:
        messagebox.showwarning(
            "Обмеження доступу",
            f"Ви увійшли як '{role}'. Доступ до HR-модуля обмежений."
        )

# Кнопки
button_login = ctk.CTkButton(app, text="Увійти", width=220, command=do_login)
button_login.pack(pady=(24, 10))

button_exit = ctk.CTkButton(app, text="Вийти", fg_color="gray", hover_color="darkgray", width=220, command=app.destroy)
button_exit.pack()

# Гарячі клавіші
app.bind("<Return>", lambda e: button_login.invoke())  # Enter = натиснути "Увійти"

# Запуск
app.mainloop()
