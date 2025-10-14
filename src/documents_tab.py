# src/documents_tab.py
import json
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import date, datetime
from pathlib import Path
import db_manager as db
from p1_create_form import P1CreateForm


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
                      command=lambda: (menu.destroy(), self.open_create_p1())).pack(pady=6)
        ctk.CTkButton(menu, text="Звільнення (ще не реалізовано)", width=260,
                      command=lambda: messagebox.showinfo("У розробці", "Тип документа ще не реалізовано.")).pack(pady=6)
        ctk.CTkButton(menu, text="Відпустка (ще не реалізовано)", width=260,
                      command=lambda: messagebox.showinfo("У розробці", "Тип документа ще не реалізовано.")).pack(pady=6)

    # ---------- Create P-1 ----------
    def open_create_p1(self):
        """Вікно П-1: створюємо працівника, документ і payload."""
        form = P1CreateForm(self)

        def on_submit(emp_data, payload):
            # 1) створюємо employee
            db.execute("""
                INSERT INTO employees(last_name, first_name, middle_name, email, phone, department_id, position_id)
                VALUES (:last_name, :first_name, :middle_name, :email, :phone, :department_id, :position_id)
            """, emp_data)
            emp_id = db.fetch_one("SELECT last_insert_rowid() AS id")["id"]

            # 2) запис у documents
            db.execute("""
                INSERT INTO documents(doc_type, employee_id, status, title)
                VALUES ('P1', :emp_id, 'created', :title)
            """, {"emp_id": emp_id, "title": f"Наказ П-1: {emp_data['last_name']} {emp_data['first_name']}"})
            doc_id = db.fetch_one("SELECT last_insert_rowid() AS id")["id"]

            # 3) payload у document_payloads
            db.execute("""
                INSERT INTO document_payloads(document_id, payload_json)
                VALUES (:doc_id, :payload)
            """, {"doc_id": doc_id, "payload": json.dumps(payload, ensure_ascii=False)})

            # 4) оновимо таблицю
            if hasattr(self, "refresh_documents_table"):
                self.refresh_documents_table()

        form.on_submit = on_submit
