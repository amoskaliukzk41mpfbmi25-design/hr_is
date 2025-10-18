# src/login_window.py

import customtkinter as ctk
import sqlite3
from tkinter import messagebox

# === Налаштування теми ===
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

DB_PATH = r"D:/Projects/hr_is/data/hr_system.db"  # перевір, що шлях вірний для твоєї структури

def authenticate(username: str, password: str):
    """
    Повертає кортеж (ok: bool, role: str | None, employee_id: int | None, err: str | None)
    """
    if not username or not password:
        return False, None, None, "Введіть логін і пароль."

    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute(
            "SELECT role, employee_id, is_active FROM users WHERE username = ? AND password = ?",
            (username.strip(), password.strip())
        )
        row = cur.fetchone()
        con.close()
    except Exception as e:
        return False, None, None, f"Помилка БД: {e}"

    if row is None:
        return False, None, None, "Невірний логін або пароль."

    role, employee_id, is_active = row[0], row[1], row[2]
    if is_active is not None and int(is_active) == 0:
        return False, None, None, "Обліковий запис деактивовано."

    return True, role, employee_id, None



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
    status_label.configure(text="")
    username = entry_username.get()
    password = entry_password.get()

    ok, role, employee_id, err = authenticate(username, password)
    if not ok:
        status_label.configure(text=err or "Помилка авторизації.")
        return

    app.destroy()  # закриваємо вікно авторизації

    if role == "admin":
        from admin_main_window import AdminMainWindow
        AdminMainWindow(None, current_user={"username": username, "role": role}).mainloop()

    elif role == "hr":
        from hr_main_window import HRMainWindow
        HRMainWindow(None, current_user={"username": username, "role": role}).mainloop()

    elif role == "employee":
        import employee_main_window as emw
        emw.EmployeeMainWindow(
            current_user={"username": username, "role": role, "employee_id": employee_id}
        ).mainloop()


    else:
        messagebox.showwarning("Обмеження доступу",
                               f"Роль '{role}' не має окремого вікна.")


# Кнопки
button_login = ctk.CTkButton(app, text="Увійти", width=220, command=do_login)
button_login.pack(pady=(24, 10))

button_exit = ctk.CTkButton(app, text="Вийти", fg_color="gray", hover_color="darkgray", width=220, command=app.destroy)
button_exit.pack()

# Гарячі клавіші
app.bind("<Return>", lambda e: button_login.invoke())  # Enter = натиснути "Увійти"

# Запуск
app.mainloop()
