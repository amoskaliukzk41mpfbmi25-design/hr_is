# src/p4_create_form.py
import customtkinter as ctk
from tkinter import messagebox
from datetime import date, datetime
import db_manager as db

class P4CreateForm(ctk.CTkToplevel):
    """
    Вікно створення наказу П-4 (звільнення).
    Повертає через self.on_submit(emp_id, payload) заповнений payload.
    """
    def __init__(self, master):
        super().__init__(master)
        self.title("Створення документа: Наказ (П-4) про звільнення")
        self.geometry("880x620")
        self.resizable(True, True)
        self.grab_set()

        self.on_submit = None

        body = ctk.CTkScrollableFrame(self)
        body.pack(fill="both", expand=True, padx=12, pady=12)

        # ===== 1) Працівник =====
        ctk.CTkLabel(body, text="Працівник", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0,6))
        row_emp = ctk.CTkFrame(body); row_emp.pack(fill="x", pady=4)

        # список [(id, "ПІБ")]
        self.emp_list = db.get_employee_brief_list()
        names = [nm for (_id, nm) in self.emp_list]
        self.emp_var = ctk.StringVar()
        self.emp_box = ctk.CTkComboBox(row_emp, values=names, variable=self.emp_var, width=420, command=lambda _=None: self._load_emp_meta())
        self.emp_box.pack(side="left")
        if names:
            self.emp_var.set(names[0])

        self.meta_lbl = ctk.CTkLabel(row_emp, text="", anchor="w")
        self.meta_lbl.pack(side="left", padx=12)

        # ===== 2) Параметри наказу =====
        ctk.CTkLabel(body, text="Параметри наказу", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(10,6))
        row_params = ctk.CTkFrame(body); row_params.pack(fill="x", pady=4)

        self.order_number = ctk.CTkEntry(row_params, placeholder_text="Номер наказу (напр. 3/2025)", width=200)
        self.order_number.pack(side="left", padx=(0,8))
        self.order_date = ctk.CTkEntry(row_params, placeholder_text="Дата наказу (YYYY-MM-DD)", width=160)
        self.order_date.pack(side="left", padx=(0,8))
        self.dismissal_date = ctk.CTkEntry(row_params, placeholder_text="Дата звільнення (YYYY-MM-DD)", width=200)
        self.dismissal_date.pack(side="left", padx=(0,8))

        # автопропозиції
        try:
            self.order_number.insert(0, db.get_next_p4_order_number())
        except Exception:
            self.order_number.insert(0, "")
        self.order_date.insert(0, db.today_iso())

        # ===== 3) Підстава/причина =====
        ctk.CTkLabel(body, text="Підстава/причина звільнення", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(10,6))
        row_reason = ctk.CTkFrame(body); row_reason.pack(fill="x", pady=4)

        # коротка причина
        reasons = [
            "за угодою сторін (п.1 ч.1 ст.36 КЗпП)",
            "за власним бажанням (ст.38 КЗпП)",
            "ініціатива роботодавця (ст.40 КЗпП)",
            "інші підстави (ст.41 КЗпП)"
        ]
        self.reason_var = ctk.StringVar(value=reasons[0])
        ctk.CTkComboBox(row_reason, values=reasons, variable=self.reason_var, width=380).pack(side="left", padx=(0,8))

        # детальніше (вільний текст)
        self.basis_text = ctk.CTkEntry(row_reason, placeholder_text="Формулювання підстави/посилання на норму", width=420)
        self.basis_text.pack(side="left")

        # ===== 4) Вихідна допомога (опц.) =====
        ctk.CTkLabel(body, text="Вихідна допомога (за наявності)", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(10,6))
        row_sev = ctk.CTkFrame(body); row_sev.pack(fill="x", pady=4)
        self.sev_grn = ctk.CTkEntry(row_sev, placeholder_text="грн", width=120); self.sev_grn.pack(side="left")
        self.sev_kop = ctk.CTkEntry(row_sev, placeholder_text="коп", width=80);  self.sev_kop.pack(side="left", padx=(8,0))

        # ===== Кнопки =====
        btns = ctk.CTkFrame(body); btns.pack(fill="x", pady=14)
        ctk.CTkButton(btns, text="Скасувати", fg_color="#666", hover_color="#555", command=self.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Зберегти", command=self._submit).pack(side="right")

        # первинне відображення метаданих
        self._load_emp_meta()

    # --- helpers ---
    def _find_emp_id(self) -> int | None:
        name = self.emp_var.get()
        for _id, nm in self.emp_list:
            if nm == name:
                return _id
        return None

    def _load_emp_meta(self):
        emp_id = self._find_emp_id()
        if not emp_id:
            self.meta_lbl.configure(text="")
            return
        try:
            m = db.get_employee_min(emp_id)  # { last_name, first_name, middle_name, department_name, position_name, ... }
            txt = f"{m.get('department_name','—')} • {m.get('position_name','—')}"
            self.meta_lbl.configure(text=txt)
        except Exception:
            self.meta_lbl.configure(text="")

    def _validate(self) -> str | None:
        if not self.emp_var.get().strip():
            return "Оберіть працівника."
        if not self.order_number.get().strip() or not self.order_date.get().strip() or not self.dismissal_date.get().strip():
            return "Заповніть номер наказу, дату наказу та дату звільнення."
        for fld in (self.order_date.get().strip(), self.dismissal_date.get().strip()):
            if len(fld) != 10:
                return "Дати мають формат YYYY-MM-DD."
        return None

    def _submit(self):
        err = self._validate()
        if err:
            messagebox.showerror("Помилка", err, parent=self); return

        emp_id = self._find_emp_id()
        m = db.get_employee_min(emp_id)  # {last_name, first_name, middle_name, department_name, position_name, ...}

        # логіка: вихідна допомога вважається наявною, якщо сума > 0
        sev_grn = (self.sev_grn.get().strip() or "0")
        sev_kop = (self.sev_kop.get().strip() or "00")
        has_severance = (sev_grn.isdigit() and int(sev_grn) > 0) or (sev_kop.isdigit() and int(sev_kop) > 0)

        payload = {
            # службові поля
            "order_number":   self.order_number.get().strip(),
            "order_date":     self.order_date.get().strip(),      # YYYY-MM-DD (рендер сам зробить order_date_str)
            "dismissal_date": self.dismissal_date.get().strip(),  # YYYY-MM-DD (рендер сам зробить dismissal_date_str)

            # дані працівника — рівно як чекає шаблон {{ employee.* }}
            "employee": {
                "last_name":       m.get("last_name", ""),
                "first_name":      m.get("first_name", ""),
                "middle_name":     m.get("middle_name", ""),
                "department_name": m.get("department_name", ""),
                "position_name":   m.get("position_name", ""),
            },

            # дубль у вигляді об’єктів з .name — це зручно, якщо десь ще буде використовуватись
            "department": { "name": m.get("department_name", "") },
            "position":   { "name": m.get("position_name", "") },

            # причини/підстави
            "dismissal_reason": self.reason_var.get().strip(),
            "dismissal_basis":  self.basis_text.get().strip(),

            # вихідна допомога
            "severance":     has_severance,    # для чекбокса {{ cb_severance }}
            "severance_grn": sev_grn,
            "severance_kop": sev_kop,

            # директор (якщо не зберігаєш у БД налаштувань — лишай порожнім)
            "director_full_name": "",
        }

        # НЕ ставимо тут employee_sign_day/month/year — їх додасть вікно працівника у момент підпису

        if callable(self.on_submit):
            try:
                self.on_submit(emp_id, payload)
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося зберегти: {e}", parent=self)
                return
        self.destroy()

