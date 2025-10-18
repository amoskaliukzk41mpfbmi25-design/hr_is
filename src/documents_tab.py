# src/documents_tab.py
import json
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import date, datetime
from pathlib import Path
import db_manager as db
from p1_create_form import P1CreateForm
from p4_create_form import P4CreateForm
import string
from secrets import choice


CRED_DIR = Path("data/credentials")
CRED_DIR.mkdir(parents=True, exist_ok=True)

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

def _gen_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(choice(alphabet) for _ in range(length))

def _unique_username(base: str) -> str:
    """Гарантує унікальний username: base, base-1, base-2, ..."""
    candidate = base.strip().lower()
    if not candidate:
        candidate = "user"
    i = 1
    while db.fetch_one("SELECT 1 AS x FROM users WHERE username = ?", (candidate,)):
        candidate = f"{base}-{i}"
        i += 1
    return candidate



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
            bar, values=["усі","sent","signed"],
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
                      command=lambda: (menu.destroy(), self.open_create_p1())).pack(pady=6)
        ctk.CTkButton(menu, text="Звільнення (П-4)", width=260,
                    command=lambda: (menu.destroy(), self.open_create_p4())).pack(pady=6)
        ctk.CTkButton(menu, text="Відпустка (ще не реалізовано)", width=260,
                      command=lambda: messagebox.showinfo("У розробці", "Тип документа ще не реалізовано.")).pack(pady=6)

    # ---------- Create P-1 ----------
    def open_create_p1(self):
        """Вікно П-1: створюємо працівника, документ і payload."""
        form = P1CreateForm(self)

        def on_submit(emp_data, payload):
            # 1) створюємо employee і одразу беремо його id
            emp_id = db.execute_query("""
                INSERT INTO employees(last_name, first_name, middle_name, birth_date, email, phone, department_id, position_id)
                VALUES (:last_name, :first_name, :middle_name, :birth_date, :email, :phone, :department_id, :position_id)
            """, emp_data)


            if hasattr(self, "on_employee_created") and callable(self.on_employee_created): # оновлення таблиці співробітників
                self.on_employee_created()


            # 1.2) СТАЖУВАННЯ: створюємо запис для новачка
            # старт стажування — з payload (hire_date/start_date) або сьогодні
            start_iso = (
                payload.get("hire_date")
                or payload.get("start_date")
                or db.today_iso()
            )

            # тривалість у місяцях: з payload['probation_months'] або дефолт 3
            try:
                months = int(payload.get("probation_months") or 3)
            except (TypeError, ValueError):
                months = 3

            # запис у таблицю internships (під твою схему!)
            db.execute_query("""
                INSERT INTO internships (
                    employee_id, start_date, months, planned_end_date, status, notes,
                    created_at,          updated_at
                )
                VALUES (
                    :emp_id, :start_date, :months,
                    DATE(:start_date, '+' || :months || ' months'),
                    'active', 'Авто: прийняття за П-1',
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """, {"emp_id": emp_id, "start_date": start_iso, "months": months})



            # ─────────────────────────────────────────────────────────────
            # 1.1) СТВОРЮЄМО ОБЛІКОВИЙ ЗАПИС ДЛЯ ПРАЦІВНИКА
            # база для логіна (з email або з ПІБ)
            base_username = db.suggest_username(emp_data.get("email"), emp_data["last_name"], emp_data["first_name"])

            # гарантуємо унікальність логіна
            username = base_username or "user"
            i = 1
            while db.fetch_one("SELECT 1 AS x FROM users WHERE username = ?", (username,)):
                username = f"{base_username}-{i}"
                i += 1

            # випадковий тимчасовий пароль (10 символів)
            import string
            from secrets import choice
            alphabet = string.ascii_letters + string.digits
            temp_password = "".join(choice(alphabet) for _ in range(10))

            # вставляємо користувача з роллю employee і прив'язкою до employee_id
            db.create_user_for_employee(username=username, password=temp_password, role="employee", employee_id=emp_id)

            # зберігаємо .txt з доступами
            from datetime import datetime
            from pathlib import Path
            cred_dir = Path("data/credentials"); cred_dir.mkdir(parents=True, exist_ok=True)
            cred_path = cred_dir / f"emp_{emp_id:04d}_{username}.txt"
            cred_text = (
                "ДОСТУПИ ДО СИСТЕМИ\n"
                "-------------------\n"
                f"ПІБ: {emp_data['last_name']} {emp_data['first_name']} {emp_data.get('middle_name','')}\n"
                f"Логін: {username}\n"
                f"Пароль: {temp_password}\n"
                f"Створено: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
            )
            cred_path.write_text(cred_text, encoding="utf-8")

            # скопіюємо пароль у буфер — зручно HR одразу надіслати
            try:
                self.clipboard_clear()
                self.clipboard_append(temp_password)
            except Exception:
                pass
            # ─────────────────────────────────────────────────────────────



            # 2) створюємо документ (кладемо payload також у context_json) і беремо doc_id
            doc_id = db.execute_query("""
                INSERT INTO documents(type, employee_id, status, title, context_json)
                VALUES ('P1', :emp_id, 'sent', :title, :context_json)
            """, {
                "emp_id": emp_id,
                "title": f"Наказ П-1: {emp_data['last_name']} {emp_data['first_name']}",
                "context_json": json.dumps(payload, ensure_ascii=False)
            })

            # 3) дублюємо payload в історію/версії (document_payloads)
            db.execute_query("""
                INSERT INTO document_payloads(document_id, payload_json)
                VALUES (:doc_id, :payload)
            """, {"doc_id": doc_id, "payload": json.dumps(payload, ensure_ascii=False)})

            # 4) миттєво оновлюємо таблицю документів
            self.refresh()

            # повідомлення HR (шлях до файлу і що пароль в буфері)
            messagebox.showinfo(
                "Створено",
                f"Документ створено і відправлено на підпис.\n\n"
                f"Обліковий запис працівника створено.\n"
                f"Логін: {username}\nПароль (скопійовано у буфер): {temp_password}\n\n"
                f"Файл з доступами: {cred_path}"
            )

        form.on_submit = on_submit



    def open_create_p4(self):
        """Вікно П-4: створюємо документ для існуючого працівника."""
        form = P4CreateForm(self)

        def _to_ddmmyyyy(iso: str) -> str:
            if not iso:
                return ""
            return datetime.strptime(iso, "%Y-%m-%d").strftime("%d.%m.%Y")

        def on_submit(emp_id, payload):
            # ---- Збираємо context для шаблону П-4 ----
            order_date_iso     = payload.get("order_date", "")       # YYYY-MM-DD
            dismissal_date_iso = payload.get("dismissal_date", "")   # YYYY-MM-DD

            # вихідна допомога -> чекбокс і суми
            sev_grn = (payload.get("severance_grn") or "0").strip()
            sev_kop = (payload.get("severance_kop") or "00").strip()
            try:
                has_sev = int(sev_grn) > 0 or int(sev_kop) > 0
            except ValueError:
                has_sev = False
            cb_severance = "☑" if has_sev else "☐"
            sev_kop = f"{int(sev_kop):02d}" if sev_kop.isdigit() else "00"

            context = {
                "order_number":       payload.get("order_number", ""),
                "order_date_str":     _to_ddmmyyyy(order_date_iso),
                "dismissal_date_str": _to_ddmmyyyy(dismissal_date_iso),

                # П-4 шаблон просить саме так:
                "employee": {
                    "last_name":       payload.get("employee", {}).get("last_name", ""),
                    "first_name":      payload.get("employee", {}).get("first_name", ""),
                    "middle_name":     payload.get("employee", {}).get("middle_name", ""),
                    "department_name": payload.get("employee", {}).get("department_name", ""),
                    "position_name":   payload.get("employee", {}).get("position_name", ""),
                },

                "dismissal_reason": payload.get("dismissal_reason", ""),
                "dismissal_basis":  payload.get("dismissal_basis", ""),

                "cb_severance":  cb_severance,
                "severance_grn": sev_grn,
                "severance_kop": sev_kop,

                "director_full_name": payload.get("director_full_name", ""),  # поки можна лишити ""

                # дати підпису працівника ставляться при натисканні "Підписати"
                "employee_sign_day":   "",
                "employee_sign_month": "",
                "employee_sign_year":  "",
            }


            # ---- INSERT у documents зі статусом 'sent' ----
            doc_id = db.execute_query("""
                INSERT INTO documents(type, employee_id, status, title, context_json, created_by)
                VALUES ('P4', ?, 'sent', ?, ?, ?)
            """, (
                emp_id,
                f"Наказ П-4: {context['employee']['last_name']} {context['employee']['first_name']}",
                json.dumps(context, ensure_ascii=False),
                (self.current_user or {}).get("username", "hr"),
            ))

            # ---- (необовʼязково) зберігаємо історію payload/context ----
            try:
                db.execute_query(
                    "INSERT INTO document_payloads(document_id, payload_json) VALUES (?, ?)",
                    (doc_id, json.dumps(context, ensure_ascii=False))
                )
            except Exception:
                pass

            # ---- Оновити таблицю ----
            self.refresh()
            messagebox.showinfo("Готово", "Наказ П-4 створено і відправлено на підпис.")

        form.on_submit = on_submit

