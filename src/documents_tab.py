# src/documents_tab.py
import json
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import date, datetime
from pathlib import Path

import db_manager as db

TEMPLATES_DIR = Path("data/templates")
DOCS_DIR = Path("data/documents")
DOCS_DIR.mkdir(parents=True, exist_ok=True)

MONTHS_GEN = [
    "", "січня","лютого","березня","квітня","травня","червня",
    "липня","серпня","вересня","жовтня","листопада","грудня"
]

def cb(flag: bool) -> str: return "☑" if flag else "☐"
def date_ddmmyyyy(raw: str) -> str: return datetime.strptime(raw, "%Y-%m-%d").strftime("%d.%m.%Y")
def date_uk_full(d: date) -> str:   return f'«{d.day:02d}» {MONTHS_GEN[d.month]} {d.year} р.'


class DocumentsTab(ctk.CTkFrame):
    def __init__(self, master, current_user):
        super().__init__(master)
        self.current_user = current_user  # {"username": "...", "role": "hr"}
        self._build_ui()
        self.refresh()

    # ---------- UI ----------
    def _build_ui(self):
        # Top bar
        bar = ctk.CTkFrame(self)
        bar.pack(fill="x", padx=8, pady=(8,4))

        # Create button with dropdown
        self.btn_create = ctk.CTkButton(bar, text="Створити документ", command=self._open_create_menu)
        self.btn_create.pack(side="left")

        # status filter
        self.status_var = ctk.StringVar(value="усі")
        ctk.CTkLabel(bar, text="   Статус:").pack(side="left", padx=(6,4))
        self.status_filter = ctk.CTkComboBox(
            bar, values=["усі","draft","sent","signed","archived"],
            variable=self.status_var, width=130, command=lambda _=None: self.refresh()
        )
        self.status_filter.pack(side="left")

        # search
        ctk.CTkLabel(bar, text="   Пошук:").pack(side="left", padx=(12,4))
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(bar, textvariable=self.search_var, width=240)
        self.search_entry.pack(side="left")
        ctk.CTkButton(bar, text="Знайти", width=80, command=self.refresh).pack(side="left", padx=6)

        # refresh
        ctk.CTkButton(bar, text="Оновити", width=100, command=self.refresh).pack(side="right")

        # Table
        table_wrap = ctk.CTkFrame(self)
        table_wrap.pack(fill="both", expand=True, padx=8, pady=(0,8))

        cols = ("id","employee","type","title","status","created_at","signed_by","signed_at")
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings", height=18)
        headings = {
            "id":"ID","employee":"Працівник","type":"Тип","title":"Назва",
            "status":"Статус","created_at":"Створено","signed_by":"Підписав","signed_at":"Дата підпису"
        }
        for k, v in headings.items():
            self.tree.heading(k, text=v)
            self.tree.column(k, width=120 if k not in ("title","employee") else 220, stretch=True)

        yscroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

    # ---------- Data ops ----------
    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        query = self.search_var.get().strip()
        status = self.status_var.get()
        if status == "усі": status = None
        docs = db.list_documents(search=query, status=status)
        for d in docs:
            self.tree.insert("", "end", values=(
                d["id"], d["employee_name"], d["type"], d["title"], d["status"],
                d["created_at"], d.get("signed_by",""), d.get("signed_at","")
            ))

    # ---------- Create menu ----------
    def _open_create_menu(self):
        menu = ctk.CTkToplevel(self)
        menu.title("Обрати тип документа")
        menu.geometry("360x200")
        menu.resizable(False, False)
        menu.grab_set()

        ctk.CTkLabel(menu, text="Оберіть тип документа:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(16,10))

        # Поки реалізований тільки П-1; інші покажуть заглушку
        ctk.CTkButton(menu, text="Прийняття на роботу (П-1)", width=260,
                      command=lambda: (menu.destroy(), self._create_document_P1())).pack(pady=6)
        ctk.CTkButton(menu, text="Звільнення (ще не реалізовано)", width=260,
                      command=lambda: messagebox.showinfo("У розробці", "Тип документа ще не реалізовано.")).pack(pady=6)
        ctk.CTkButton(menu, text="Відпустка (ще не реалізовано)", width=260,
                      command=lambda: messagebox.showinfo("У розробці", "Тип документа ще не реалізовано.")).pack(pady=6)

    # ---------- Create P-1 ----------
    def _create_document_P1(self):
        CreateP1Dialog(self, on_saved=lambda ok: self.refresh() if ok else None, current_user=self.current_user)


class CreateP1Dialog(ctk.CTkToplevel):
    """
    Діалог збору даних для П-1.
    Режими: Новий працівник / Існуючий працівник.
    Якщо Новий — створюємо запис у employees (+опц. users), тоді документ (sent).
    """
    def __init__(self, master, on_saved, current_user):
        super().__init__(master)
        self.on_saved = on_saved
        self.current_user = current_user
        self.title("Створення документа: Наказ (П-1)")
        self.geometry("820x780"); self.grab_set()
        self._build_form()

    # ---------- UI ----------
    def _build_form(self):
        self.container = ctk.CTkScrollableFrame(self); self.container.pack(fill="both", expand=True, padx=12, pady=12)

        # Режим
        mode_row = ctk.CTkFrame(self.container); mode_row.pack(fill="x", pady=(0,8))
        ctk.CTkLabel(mode_row, text="Режим:").pack(side="left", padx=(0,8))
        self.mode_var = ctk.StringVar(value="new")  # "new" | "existing"
        ctk.CTkRadioButton(mode_row, text="Новий працівник", variable=self.mode_var, value="new",
                           command=self._toggle_mode).pack(side="left")
        ctk.CTkRadioButton(mode_row, text="Існуючий працівник", variable=self.mode_var, value="existing",
                           command=self._toggle_mode).pack(side="left", padx=12)

        # ===== Блок даних працівника (NEW) =====
        self.emp_new_frame = ctk.CTkFrame(self.container); self.emp_new_frame.pack(fill="x", pady=6)

        row_fio = ctk.CTkFrame(self.emp_new_frame); row_fio.pack(fill="x", pady=4)
        self.last_name  = ctk.CTkEntry(row_fio, placeholder_text="Прізвище", width=220); self.last_name.pack(side="left", padx=(0,6))
        self.first_name = ctk.CTkEntry(row_fio, placeholder_text="Ім'я", width=180);     self.first_name.pack(side="left", padx=6)
        self.middle_name= ctk.CTkEntry(row_fio, placeholder_text="По батькові", width=200); self.middle_name.pack(side="left", padx=6)

        row_contacts = ctk.CTkFrame(self.emp_new_frame); row_contacts.pack(fill="x", pady=4)
        self.email = ctk.CTkEntry(row_contacts, placeholder_text="Email", width=260); self.email.pack(side="left", padx=(0,6))
        self.phone = ctk.CTkEntry(row_contacts, placeholder_text="Телефон", width=180); self.phone.pack(side="left", padx=6)

        # Відділення -> Посада
        row_dp = ctk.CTkFrame(self.emp_new_frame); row_dp.pack(fill="x", pady=4)
        deps = db.get_departments_list()
        self.deps_map = {d["name"]: d["id"] for d in deps}
        ctk.CTkLabel(row_dp, text="Відділення:").pack(side="left", padx=(0,6))
        self.dep_var = ctk.StringVar()
        self.dep_box = ctk.CTkComboBox(row_dp, values=list(self.deps_map.keys()), variable=self.dep_var, width=260,
                                       command=lambda _=None: self._reload_positions())
        self.dep_box.pack(side="left")
        ctk.CTkLabel(row_dp, text="   Посада:").pack(side="left", padx=(10,6))
        self.pos_var = ctk.StringVar()
        self.pos_box = ctk.CTkComboBox(row_dp, values=[], variable=self.pos_var, width=260)
        self.pos_box.pack(side="left")
        # первинне завантаження списку посад
        if self.deps_map:
            first_dep = list(self.deps_map.keys())[0]
            self.dep_var.set(first_dep); self._reload_positions()


        # --- РОЗДІЛ: Параметри документа П-1 ---------------------------------

        # 1) Шапка документа (номер та дати)
        row_head = ctk.CTkFrame(self.container); row_head.pack(fill="x", pady=(12,6))
        ctk.CTkLabel(row_head, text="Параметри наказу", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0,4))

        self.order_number = ctk.CTkEntry(row_head, placeholder_text="Номер наказу (напр. 15/2025)", width=240)
        self.order_number.pack(side="left", padx=(0,8))
        self.hire_date = ctk.CTkEntry(row_head, placeholder_text="Дата наказу (YYYY-MM-DD)", width=180)
        self.hire_date.pack(side="left", padx=(0,8))
        self.start_date = ctk.CTkEntry(row_head, placeholder_text="Початок роботи (YYYY-MM-DD)", width=180)
        self.start_date.pack(side="left")

        # 2) Умови прийняття (7 чекбоксів + поля)
        ctk.CTkLabel(self.container, text="Умови прийняття на роботу",
                    font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(10,4))

        self.basis_competition = ctk.BooleanVar(False)
        self.basis_contract    = ctk.BooleanVar(True)
        self.basis_probation   = ctk.BooleanVar(True)
        self.basis_absence     = ctk.BooleanVar(False)
        self.basis_reserve     = ctk.BooleanVar(False)
        self.basis_internship  = ctk.BooleanVar(False)
        self.basis_transfer    = ctk.BooleanVar(False)
        self.basis_other       = ctk.BooleanVar(False)

        ctk.CTkCheckBox(self.container, text="на конкурсній основі",
                        variable=self.basis_competition).pack(anchor="w")

        rowc = ctk.CTkFrame(self.container); rowc.pack(fill="x", pady=2)
        ctk.CTkCheckBox(rowc, text="за умовами контракту до (дд.мм.рррр)",
                        variable=self.basis_contract).pack(side="left")
        self.contract_until = ctk.CTkEntry(rowc, placeholder_text="2026-10-14 або порожньо (YYYY-MM-DD)", width=260)
        self.contract_until.pack(side="left", padx=8)

        rowp = ctk.CTkFrame(self.container); rowp.pack(fill="x", pady=2)
        ctk.CTkCheckBox(rowp, text="зі строком випробування (міс.)",
                        variable=self.basis_probation).pack(side="left")
        self.probation_months = ctk.CTkEntry(rowp, placeholder_text="3", width=80)
        self.probation_months.pack(side="left", padx=8)

        ctk.CTkCheckBox(self.container, text="на період відсутності основного працівника",
                        variable=self.basis_absence).pack(anchor="w")
        ctk.CTkCheckBox(self.container, text="із кадрового резерву",
                        variable=self.basis_reserve).pack(anchor="w")
        ctk.CTkCheckBox(self.container, text="за результатами успішного стажування",
                        variable=self.basis_internship).pack(anchor="w")
        ctk.CTkCheckBox(self.container, text="переведення",
                        variable=self.basis_transfer).pack(anchor="w")

        rowo = ctk.CTkFrame(self.container); rowo.pack(fill="x", pady=2)
        ctk.CTkCheckBox(rowo, text="інше:", variable=self.basis_other).pack(side="left")
        self.other_text = ctk.CTkEntry(rowo, placeholder_text="на час виконання певної роботи", width=360)
        self.other_text.pack(side="left", padx=8)

        # 3) Умови роботи
        ctk.CTkLabel(self.container, text="Умови роботи",
                    font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(10,4))

        self.is_main_work = ctk.BooleanVar(True)
        self.is_secondary_work = ctk.BooleanVar(False)
        roww = ctk.CTkFrame(self.container); roww.pack(fill="x", pady=2)
        ctk.CTkCheckBox(roww, text="основна", variable=self.is_main_work).pack(side="left")
        ctk.CTkCheckBox(roww, text="за сумісництвом",
                        variable=self.is_secondary_work).pack(side="left", padx=10)

        self.has_fulltime = ctk.BooleanVar(True)
        rowt = ctk.CTkFrame(self.container); rowt.pack(fill="x", pady=2)
        ctk.CTkCheckBox(rowt, text="тривалість робочого дня (тижня):",
                        variable=self.has_fulltime).pack(side="left")
        self.work_hours = ctk.CTkEntry(rowt, placeholder_text="год", width=60); self.work_hours.pack(side="left", padx=6)
        self.work_minutes = ctk.CTkEntry(rowt, placeholder_text="хв", width=60); self.work_minutes.pack(side="left", padx=6)

        # 4) Оклад + керівник + дата під документом
        ctk.CTkLabel(self.container, text="Оплата та підписи",
                    font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(10,4))

        row_s = ctk.CTkFrame(self.container); row_s.pack(fill="x", pady=2)
        self.salary_grn = ctk.CTkEntry(row_s, placeholder_text="Оклад, грн (напр. 23000)", width=200)
        self.salary_grn.pack(side="left", padx=(0,8))
        self.salary_kop = ctk.CTkEntry(row_s, placeholder_text="коп (00)", width=80)
        self.salary_kop.pack(side="left")

        row_d = ctk.CTkFrame(self.container); row_d.pack(fill="x", pady=2)
        self.director_full_name = ctk.CTkEntry(row_d, placeholder_text="ПІБ керівника", width=280)
        self.director_full_name.pack(side="left", padx=(0,8))
        self.sign_doc_date = ctk.CTkEntry(row_d, placeholder_text="Дата під документом (YYYY-MM-DD)", width=220)
        self.sign_doc_date.pack(side="left")
        # ----------------------------------------------------------------------




        # Чекбокс створення облікового запису
        row_acc = ctk.CTkFrame(self.emp_new_frame); row_acc.pack(fill="x", pady=(6,4))
        self.create_account_var = ctk.BooleanVar(True)
        ctk.CTkCheckBox(row_acc, text="Створити обліковий запис для працівника (роль: employee)",
                        variable=self.create_account_var).pack(side="left")
        self.initial_password = ctk.CTkEntry(row_acc, placeholder_text="Початковий пароль (опц.)", width=220)
        self.initial_password.pack(side="left", padx=8)

        # ===== Блок вибору працівника (EXISTING) =====
        self.emp_exist_frame = ctk.CTkFrame(self.container); self.emp_exist_frame.pack_forget()  # ховаємо
        emps = db.get_employee_brief_list()
        self.emp_map = {f"{full} (id:{eid})": eid for eid, full in emps}
        ctk.CTkLabel(self.emp_exist_frame, text="Працівник:").pack(anchor="w")
        self.employee_var = ctk.StringVar()
        self.employee_box = ctk.CTkComboBox(self.emp_exist_frame, values=list(self.emp_map.keys()),
                                            variable=self.employee_var, width=420)
        self.employee_box.pack(anchor="w", pady=(0,8))

        # ===== Шапка документа =====
        row_head = ctk.CTkFrame(self.container); row_head.pack(fill="x", pady=(8,4))
        self.order_number = ctk.CTkEntry(row_head, placeholder_text="Номер наказу (напр. 15/2025)", width=250)
        self.order_number.pack(side="left", padx=(0,8))
        self.hire_date = ctk.CTkEntry(row_head, placeholder_text="Дата наказу (YYYY-MM-DD)", width=180)
        self.hire_date.pack(side="left", padx=(0,8))
        self.start_date = ctk.CTkEntry(row_head, placeholder_text="Початок роботи (YYYY-MM-DD)", width=180)
        self.start_date.pack(side="left")

        # === Умови прийняття (7 чекбоксів + службові поля) ===
        conds = ctk.CTkFrame(self.container)
        conds.pack(fill="x", pady=(0,8))  # ВАЖЛИВО: пакуємо в self.container

        # змінні
        self.basis_competition = ctk.BooleanVar(False)
        self.basis_contract    = ctk.BooleanVar(True)
        self.basis_probation   = ctk.BooleanVar(True)
        self.basis_absence     = ctk.BooleanVar(False)
        self.basis_reserve     = ctk.BooleanVar(False)
        self.basis_internship  = ctk.BooleanVar(False)
        self.basis_transfer    = ctk.BooleanVar(False)
        self.basis_other       = ctk.BooleanVar(False)

        # 1) конкурс
        ctk.CTkCheckBox(conds, text="на конкурсній основі",
                        variable=self.basis_competition).pack(anchor="w")

        # 2) контракт до + дата
        rowc = ctk.CTkFrame(conds); rowc.pack(fill="x", pady=2)
        ctk.CTkCheckBox(rowc, text="за умовами контракту до (дд.мм.рррр)",
                        variable=self.basis_contract).pack(side="left")
        self.contract_until = ctk.CTkEntry(rowc, placeholder_text="2026-10-14 або порожньо (YYYY-MM-DD)", width=260)
        self.contract_until.pack(side="left", padx=8)

        # 3) випробувальний термін (міс.)
        rowp = ctk.CTkFrame(conds); rowp.pack(fill="x", pady=2)
        ctk.CTkCheckBox(rowp, text="зі строком випробування (міс.)",
                        variable=self.basis_probation).pack(side="left")
        self.probation_months = ctk.CTkEntry(rowp, placeholder_text="3", width=80)
        self.probation_months.pack(side="left", padx=8)

        # 4–6) інші стандартні підстави
        ctk.CTkCheckBox(conds, text="на період відсутності основного працівника",
                        variable=self.basis_absence).pack(anchor="w")
        ctk.CTkCheckBox(conds, text="із кадрового резерву",
                        variable=self.basis_reserve).pack(anchor="w")
        ctk.CTkCheckBox(conds, text="за результатами успішного стажування",
                        variable=self.basis_internship).pack(anchor="w")

        # 7) переведення
        ctk.CTkCheckBox(conds, text="переведення",
                        variable=self.basis_transfer).pack(anchor="w")

        # 8) інше + текст
        rowo = ctk.CTkFrame(conds); rowo.pack(fill="x", pady=2)
        ctk.CTkCheckBox(rowo, text="інше:", variable=self.basis_other).pack(side="left")
        self.other_text = ctk.CTkEntry(rowo, placeholder_text="на час виконання певної роботи", width=360)
        self.other_text.pack(side="left", padx=8)



        # ===== Умови роботи =====
        ctk.CTkLabel(self.container, text="Умови роботи:").pack(anchor="w", pady=(10,2))
        self.is_main_work = ctk.BooleanVar(True)
        self.is_secondary_work = ctk.BooleanVar(False)
        roww = ctk.CTkFrame(self.container); roww.pack(fill="x")
        ctk.CTkCheckBox(roww, text="основна", variable=self.is_main_work).pack(side="left")
        ctk.CTkCheckBox(roww, text="за сумісництвом", variable=self.is_secondary_work).pack(side="left", padx=10)

        self.has_fulltime = ctk.BooleanVar(True)
        rowt = ctk.CTkFrame(self.container); rowt.pack(fill="x")
        ctk.CTkCheckBox(rowt, text="тривалість робочого дня (тижня):", variable=self.has_fulltime).pack(side="left")
        self.work_hours = ctk.CTkEntry(rowt, placeholder_text="год", width=60); self.work_hours.pack(side="left", padx=6)
        self.work_minutes = ctk.CTkEntry(rowt, placeholder_text="хв", width=60); self.work_minutes.pack(side="left", padx=6)

        # ===== Оклад + Керівник + Дата у підписному блоці =====
        row_s = ctk.CTkFrame(self.container); row_s.pack(fill="x", pady=(10,2))
        self.salary_grn = ctk.CTkEntry(row_s, placeholder_text="Оклад, грн (напр. 23000)", width=200)
        self.salary_grn.pack(side="left", padx=(0,8))
        self.salary_kop = ctk.CTkEntry(row_s, placeholder_text="коп (напр. 00)", width=80)
        self.salary_kop.pack(side="left")

        row_d = ctk.CTkFrame(self.container); row_d.pack(fill="x", pady=(8,2))
        self.director_full_name = ctk.CTkEntry(row_d, placeholder_text="ПІБ керівника", width=280)
        self.director_full_name.pack(side="left", padx=(0,8))
        self.sign_doc_date = ctk.CTkEntry(row_d, placeholder_text="Дата під документом (YYYY-MM-DD)", width=220)
        self.sign_doc_date.pack(side="left")

        ctk.CTkButton(self, text="Зберегти", command=self._save, width=140).pack(pady=8)

    def _toggle_mode(self):
        if self.mode_var.get() == "new":
            self.emp_exist_frame.pack_forget()
            self.emp_new_frame.pack(fill="x", pady=6)
        else:
            self.emp_new_frame.pack_forget()
            self.emp_exist_frame.pack(fill="x", pady=6)

    def _reload_positions(self):
        dep_name = self.dep_var.get()
        dep_id = self.deps_map.get(dep_name)
        positions = db.get_positions_by_department(dep_id) if dep_id else []
        pos_names = [p["name"] for p in positions]
        self.pos_box.configure(values=pos_names)
        if pos_names: self.pos_var.set(pos_names[0])

    # ---------- SAVE ----------
    def _save(self):
        try:
            # 1) employee_id (new or existing)
            mode = self.mode_var.get()
            if mode == "new":
                # валідація мінімальних полів
                ln = self.last_name.get().strip()
                fn = self.first_name.get().strip()
                em = self.email.get().strip()
                if not (ln and fn and em):
                    messagebox.showwarning("Дані", "Вкажіть прізвище, ім'я та email нового працівника.")
                    return
                if db.get_employee_by_email(em):
                    messagebox.showwarning("Дані", "Такий email уже існує серед працівників.")
                    return

                dep_id = self.deps_map.get(self.dep_var.get())
                if not dep_id:
                    messagebox.showwarning("Дані", "Оберіть відділення.")
                    return
                # знайти id посади за назвою
                pos_list = db.get_positions_by_department(dep_id)
                pos_id = None
                for p in pos_list:
                    if p["name"] == self.pos_var.get():
                        pos_id = p["id"]; break
                if not pos_id:
                    messagebox.showwarning("Дані", "Оберіть посаду.")
                    return

                emp_id = db.create_employee_minimal(
                    last_name=ln, first_name=fn, middle_name=self.middle_name.get().strip(),
                    email=em, phone=self.phone.get().strip(),
                    department_id=dep_id, position_id=pos_id
                )

                # створити обліковий запис (опційно)
                if self.create_account_var.get():
                    username = db.suggest_username(em, ln, fn)
                    password = self.initial_password.get().strip() or "ChangeMe123"
                    db.create_user_for_employee(username=username, password=password, role="employee", employee_id=emp_id)

                employee_id = emp_id
                emp = db.get_employee_min(employee_id)

            else:  # existing
                key = self.employee_var.get().strip()
                if not key:
                    messagebox.showwarning("Дані", "Оберіть працівника.")
                    return
                employee_id = self.emp_map[key]
                emp = db.get_employee_min(employee_id)

            # 2) решта полів документа — як раніше
            order_number = self.order_number.get().strip() or "1/2025"
            hire_date_raw = self.hire_date.get().strip() or datetime.now().strftime("%Y-%m-%d")
            start_date_raw = self.start_date.get().strip() or hire_date_raw
            hire_date_str = date_ddmmyyyy(hire_date_raw)
            y,m,d = map(int, start_date_raw.split("-"))
            start_date_str = date_uk_full(date(y,m,d))

            contract_until_raw = (self.contract_until.get().strip() or None)
            contract_until_str = date_ddmmyyyy(contract_until_raw) if contract_until_raw else ""
            probation_months = (self.probation_months.get().strip() or "")
            other_text = (self.other_text.get().strip() or "")

            is_main_work      = self.is_main_work.get()
            is_secondary_work = self.is_secondary_work.get()
            has_fulltime      = self.has_fulltime.get()
            work_hours   = self.work_hours.get().strip() or ""
            work_minutes = self.work_minutes.get().strip() or ""

            salary_grn = int(self.salary_grn.get().strip() or "0")
            salary_kop = self.salary_kop.get().strip() or "00"
            director_full_name = self.director_full_name.get().strip() or "Керівник Закладу О.О."
            sign_doc_date_raw = self.sign_doc_date.get().strip() or hire_date_raw
            sdt = datetime.strptime(sign_doc_date_raw, "%Y-%m-%d")
            sign_day, sign_month, sign_year = f"{sdt.day:02d}", MONTHS_GEN[sdt.month], sdt.year

            context = {
                "order_number": order_number,
                "hire_date_str": hire_date_str,
                "start_date_str": start_date_str,
                "employee": {
                    "last_name": emp["last_name"], "first_name": emp["first_name"], "middle_name": emp["middle_name"]
                },
                "department": {"name": emp["department_name"]},
                "position": {"name": emp["position_name"]},
                "tab_number": "",

                "cb_competition": "☑" if self.basis_competition.get() else "☐",
                "cb_contract":    "☑" if self.basis_contract.get()    else "☐",
                "contract_until_str": contract_until_str if self.basis_contract.get() else "",
                "cb_probation":   "☑" if self.basis_probation.get()   else "☐",
                "probation_months": probation_months if self.basis_probation.get() else "",
                "cb_absence":     "☑" if self.basis_absence.get()     else "☐",
                "cb_reserve":     "☑" if self.basis_reserve.get()     else "☐",
                "cb_internship":  "☑" if self.basis_internship.get()  else "☐",
                "cb_transfer":    "☑" if self.basis_transfer.get()    else "☐",
                "cb_other":       "☑" if self.basis_other.get()       else "☐",
                "other_text":     other_text if self.basis_other.get() else "",

                "cb_work_main":      "☑" if is_main_work else "☐",
                "cb_work_secondary": "☑" if is_secondary_work else "☐",
                "cb_worktime_full":  "☑" if has_fulltime else "☐",
                "work_hours":   work_hours if has_fulltime else "",
                "work_minutes": work_minutes if has_fulltime else "",

                "salary_grn": salary_grn, "salary_kop": salary_kop,
                "director_full_name": director_full_name,
                "sign_day": sign_day, "sign_month": sign_month, "sign_year": sign_year,

                "sign_emp_day": "", "sign_emp_month": "", "sign_emp_year": "",
            }

            title = f"Наказ (П-1) про прийняття: {emp['last_name']} {emp['first_name']}"

            doc_id, out_path = db.create_document_with_preview(
                employee_id=employee_id,
                doc_type="HIRE_ORDER_P1",
                title=title,
                context=context,
                created_by=self.current_user["username"],
                template_path=str(TEMPLATES_DIR / "hire_order_P1.docx"),
                out_dir=str(DOCS_DIR),
                status_on_create="sent"
            )

            messagebox.showinfo("OK", f"Документ #{doc_id} створено і надіслано на підпис.")
            self.on_saved(True); self.destroy()

        except Exception as e:
            messagebox.showerror("Помилка", str(e))
            self.on_saved(False)
