# src/attestation_form.py
import customtkinter as ctk
from tkinter import messagebox
from datetime import date, datetime
import db_manager as db


ACTION_CHOICES = [
    ("присвоєння",   "assignment"),
    ("підтвердження","confirmation"),
    ("інше",         "other"),
]
SCHEDULE_CHOICES = [
    ("планова",      "planned"),
    ("позачергова",  "unscheduled"),
]

# ДОВГІ підписи для шаблону/docx
LONG_ACTION_LABELS = {
    "assignment":  "Присвоєння кваліфікаційної категорії",
    "confirmation":"Підтвердження кваліфікаційної категорії",
    "other":       "Інша дія (атестація)",
}
LONG_SCHEDULE_LABELS = {
    "planned":     "Чергова (планова) атестація",
    "unscheduled": "Позачергова атестація",
}


def _to_ddmmyyyy(iso: str) -> str:
    try:
        d = datetime.strptime(iso, "%Y-%m-%d").date()
        return f"{d.day:02d}.{d.month:02d}.{d.year}"
    except Exception:
        return ""


class AttestationForm(ctk.CTkToplevel):
    """
    Форма: Направлення на атестацію.
    Викликає зовнішній колбек self.on_submit(emp_id: int, payload: dict).
    """
    def __init__(self, master):
        super().__init__(master)
        self.title("Направлення на атестацію")
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
        self.order_number = ctk.CTkEntry(row_ord, placeholder_text="Номер наказу (наприклад, 12/2025)", width=220)
        self.order_number.pack(side="left", padx=(0,8))
        self.order_date = ctk.CTkEntry(row_ord, placeholder_text="Дата наказу (YYYY-MM-DD)", width=180)
        self.order_date.pack(side="left")
        self.order_date.insert(0, date.today().isoformat())

        # автопідстановка номера (може ще не існувати — тихо ігноруємо)
        try:
            if hasattr(db, "get_next_attestation_order_number"):
                suggested_no = db.get_next_attestation_order_number()
            else:
                suggested_no = ""
        except Exception:
            suggested_no = ""
        if suggested_no:
            self.order_number.insert(0, suggested_no)

        # ===== 3) Параметри атестації =====
        ctk.CTkLabel(root, text="Інформація про атестацію", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(10,6))

        row_a = ctk.CTkFrame(root); row_a.pack(fill="x", pady=4)
        ctk.CTkLabel(row_a, text="Тип атестації:").pack(side="left", padx=(0,6))
        self.action_label_var = ctk.StringVar(value=ACTION_CHOICES[0][0])
        self.action_box = ctk.CTkComboBox(row_a, values=[x[0] for x in ACTION_CHOICES], variable=self.action_label_var, width=220)
        self.action_box.pack(side="left", padx=(0,16))

        ctk.CTkLabel(row_a, text="Вид:").pack(side="left", padx=(0,6))
        self.schedule_label_var = ctk.StringVar(value=SCHEDULE_CHOICES[0][0])
        self.schedule_box = ctk.CTkComboBox(row_a, values=[x[0] for x in SCHEDULE_CHOICES], variable=self.schedule_label_var, width=220)
        self.schedule_box.pack(side="left")

        row_b = ctk.CTkFrame(root); row_b.pack(fill="x", pady=4)
        self.att_date = ctk.CTkEntry(row_b, placeholder_text="Дата проведення (YYYY-MM-DD)", width=220)
        self.att_date.pack(side="left", padx=(0,16))

        self.commission_place = ctk.CTkEntry(row_b, placeholder_text="Місце проведення (адреса / платформа)", width=320)
        self.commission_place.pack(side="left", padx=(0,10))

        row_c = ctk.CTkFrame(root); row_c.pack(fill="x", pady=4)
        self.commission_name = ctk.CTkEntry(row_c, placeholder_text="Назва комісії (наприклад, Атестаційна комісія при Департаменті...)", width=620)
        self.commission_name.pack(side="left")

        row_d = ctk.CTkFrame(root); row_d.pack(fill="x", pady=4)
        self.basis = ctk.CTkEntry(row_d, placeholder_text="Підстава (план БПР / наказ / лист-запрошення / внутрішній графік…)", width=740)
        self.basis.pack(side="left")

        # ===== Кнопки =====
        btns = ctk.CTkFrame(root); btns.pack(fill="x", pady=12)
        ctk.CTkButton(btns, text="Скасувати", fg_color="#666", hover_color="#555", command=self.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Зберегти", command=self._submit).pack(side="right")

    # ---------- helpers ----------
    def _validate(self) -> str | None:
        if not self.employees:
            return "У базі немає працівників."
        if not self.order_number.get().strip():
            return "Вкажіть номер наказу."
        if not self.order_date.get().strip():
            return "Вкажіть дату наказу."
        if not self.att_date.get().strip():
            return "Вкажіть дату проведення атестації."

        # Перевірка дат
        for s in (self.order_date.get().strip(), self.att_date.get().strip()):
            try:
                datetime.strptime(s, "%Y-%m-%d")
            except ValueError:
                return "Дати мають формат YYYY-MM-DD та мають бути коректними календарними датами."

        return None

    def _selected_employee_id(self):
        name = self.emp_var.get()
        for _id, _name in self.employees:
            if _name == name:
                return _id
        return None

    def _submit(self):
        err = self._validate()
        if err:
            messagebox.showerror("Перевірка", err, parent=self)
            return

        emp_id = self._selected_employee_id()
        if not emp_id:
            messagebox.showerror("Помилка", "Не вдалося визначити працівника.", parent=self)
            return

        # Коди й лейбли
        action_label = self.action_label_var.get().strip()
        schedule_label = self.schedule_label_var.get().strip()

        action_code = dict(ACTION_CHOICES)[action_label]
        schedule_code = dict(SCHEDULE_CHOICES)[schedule_label]

        # Профіль працівника
        emp_min = db.get_employee_min(emp_id)

        # Директор (як і в інших формах)
        director_full_name = db.get_setting("DIRECTOR_FULL_NAME") or ""
        try:
            dir_emp_id = db.get_setting("director_employee_id")
            if dir_emp_id:
                row = db.fetch_one("""
                    SELECT TRIM(
                        COALESCE(last_name,'') || ' ' || COALESCE(first_name,'') ||
                        CASE WHEN IFNULL(middle_name,'')<>'' THEN ' '||middle_name ELSE '' END
                    ) AS full_name
                    FROM employees
                    WHERE id = ?
                """, (dir_emp_id,))
                if row and (row.get("full_name") or "").strip():
                    director_full_name = row["full_name"].strip()
        except Exception:
            pass

        # Дати
        order_date_iso = self.order_date.get().strip()
        att_date_iso   = self.att_date.get().strip()

        long_action_label   = LONG_ACTION_LABELS.get(action_code, action_label)
        long_schedule_label = LONG_SCHEDULE_LABELS.get(schedule_code, schedule_label)



        payload = {
            "order_number": self.order_number.get().strip(),
            "order_date":   order_date_iso,
            "order_date_str": _to_ddmmyyyy(order_date_iso),

            "employee": emp_min,  # {last_name, first_name, middle_name, department_name, position_name}

            "attestation": {
                "action": action_code,
                "action_label": long_action_label,
                "schedule": schedule_code,
                "schedule_label": long_schedule_label,
                "date": att_date_iso,
                "date_str": _to_ddmmyyyy(att_date_iso),
                "commission_place": self.commission_place.get().strip(),
                "commission_name":  self.commission_name.get().strip(),
                "basis_text":       self.basis.get().strip(),
            },

            "director_full_name": director_full_name,

            # поля підпису працівника заповняться при sign
            "employee_sign_day": "",
            "employee_sign_month": "",
            "employee_sign_year": "",
        }

        if callable(self.on_submit):
            try:
                self.on_submit(emp_id, payload)
            except Exception as e:
                messagebox.showerror("Збереження", f"Помилка у on_submit: {e}", parent=self)
                return
        self.destroy()
