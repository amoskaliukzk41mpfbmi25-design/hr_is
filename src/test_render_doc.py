# file: D:\Projects\hr_is\src\test_render_doc.py
from docxtpl import DocxTemplate
from datetime import date, datetime
from pathlib import Path

# ---------------- Helpers ----------------
MONTHS_GEN = [
    "", "січня","лютого","березня","квітня","травня","червня",
    "липня","серпня","вересня","жовтня","листопада","грудня"
]

def cb(flag: bool) -> str:
    """Галочка/порожній квадратик для .docx (за потреби заміни на '[X]'/'[ ]')."""
    return "☑" if flag else "☐"

def date_ddmmyyyy(raw_yyyy_mm_dd: str) -> str:
    """'YYYY-MM-DD' -> 'dd.mm.yyyy'"""
    return datetime.strptime(raw_yyyy_mm_dd, "%Y-%m-%d").strftime("%d.%m.%Y")

def date_uk_full(d: date) -> str:
    """'«15» жовтня 2025 р.'"""
    return f'«{d.day:02d}» {MONTHS_GEN[d.month]} {d.year} р.'

# ---------------- Вхідні дані (приклад) ----------------
# Шапка наказу
order_number   = "15/2025"
hire_date_raw  = "2025-10-15"                 # дата наказу (для "від ..."), формат у БД: YYYY-MM-DD
hire_date_str  = date_ddmmyyyy(hire_date_raw) # від 15.10.2025

# Прийняття на роботу з ... (короткий варіант рядком)
start_date     = date(2025, 10, 15)
start_date_str = date_uk_full(start_date)     # «15» жовтня 2025 р.

# Працівник / посада / підрозділ
employee = {"last_name": "Іваненко", "first_name": "Оксана", "middle_name": "Петрівна"}
department = {"name": "Терапевтичне відділення"}
position   = {"name": "Лікар-терапевт"}
tab_number = "000123"

# ---- УМОВИ ПРИЙНЯТТЯ (7 галочок + дод. поля) ----
basis_competition = False
basis_contract    = True
basis_probation   = True
basis_absence     = False
basis_reserve     = False
basis_internship  = False
basis_transfer    = False
basis_other       = True

contract_until_raw = "2026-10-14"                    # якщо немає — None
contract_until_str = date_ddmmyyyy(contract_until_raw) if contract_until_raw else ""
probation_months   = 3                                # якщо немає — ""
other_text         = "на час виконання певної роботи" # або ""

# ---- УМОВИ РОБОТИ ----
is_main_work       = True     # основна
is_secondary_work  = False    # за сумісництвом
has_fulltime       = True
work_hours         = 8
work_minutes       = 0

# ---- ОКЛАД (грн/коп) ----
salary_grn = 23000
salary_kop = "00"   # рядком, щоб не зникали провідні нулі

# ---- Керівник + дата праворуч ----
director_full_name = "Коваль Олена Богданівна"
sign_doc_date      = date(2025, 10, 11)    # дата в правому нижньому куті
sign_day           = f"{sign_doc_date.day:02d}"
sign_month         = MONTHS_GEN[sign_doc_date.month]
sign_year          = sign_doc_date.year

# ---- Підпис працівника (порожньо ПРИ СТВОРЕННІ; заповнимо під час «Підписати») ----
sign_emp_day   = ""
sign_emp_month = ""
sign_emp_year  = ""

# ---------------- Контекст для шаблону ----------------
context = {
    # шапка/працівник
    "order_number": order_number,
    "hire_date_str": hire_date_str,
    "start_date_str": start_date_str,
    "employee": employee,
    "department": department,
    "position": position,
    "tab_number": tab_number,

    # умови прийняття
    "cb_competition": cb(basis_competition),
    "cb_contract":    cb(basis_contract),
    "contract_until_str": contract_until_str if basis_contract else "",
    "cb_probation":   cb(basis_probation),
    "probation_months": probation_months if basis_probation else "",
    "cb_absence":     cb(basis_absence),
    "cb_reserve":     cb(basis_reserve),
    "cb_internship":  cb(basis_internship),
    "cb_transfer":    cb(basis_transfer),
    "cb_other":       cb(basis_other),
    "other_text":     other_text if basis_other else "",

    # умови роботи
    "cb_work_main": cb(is_main_work),
    "cb_work_secondary": cb(is_secondary_work),
    "cb_worktime_full": cb(has_fulltime),
    "work_hours":   work_hours if has_fulltime else "",
    "work_minutes": work_minutes if has_fulltime else "",

    # оклад
    "salary_grn": salary_grn,
    "salary_kop": salary_kop,

    # керівник + дата
    "director_full_name": director_full_name,
    "sign_day": sign_day,
    "sign_month": sign_month,
    "sign_year": sign_year,

    # дата підпису працівника (буде заповнена ПІЗНІШЕ під час підпису)
    "sign_emp_day":   sign_emp_day,
    "sign_emp_month": sign_emp_month,
    "sign_emp_year":  sign_emp_year,
}

# ---------------- Рендер ----------------
TEMPLATE = Path(r"D:\Projects\hr_is\data\templates\hire_order_P1.docx")
OUT_DIR  = Path(r"D:\Projects\hr_is\data\documents\test")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "hire_order_P1_test.docx"

doc = DocxTemplate(TEMPLATE)
doc.render(context)
doc.save(OUT_PATH)

print("✅ Документ створено:", OUT_PATH)
