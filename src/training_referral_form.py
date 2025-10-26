# src/training_referral_form.py
import customtkinter as ctk
from tkinter import messagebox
from datetime import date, datetime
import db_manager as db


class TrainingReferralForm(ctk.CTkToplevel):
    """
    Форма: Направлення на підвищення кваліфікації.
    Викликає зовнішній колбек self.on_submit(emp_id: int, payload: dict).
    """
    def __init__(self, master):
        super().__init__(master)
        self.title("Направлення на підвищення кваліфікації")
        self.geometry("960x720")
        self.grab_set()

        self.on_submit = None  # призначиш у виклику

        root = ctk.CTkScrollableFrame(self)
        root.pack(fill="both", expand=True, padx=12, pady=12)

        # ===== 1) Працівник =====
        ctk.CTkLabel(root, text="Працівник", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0,6))
        row_emp = ctk.CTkFrame(root); row_emp.pack(fill="x", pady=4)

        self.employees = db.get_employee_brief_list()  # [(id, "ПІБ"), ...]
        emp_names = [x[1] for x in self.employees]
        self.emp_var = ctk.StringVar(value=emp_names[0] if emp_names else "")
        self.emp_box = ctk.CTkComboBox(row_emp, values=emp_names, variable=self.emp_var, width=420)
        self.emp_box.pack(side="left", padx=(0,10))

        # ===== 2) Реквізити наказу =====
        ctk.CTkLabel(root, text="Реквізити", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(10,6))
        row_ord = ctk.CTkFrame(root); row_ord.pack(fill="x", pady=4)
        self.order_number = ctk.CTkEntry(row_ord, placeholder_text="Номер наказу (наприклад, 15/2025)", width=220)
        self.order_number.pack(side="left", padx=(0,8))
        self.order_date = ctk.CTkEntry(row_ord, placeholder_text="Дата наказу (YYYY-MM-DD)", width=180)
        self.order_date.pack(side="left")
        self.order_date.insert(0, date.today().isoformat())
        # автопідстановка номеру наказу
        try:
            suggested_no = db.get_next_training_order_number()
        except Exception:
            suggested_no = ""
        if suggested_no:
            self.order_number.insert(0, suggested_no)


        # ===== 3) Інформація про захід =====
        ctk.CTkLabel(root, text="Інформація про захід", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(10,6))

        row1 = ctk.CTkFrame(root); row1.pack(fill="x", pady=4)
        self.course_title = ctk.CTkEntry(row1, placeholder_text="Назва курсу / тренінгу", width=420); self.course_title.pack(side="left", padx=(0,8))
        self.provider     = ctk.CTkEntry(row1, placeholder_text="Провайдер (організатор)", width=320); self.provider.pack(side="left")

        row2 = ctk.CTkFrame(root); row2.pack(fill="x", pady=4)
        self.format_var = ctk.StringVar(value="очний")
        ctk.CTkLabel(row2, text="Формат:").pack(side="left", padx=(0,6))
        ctk.CTkComboBox(row2, values=["очний","дистанційний","змішаний"], variable=self.format_var, width=180).pack(side="left")

        self.place = ctk.CTkEntry(row2, placeholder_text="Місце / платформа (місто, адреса або Zoom)", width=420)
        self.place.pack(side="left", padx=(12,0))

        row3 = ctk.CTkFrame(root); row3.pack(fill="x", pady=4)
        self.start_date = ctk.CTkEntry(row3, placeholder_text="Початок (YYYY-MM-DD)", width=180); self.start_date.pack(side="left", padx=(0,8))
        self.end_date   = ctk.CTkEntry(row3, placeholder_text="Кінець (YYYY-MM-DD)", width=180);  self.end_date.pack(side="left", padx=(0,16))
        self.hours      = ctk.CTkEntry(row3, placeholder_text="Обсяг (акад. години)", width=200); self.hours.pack(side="left")

        row4 = ctk.CTkFrame(root); row4.pack(fill="x", pady=4)
        self.mode_var = ctk.StringVar(value="з відривом")
        ctk.CTkLabel(row4, text="Режим:").pack(side="left", padx=(0,6))
        ctk.CTkComboBox(row4, values=["з відривом","без відриву"], variable=self.mode_var, width=180).pack(side="left")

        ctk.CTkLabel(row4, text="   Фінансування:").pack(side="left", padx=(16,6))
        self.fund_var = ctk.StringVar(value="коштом закладу")
        ctk.CTkComboBox(row4, values=["коштом закладу","власний рахунок","інше"], variable=self.fund_var, width=200).pack(side="left")

        row5 = ctk.CTkFrame(root); row5.pack(fill="x", pady=4)
        self.cost = ctk.CTkEntry(row5, placeholder_text="Орієнтовна вартість (необов'язково)", width=240); self.cost.pack(side="left", padx=(0,10))
        self.basis = ctk.CTkEntry(row5, placeholder_text="Підстава (план БПР / атестація / лист-запрошення…)", width=520); self.basis.pack(side="left")

        # ===== Кнопки =====
        btns = ctk.CTkFrame(root); btns.pack(fill="x", pady=12)
        ctk.CTkButton(btns, text="Скасувати", fg_color="#666", hover_color="#555", command=self.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Зберегти", command=self._submit).pack(side="right")

    # ---------- helpers ----------
    def _validate(self) -> str | None:
        if not self.employees:
            return "У базі немає працівників."

        if not self.course_title.get().strip():
            return "Вкажіть назву курсу."

        if not self.start_date.get().strip() or not self.end_date.get().strip():
            return "Вкажіть період навчання (початок і кінець)."

        if not self.hours.get().strip():
            return "Вкажіть обсяг (академічні години)."

        if not self.order_number.get().strip():
            return "Вкажіть номер наказу."

        if not self.order_date.get().strip():
            return "Вкажіть дату наказу."

        # --- Перевірка коректності дат та порядку ---
        try:
            sd = datetime.strptime(self.start_date.get().strip(), "%Y-%m-%d").date()
            ed = datetime.strptime(self.end_date.get().strip(),   "%Y-%m-%d").date()
            _  = datetime.strptime(self.order_date.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            return "Дати мають формат YYYY-MM-DD та мають бути коректними календарними датами."

        if sd > ed:
            return "Період навчання некоректний: дата початку не може бути пізніше за дату завершення."

        # --- Перевірка годин як числа > 0 (дозволено десяткові; кома або крапка) ---
        h_raw = (self.hours.get().strip() or "").replace(",", ".")
        try:
            h_val = float(h_raw)
            if h_val <= 0:
                return "Обсяг навчання має бути додатнім числом."
        except ValueError:
            return "Обсяг навчання має бути числом (можна використовувати десяткові значення)."

        return None


    def _submit(self):
        err = self._validate()
        if err:
            messagebox.showerror("Перевірка", err, parent=self)
            return

        # employee_id за назвою
        name = self.emp_var.get()
        emp_id = None
        for _id, _name in self.employees:
            if _name == name:
                emp_id = _id
                break
        if not emp_id:
            messagebox.showerror("Помилка", "Не вдалося визначити працівника.", parent=self)
            return

        payload = {
            "order_number": self.order_number.get().strip(),
            "order_date":   self.order_date.get().strip(),

            "employee": db.get_employee_min(emp_id),  # {last_name, first_name, middle_name, department_name, position_name}

            "training": {
                "title": self.course_title.get().strip(),
                "provider": self.provider.get().strip(),
                "format": self.format_var.get().strip(),          # очний/дистанційний/змішаний
                "place": self.place.get().strip(),
                "start_date": self.start_date.get().strip(),
                "end_date": self.end_date.get().strip(),
                "planned_hours": f"{float((self.hours.get().strip() or '0').replace(',', '.')):g}",
                "mode": self.mode_var.get().strip(),              # з відривом/без відриву
                "funding": self.fund_var.get().strip(),           # коштом закладу/власний рахунок/інше
                "estimated_cost": self.cost.get().strip(),
                "basis_text": self.basis.get().strip(),
            },

            # Буде підставлено при рендері, якщо є в налаштуваннях
            "director_full_name": db.get_setting("DIRECTOR_FULL_NAME") or "",

            # Підпис працівника додасться після sign
            "employee_sign_day": "",
            "employee_sign_month": "",
            "employee_sign_year": "",
        }

        # Гарантуємо, що director_full_name буде в payload (за app_settings.director_employee_id)
        full_name = ""
        try:
            dir_id = db.get_setting("director_employee_id")  # ← саме цей ключ
        except Exception:
            dir_id = None

        if dir_id:
            row = db.fetch_one("""
                SELECT TRIM(
                    COALESCE(last_name,'') || ' ' || COALESCE(first_name,'') ||
                    CASE WHEN IFNULL(middle_name,'') <> '' THEN ' '||middle_name ELSE '' END
                ) AS full_name
                FROM employees
                WHERE id = ?
            """, (dir_id,))
            full_name = (row or {}).get("full_name", "") or ""

            # перезаписуємо лише якщо реально знайшли ПІБ директора
            if full_name:
                payload["director_full_name"] = full_name


        payload["director_full_name"] = full_name



        if callable(self.on_submit):
            try:
                self.on_submit(emp_id, payload)
            except Exception as e:
                messagebox.showerror("Збереження", f"Помилка у on_submit: {e}", parent=self)
                return
        self.destroy()
