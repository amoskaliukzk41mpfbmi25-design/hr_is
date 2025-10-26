# src/p1_create_form.py
import customtkinter as ctk
from tkinter import messagebox
from datetime import date
import json

# очікуємо, що в db_manager є:
# - get_departments_list() -> [{'id','name'}]
# - get_positions_by_department(dep_id) -> [{'id','name'}]
import db_manager as db


class P1CreateForm(ctk.CTkToplevel):
    """
    Вікно створення наказу П-1.
    Повертає через self.on_submit(employee_data, payload) заповнені структури.
    - employee_data: dict для таблиці employees
    - payload: dict зі всіма змінними шаблону П-1
    """

    def __init__(self, master, default_department_id=None, default_position_id=None):
        super().__init__(master)
        self.title("Створення документа: Наказ (П-1)")
        self.geometry("980x720")
        self.grab_set()

        self.on_submit = None  # сюди призначиш callback зовні

        # ---- Кореневий скрол ----
        self.body = ctk.CTkScrollableFrame(self)
        self.body.pack(fill="both", expand=True, padx=12, pady=12)

        # ===== 1) Дані працівника =====
        ctk.CTkLabel(self.body, text="Дані працівника",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0,6))

        row1 = ctk.CTkFrame(self.body); row1.pack(fill="x", pady=3)
        self.last_name   = ctk.CTkEntry(row1, placeholder_text="Прізвище", width=220); self.last_name.pack(side="left", padx=(0,8))
        self.first_name  = ctk.CTkEntry(row1, placeholder_text="Ім’я", width=220);      self.first_name.pack(side="left", padx=(0,8))
        self.mid_name    = ctk.CTkEntry(row1, placeholder_text="По батькові", width=260); self.mid_name.pack(side="left")

        row2 = ctk.CTkFrame(self.body); row2.pack(fill="x", pady=3)
        self.email  = ctk.CTkEntry(row2, placeholder_text="Email", width=300); self.email.pack(side="left", padx=(0,8))
        self.phone  = ctk.CTkEntry(row2, placeholder_text="Телефон", width=200); self.phone.pack(side="left")

        row2b = ctk.CTkFrame(self.body); row2b.pack(fill="x", pady=3)
        ctk.CTkLabel(row2b, text="Дата народження:").pack(side="left", padx=(0,6))
        self.birth_date = ctk.CTkEntry(row2b, placeholder_text="YYYY-MM-DD", width=160)
        self.birth_date.pack(side="left")


        # Відділення/посада (залежні)
        deps = db.get_departments_list()
        self.deps_map = {d["name"]: d["id"] for d in deps}
        dep_names = list(self.deps_map.keys())

        row3 = ctk.CTkFrame(self.body); row3.pack(fill="x", pady=3)
        ctk.CTkLabel(row3, text="Відділення:").pack(side="left", padx=(0,6))
        self.dep_var = ctk.StringVar(value=dep_names[0] if dep_names else "")
        self.dep_box = ctk.CTkComboBox(
            row3, values=dep_names, variable=self.dep_var, width=320,
            command=lambda _=None: (self._reload_positions(), self._reload_mentors())
        )
        self.dep_box.pack(side="left", padx=(0,16))

        ctk.CTkLabel(row3, text="Посада:").pack(side="left", padx=(0,6))
        self.pos_var = ctk.StringVar()
        self.pos_box = ctk.CTkComboBox(row3, values=[], variable=self.pos_var, width=320)
        self.pos_box.pack(side="left")

        # початкове наповнення посад
        if dep_names:
            self._reload_positions()


        # ===== 2) Параметри наказу =====
        ctk.CTkLabel(self.body, text="Параметри наказу",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(10,6))
        row4 = ctk.CTkFrame(self.body); row4.pack(fill="x", pady=3)
        self.order_number = ctk.CTkEntry(row4, placeholder_text="Номер наказу (напр. 15/2025)", width=220)
        self.order_number.pack(side="left", padx=(0,8))
        self.order_date   = ctk.CTkEntry(row4, placeholder_text="Дата наказу (YYYY-MM-DD)", width=200)
        self.order_date.pack(side="left", padx=(0,8))
        self.hire_date    = ctk.CTkEntry(row4, placeholder_text="Початок роботи (YYYY-MM-DD)", width=220)
        self.hire_date.pack(side="left")

        try:
            suggested_no = db.get_next_p1_order_number()
        except Exception:
            suggested_no = ""

        self.order_number.insert(0, suggested_no)   # пропозиція номера
        self.order_date.insert(0, db.today_iso())   # сьогоднішня дата


        # ===== Умови прийняття на роботу =====
        ctk.CTkLabel(self.body, text="Умови прийняття на роботу",
                    font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(12,4))

        basis_row = ctk.CTkFrame(self.body)
        basis_row.pack(fill="x", pady=(0,6))

        self.basis_var = ctk.StringVar(value="за умовами контракту")
        basis_options = [
            "на конкурсній основі",
            "за умовами контракту",
            "зі строком випробування",
            "на період відсутності основного працівника",
            "із кадрового резерву",
            "за результатами успішного стажування",
            "переведення",
            "інше",
        ]
        ctk.CTkComboBox(
            basis_row, values=basis_options,
            variable=self.basis_var, width=420,
            command=lambda _=None: self._on_basis_change()
        ).pack(side="left")

        # динамічні додаткові поля (ЄДИНИЙ контейнер!)
        self.basis_extra = ctk.CTkFrame(self.body)
        self.basis_extra.pack(fill="x")

        self.contract_until   = ctk.CTkEntry(self.basis_extra, placeholder_text="Контракт до (YYYY-MM-DD)", width=240)
        self.probation_months = ctk.CTkEntry(self.basis_extra, placeholder_text="Тривалість випробування (міс.)", width=240)
        self.other_text       = ctk.CTkEntry(self.basis_extra, placeholder_text="Вкажіть інше…", width=420)

        self._on_basis_change()  # первинна отрисовка

        # ===== Умови роботи =====
        ctk.CTkLabel(self.body, text="Умови роботи",
                    font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(12,4))

        job_row = ctk.CTkFrame(self.body)
        job_row.pack(fill="x", pady=(0,6))

        self.job_mode_var = ctk.StringVar(value="основна")
        ctk.CTkComboBox(job_row, values=["основна", "за сумісництвом"],
                        variable=self.job_mode_var, width=220).pack(side="left")

        ctk.CTkLabel(job_row, text=" Тривалість робочого дня:").pack(side="left", padx=(16,6))
        self.work_hours = ctk.CTkEntry(job_row, placeholder_text="год", width=70); self.work_hours.pack(side="left", padx=(0,6))
        self.work_mins  = ctk.CTkEntry(job_row,  placeholder_text="хв",  width=70); self.work_mins.pack(side="left")

        # ===== Оплата праці =====
        ctk.CTkLabel(self.body, text="Оплата праці",
                    font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(12,4))

        sal_row = ctk.CTkFrame(self.body)
        sal_row.pack(fill="x", pady=(0,6))

        self.salary_grn = ctk.CTkEntry(sal_row, placeholder_text="Оклад, грн", width=150); self.salary_grn.pack(side="left")
        self.salary_kop = ctk.CTkEntry(sal_row, placeholder_text="коп",      width=70);  self.salary_kop.pack(side="left", padx=(8,0))


        # ===== Стажування (місяці + наставник) =====
        ctk.CTkLabel(self.body, text="Стажування",
                    font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(12,4))

        intern_row = ctk.CTkFrame(self.body)
        intern_row.pack(fill="x", pady=(0,6))

        # Тривалість стажування, міс. (1–3, дефолт 3)
        ctk.CTkLabel(intern_row, text="Тривалість (міс.):").pack(side="left", padx=(0,6))
        self.intern_months = ctk.CTkEntry(intern_row, width=80)
        self.intern_months.pack(side="left")
        self.intern_months.insert(0, "3")

        # Наставник — підвантажуємо за обраним відділенням
        ment_row = ctk.CTkFrame(self.body)
        ment_row.pack(fill="x", pady=(0,6))

        ctk.CTkLabel(ment_row, text="Наставник:").pack(side="left", padx=(0,6))
        self.mentor_name_var = ctk.StringVar(value="")
        self.mentor_box = ctk.CTkComboBox(ment_row, values=[], variable=self.mentor_name_var, width=360)
        self.mentor_box.pack(side="left")

        # мапи id<->name формуватимемо під час _reload_mentors()
        self._mentor_name_by_id = {}
        self._mentor_id_by_name = {}
        self._reload_mentors()



        # ===== Кнопки =====
        btns = ctk.CTkFrame(self.body); btns.pack(fill="x", pady=14)
        ctk.CTkButton(btns, text="Скасувати", fg_color="#666", hover_color="#555",
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Зберегти", command=self._submit).pack(side="right")

    # ---------------- helpers ----------------
    def _reload_positions(self):
        name = self.dep_var.get()
        dep_id = self.deps_map.get(name)
        pos = db.get_positions_by_department(dep_id) if dep_id else []
        names = [p["name"] for p in pos]
        self.pos_box.configure(values=names)
        if names:
            self.pos_var.set(names[0])
        else:
            self.pos_var.set("")

    def _reload_mentors(self):
        """Підтягнути наставників тільки з обраного відділення."""
        dep_id = self.deps_map.get(self.dep_var.get())
        ment_list = db.get_employee_brief_list_by_department(dep_id) if dep_id else []

        self._mentor_name_by_id = {i: n for i, n in ment_list}
        self._mentor_id_by_name = {n: i for i, n in ment_list}
        mentor_names = [n for _, n in ment_list] or ["—"]

        # оновлюємо комбобокс
        self.mentor_box.configure(values=mentor_names)
        # якщо список порожній — залишимо "—", це дасть mentor_employee_id = None у payload
        self.mentor_name_var.set(mentor_names[0] if mentor_names else "—")


    def _validate(self):
        if not self.last_name.get().strip() or not self.first_name.get().strip():
            return "Вкажіть прізвище та ім’я."
        if not self.dep_var.get() or not self.pos_var.get():
            return "Оберіть відділення і посаду."
        if not self.order_number.get().strip() or not self.order_date.get().strip() or not self.hire_date.get().strip():
            return "Заповніть номер наказу, дату наказу та дату початку роботи."
        # перевірка дати народження
        bd = self.birth_date.get().strip()
        if bd:
            if len(bd) != 10:
                return "Дата народження має бути у форматі YYYY-MM-DD."
            try:
                from datetime import datetime
                datetime.strptime(bd, "%Y-%m-%d")
            except ValueError:
                return "Некоректна дата народження (очікується YYYY-MM-DD)."

        return None

    def _collect_employee(self):
        dep_id = self.deps_map.get(self.dep_var.get())
        # знайдемо id посади по назві для обраного відділення
        pos_list = db.get_positions_by_department(dep_id) if dep_id else []
        pos_map = {p["name"]: p["id"] for p in pos_list}
        pos_id = pos_map.get(self.pos_var.get())
        return {
            "last_name":  self.last_name.get().strip(),
            "first_name": self.first_name.get().strip(),
            "middle_name": self.mid_name.get().strip(),
            "email":      self.email.get().strip(),
            "phone":      self.phone.get().strip(),
            "department_id": dep_id,
            "position_id":   pos_id,
            "birth_date":    self.birth_date.get().strip() or None

        }

    def _collect_payload(self):
        b = self.basis_var.get()
        flags = {
            "is_competition": (b == "на конкурсній основі"),
            "is_contract":    (b == "за умовами контракту"),
            "is_probation":   (b == "зі строком випробування"),
            "is_absence":     (b == "на період відсутності основного працівника"),
            "is_reserve":     (b == "із кадрового резерву"),
            "is_internship":  (b == "за результатами успішного стажування"),
            "is_transfer":    (b == "переведення"),
            "is_other":       (b == "інше"),
        }
        contract_until  = self.contract_until.get().strip()   if flags["is_contract"]  else ""
        probation_months= self.probation_months.get().strip() if flags["is_probation"] else ""
        other_text      = self.other_text.get().strip()       if flags["is_other"]     else ""

        return {
            "order_number": self.order_number.get().strip(),
            "order_date":   self.order_date.get().strip(),
            "hire_date":    self.hire_date.get().strip(),

            "employee": {
                "last_name":       self.last_name.get().strip(),
                "first_name":      self.first_name.get().strip(),
                "middle_name":     self.mid_name.get().strip(),
                "department_name": self.dep_var.get(),
                "position_name":   self.pos_var.get(),
            },

            # умови прийняття
            **flags,
            "contract_until":   contract_until,
            "probation_months": probation_months,
            "other_text":       other_text,

            # умови роботи
            "is_main_job":   (self.job_mode_var.get() == "основна"),
            "work_hours":    self.work_hours.get().strip(),
            "work_minutes":  self.work_mins.get().strip(),

            # оплата
            "salary_grn": self.salary_grn.get().strip(),
            "salary_kop": self.salary_kop.get().strip(),

            # плейсхолдери підпису працівника (щоб залишились у docx до моменту підпису)
            "employee_sign_day":   "{{ employee_sign_day }}",
            "employee_sign_month": "{{ employee_sign_month }}",
            "employee_sign_year":  "{{ employee_sign_year }}",

            # === ДОДАНО ДЛЯ СТАЖУВАННЯ ===
            "internship_months": self.intern_months.get().strip(),
            "mentor_employee_id": self._mentor_id_by_name.get(self.mentor_name_var.get()),

        }


    def _submit(self):
        err = self._validate()
        if err:
            messagebox.showerror("Помилка", err, parent=self)
            return
        emp = self._collect_employee()
        payload = self._collect_payload()

        if callable(self.on_submit):
            try:
                self.on_submit(emp, payload)
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося зберегти: {e}", parent=self)
                return
        self.destroy()


    def _on_basis_change(self):
        # ховаємо все
        for w in self.basis_extra.winfo_children():
            w.pack_forget()
        b = self.basis_var.get()
        if b == "за умовами контракту":
            self.contract_until.pack(side="left", padx=(0,10))
        elif b == "зі строком випробування":
            self.probation_months.pack(side="left", padx=(0,10))
        elif b == "інше":
            self.other_text.pack(side="left", padx=(0,10))

