# src/db_manager.py
from contextlib import closing
import sqlite3, json
from pathlib import Path
from docxtpl import DocxTemplate
from datetime import date

DB_PATH = r"D:/Projects/hr_is/data/hr_system.db"   # перевір, що шлях правильний під твою структуру


# =============================
# БАЗОВІ УТИЛІТИ
# =============================

def get_connection():
    """Повертає підключення до бази даних SQLite."""
    return sqlite3.connect(DB_PATH)


def fetch_all(query: str, params: tuple = ()):
    """Виконує SELECT і повертає список словників."""
    with closing(get_connection()) as conn, closing(conn.cursor()) as cur:
        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    return rows

def fetch_one(query: str, params: tuple = ()):
    """SELECT → один рядок як dict або None."""
    with closing(get_connection()) as conn, closing(conn.cursor()) as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in cur.description]
        return dict(zip(columns, row))



def execute_query(query: str, params: tuple = ()):
    """Виконує INSERT/UPDATE/DELETE."""
    with closing(get_connection()) as conn, closing(conn.cursor()) as cur:
        cur.execute(query, params)
        conn.commit()
        return cur.lastrowid


# =============================
# ФУНКЦІЇ ДЛЯ ОПЕРАЦІЙ ІЗ ТАБЛИЦЯМИ
# =============================

# ---- Departments ----
def get_departments():
    return fetch_all("SELECT id, name FROM departments ORDER BY name")

def add_department(name: str):
    return execute_query("INSERT INTO departments (name) VALUES (?)", (name,))

def delete_department(department_id: int):
    return execute_query("DELETE FROM departments WHERE id = ?", (department_id,))


# ---- Positions ----
def get_positions():
    return fetch_all("SELECT id, name FROM positions ORDER BY name")

def add_position(name: str) -> int:
    """Додає посаду і повертає її id."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO positions(name) VALUES (?)", (name,))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_position(position_id: int):
    return execute_query("DELETE FROM positions WHERE id = ?", (position_id,))


# ---- Employees ----
def get_employees():
    query = """
    SELECT e.id,
           e.last_name || ' ' || e.first_name || ' ' || IFNULL(e.middle_name, '') AS full_name,
           e.email,
           e.phone,
           d.name AS department,
           p.name AS position,
           e.birth_date,
           e.hire_date,
           e.employment_status
      FROM employees e
      LEFT JOIN departments d ON e.department_id = d.id
      LEFT JOIN positions   p ON e.position_id = p.id
     ORDER BY e.last_name, e.first_name
    """
    return fetch_all(query)

def add_employee(data: dict):
    query = """
    INSERT INTO employees
    (last_name, first_name, middle_name, birth_date, email, phone,
     department_id, position_id, hire_date, employment_status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        data.get("last_name"),
        data.get("first_name"),
        data.get("middle_name"),
        data.get("birth_date"),
        data.get("email"),
        data.get("phone"),
        data.get("department_id"),
        data.get("position_id"),
        data.get("hire_date"),
        data.get("employment_status", "активний")
    )
    return execute_query(query, params)

def delete_employee(emp_id: int):
    return execute_query("DELETE FROM employees WHERE id = ?", (emp_id,))

# ---- KPI / статистика ----
def count_employees_total():
    row = fetch_all("SELECT COUNT(*) AS cnt FROM employees")[0]
    return row["cnt"]

def count_employees_hired_last_30d():
    row = fetch_all("""
        SELECT COUNT(*) AS cnt
        FROM employees
        WHERE hire_date IS NOT NULL
          AND DATE(hire_date) >= DATE('now','-30 day')
    """)[0]
    return row["cnt"]

def count_employees_dismissed_last_30d():
    row = fetch_all("""
        SELECT COUNT(*) AS cnt
        FROM employees
        WHERE dismissal_date IS NOT NULL
          AND DATE(dismissal_date) >= DATE('now','-30 day')
    """)[0]
    return row["cnt"]

def count_departments():
    row = fetch_all("SELECT COUNT(*) AS cnt FROM departments")[0]
    return row["cnt"]






def get_employee_raw(emp_id: int):
    """Повертає поля з таблиці employees для редагування."""
    rows = fetch_all("""
        SELECT id, last_name, first_name, IFNULL(middle_name,'') AS middle_name,
               birth_date, email, phone, department_id, position_id,
               hire_date, dismissal_date, employment_status
        FROM employees
        WHERE id = ?
    """, (emp_id,))
    return rows[0] if rows else None


def update_employee(emp_id: int, data: dict):
    """Оновлює базові дані співробітника."""
    return execute_query("""
        UPDATE employees
        SET last_name = ?, first_name = ?, middle_name = ?,
            birth_date = ?, email = ?, phone = ?,
            department_id = ?, position_id = ?,
            hire_date = ?, employment_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        data.get("last_name"),
        data.get("first_name"),
        data.get("middle_name"),
        data.get("birth_date"),
        data.get("email"),
        data.get("phone"),
        data.get("department_id"),
        data.get("position_id"),
        data.get("hire_date"),
        data.get("employment_status"),
        emp_id
    ))


def get_positions_by_department(department_id: int):
    """Повертає посади, дозволені для конкретного відділення."""
    return fetch_all("""
        SELECT p.id, p.name
        FROM department_positions dp
        JOIN positions p ON p.id = dp.position_id
        WHERE dp.department_id = ?
        ORDER BY p.name
    """, (department_id,))

def is_position_allowed_for_department(position_id: int, department_id: int) -> bool:
    """Чи дозволена ця посада в цьому відділенні?"""
    row = fetch_all("""
        SELECT COUNT(*) AS cnt
        FROM department_positions
        WHERE department_id = ? AND position_id = ?
    """, (department_id, position_id))[0]
    return row["cnt"] > 0








# ======== Departments helpers ========
def rename_department(department_id: int, new_name: str):
    return execute_query("UPDATE departments SET name = ? WHERE id = ?", (new_name, department_id))

def count_employees_in_department(department_id: int) -> int:
    row = fetch_all("SELECT COUNT(*) AS cnt FROM employees WHERE department_id = ?", (department_id,))[0]
    return row["cnt"]

# ======== Positions helpers ========
def rename_position(position_id: int, new_name: str):
    return execute_query("UPDATE positions SET name = ? WHERE id = ?", (new_name, position_id))

def count_employees_in_position(position_id: int) -> int:
    row = fetch_all("SELECT COUNT(*) AS cnt FROM employees WHERE position_id = ?", (position_id,))[0]
    return row["cnt"]

# Повний список посад (для режиму "Усі посади" у довідниках)
def get_all_positions():
    return fetch_all("SELECT id, name FROM positions ORDER BY name")

# Посади доступні для конкретного відділення (ти вже додав get_positions_by_department)
# def get_positions_by_department(department_id: int): ... (вже є)

# Додати/видалити звʼязок pos ↔ dep (щоб керувати доступністю посад у відділеннях – згодом)
def link_position_to_department(position_id: int, department_id: int):
    return execute_query(
        "INSERT OR IGNORE INTO department_positions (department_id, position_id) VALUES (?, ?)",
        (department_id, position_id)
    )

def unlink_position_from_department(position_id: int, department_id: int):
    return execute_query(
        "DELETE FROM department_positions WHERE department_id = ? AND position_id = ?",
        (department_id, position_id)
    )







def get_users():
    return fetch_all("""
        SELECT
            u.id,
            u.username,
            u.role,
            u.is_active,
            u.created_at,
            u.employee_id,
            -- ПІБ
            TRIM(COALESCE(e.last_name,'') || ' ' || COALESCE(e.first_name,'')) AS full_name,
            -- Відділення / Посада
            d.name AS department_name,
            p.name AS position_name
        FROM users u
        LEFT JOIN employees  e ON e.id = u.employee_id
        LEFT JOIN departments d ON d.id = e.department_id
        LEFT JOIN positions   p ON p.id = e.position_id
        ORDER BY u.username
    """)









def _conn():
    return sqlite3.connect(DB_PATH)

def get_employee_brief_list():
    """
    Повертає [(id, "Прізвище Ім'я По-батькові"), ...] для випадаючого списку.
    """
    con = _conn()
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    rows = cur.execute("""
        SELECT e.id,
               e.last_name || ' ' || e.first_name || ' ' || IFNULL(e.middle_name,'') AS full_name
        FROM employees e
        ORDER BY e.last_name, e.first_name
    """).fetchall()
    con.close()
    return [(r["id"], r["full_name"].strip()) for r in rows]

def get_employee_min(employee_id: int):
    """
    Мінімальний профіль працівника для підстановки в шаблон.
    """
    con = _conn()
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    row = cur.execute("""
        SELECT e.id, e.last_name, e.first_name, IFNULL(e.middle_name,'') AS middle_name,
               d.name AS department_name, p.name AS position_name
        FROM employees e
        JOIN departments d ON d.id = e.department_id
        JOIN positions   p ON p.id = e.position_id
        WHERE e.id=?
    """, (employee_id,)).fetchone()
    con.close()
    if not row:
        raise RuntimeError("Працівника не знайдено")
    return dict(row)

def create_document_with_preview(employee_id: int, doc_type: str, title: str,
                                 context: dict, created_by: str,
                                 template_path: str, out_dir: str):
    """
    1) створює запис у documents (draft)
    2) рендерить чернетку DOCX з контексту
    3) оновлює file_docx
    """
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    con = _conn()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO documents (employee_id, type, title, status, created_by, context_json)
        VALUES (?, ?, ?, 'draft', ?, ?)
    """, (employee_id, doc_type, title, created_by, json.dumps(context, ensure_ascii=False)))
    doc_id = cur.lastrowid

    # DOCX draft
    out_path = out_dir / f"emp_{employee_id:04d}_doc_{doc_id:06d}_draft.docx"
    tpl = DocxTemplate(template_path)
    tpl.render(context)
    tpl.save(out_path)

    cur.execute("UPDATE documents SET file_docx=? WHERE id=?", (str(out_path), doc_id))
    con.commit(); con.close()
    return doc_id, str(out_path)

def list_documents(search: str = None, status: str = None):
    con = _conn()
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    base = """
        SELECT d.id, d.type, d.title, d.status, d.created_at,
               d.signed_by, d.signed_at, d.file_docx,
               (e.last_name || ' ' || e.first_name || ' ' || IFNULL(e.middle_name,'')) AS employee_name
        FROM documents d
        LEFT JOIN employees e ON e.id = d.employee_id
        WHERE 1=1
    """
    params = []
    if status:
        base += " AND d.status = ?"
        params.append(status)
    if search:
        like = f"%{search}%"
        base += " AND (d.title LIKE ? OR d.type LIKE ? OR employee_name LIKE ?)"
        params.extend([like, like, like])
    base += " ORDER BY d.created_at DESC"

    rows = cur.execute(base, params).fetchall()
    con.close()
    return [dict(r) for r in rows]

def update_document_status(doc_id: int, new_status: str):
    con = _conn(); cur = con.cursor()
    cur.execute("UPDATE documents SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (new_status, doc_id))
    con.commit(); con.close()

def get_document(doc_id: int):
    con = _conn(); con.row_factory = sqlite3.Row; cur = con.cursor()
    row = cur.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    con.close()
    return dict(row) if row else {}





def create_document_with_preview(employee_id: int, doc_type: str, title: str,
                                 context: dict, created_by: str,
                                 template_path: str, out_dir: str,
                                 status_on_create: str = "draft"):
    """
    1) створює запис у documents зі status_on_create ('sent' для авто-відправки)
    2) рендерить чернетку DOCX з контексту
    3) оновлює file_docx
    """
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    con = _conn(); cur = con.cursor()

    cur.execute("""
        INSERT INTO documents (employee_id, type, title, status, created_by, context_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (employee_id, doc_type, title, status_on_create, created_by, json.dumps(context, ensure_ascii=False)))
    doc_id = cur.lastrowid

    out_path = out_dir / f"emp_{employee_id:04d}_doc_{doc_id:06d}_draft.docx"
    tpl = DocxTemplate(template_path)
    tpl.render(context)
    tpl.save(out_path)

    cur.execute("UPDATE documents SET file_docx=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (str(out_path), doc_id))
    con.commit(); con.close()
    return doc_id, str(out_path)




# --- Довідники ---
def get_departments_list():
    con = _conn(); con.row_factory = sqlite3.Row; cur = con.cursor()
    rows = cur.execute("SELECT id, name FROM departments ORDER BY name").fetchall()
    con.close()
    return [dict(r) for r in rows]

def get_positions_by_department(department_id: int):
    con = _conn(); con.row_factory = sqlite3.Row; cur = con.cursor()
    rows = cur.execute("""
        SELECT p.id, p.name
        FROM positions p
        JOIN department_positions dp ON dp.position_id = p.id
        WHERE dp.department_id = ?
        ORDER BY p.name
    """, (department_id,)).fetchall()
    con.close()
    return [dict(r) for r in rows]

def get_employee_by_email(email: str):
    con = _conn(); con.row_factory = sqlite3.Row; cur = con.cursor()
    row = cur.execute("SELECT * FROM employees WHERE email = ?", (email,)).fetchone()
    con.close()
    return dict(row) if row else None

def create_employee_minimal(last_name: str, first_name: str, middle_name: str,
                            email: str, phone: str, department_id: int, position_id: int):
    con = _conn(); cur = con.cursor()
    cur.execute("""
        INSERT INTO employees(last_name, first_name, middle_name, email, phone, department_id, position_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (last_name, first_name, middle_name, email, phone, department_id, position_id))
    emp_id = cur.lastrowid
    con.commit(); con.close()
    return emp_id

def create_user_for_employee(username: str, password: str, role: str, employee_id: int):
    con = _conn(); cur = con.cursor()
    cur.execute("""
        INSERT INTO users(username, password, role, is_active, employee_id)
        VALUES (?, ?, ?, 1, ?)
    """, (username, password, role, employee_id))
    con.commit(); con.close()

def suggest_username(email: str, last_name: str, first_name: str) -> str:
    if email and "@" in email:
        return email.split("@", 1)[0]
    base = (last_name[:10] + "_" + first_name[:1]).lower()
    return base




def today_iso():
    """Сьогоднішня дата у форматі YYYY-MM-DD."""
    return date.today().isoformat()

# === App settings (глобальні налаштування) ===
def get_setting(key: str):
    """
    Повертає значення з таблиці app_settings за ключем (або None, якщо нема).
    Очікується таблиця:
      app_settings(key TEXT PRIMARY KEY, value TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """
    row = fetch_one("SELECT value FROM app_settings WHERE key = ?", (key,))
    return row["value"] if row else None


def get_next_p1_order_number():
    """
    Повертає наступний номер П-1 у форматі 'N/YYYY'.
    Читаємо останній з documents.context_json → $.order_number.
    """
    y = date.today().year
    row = fetch_one(
        """
        SELECT COALESCE(
            MAX(
                CAST(
                    SUBSTR(
                        json_extract(context_json, '$.order_number'),
                        1,
                        INSTR(json_extract(context_json, '$.order_number'), '/') - 1
                    ) AS INTEGER
                )
            ),
            0
        ) AS max_seq
        FROM documents
        WHERE type = 'P1'
          AND json_extract(context_json, '$.order_number') LIKE ?
        """,
        (f'%/{y}',)
    )
    next_seq = (row["max_seq"] if row else 0) + 1
    return f"{next_seq}/{y}"


def get_next_p4_order_number():
    """
    Повертає наступний номер П-4 у форматі 'N/YYYY', шукаючи в documents.context_json → $.order_number
    для type='P4' у поточному році.
    """
    y = date.today().year
    row = fetch_one(
        """
        SELECT COALESCE(
            MAX(
                CAST(
                    SUBSTR(
                        json_extract(context_json, '$.order_number'),
                        1,
                        INSTR(json_extract(context_json, '$.order_number'), '/') - 1
                    ) AS INTEGER
                )
            ),
            0
        ) AS max_seq
        FROM documents
        WHERE type = 'P4'
          AND json_extract(context_json, '$.order_number') LIKE ?
        """,
        (f'%/{y}',)
    )
    next_seq = (row["max_seq"] if row else 0) + 1
    return f"{next_seq}/{y}"


def get_next_training_order_number():
    """
    Повертає наступний номер для направлення на підвищення кваліфікації у форматі 'N/YYYY'.
    Шукає у documents.context_json → $.order_number для type='TRAINING' у поточному році.
    """
    y = date.today().year
    row = fetch_one(
        """
        SELECT COALESCE(
            MAX(
                CAST(
                    SUBSTR(
                        json_extract(context_json, '$.order_number'),
                        1,
                        INSTR(json_extract(context_json, '$.order_number'), '/') - 1
                    ) AS INTEGER
                )
            ),
            0
        ) AS max_seq
        FROM documents
        WHERE type = 'TRAINING'
          AND json_extract(context_json, '$.order_number') LIKE ?
        """,
        (f'%/{y}',)
    )
    next_seq = (row["max_seq"] if row else 0) + 1
    return f"{next_seq}/{y}"

def get_next_vacation_order_number():
    """
    Повертає наступний номер наказу про відпустку у форматі 'N/YYYY',
    шукаючи в documents.context_json → $.order_number для type='VACATION' у поточному році.
    """
    y = date.today().year
    row = fetch_one(
        """
        SELECT COALESCE(
            MAX(
                CAST(
                    SUBSTR(
                        json_extract(context_json, '$.order_number'),
                        1,
                        INSTR(json_extract(context_json, '$.order_number'), '/') - 1
                    ) AS INTEGER
                )
            ),
            0
        ) AS max_seq
        FROM documents
        WHERE type = 'VACATION'
          AND json_extract(context_json, '$.order_number') LIKE ?
        """,
        (f'%/{y}',)
    )
    next_seq = (row["max_seq"] if row else 0) + 1
    return f"{next_seq}/{y}"

def get_next_attestation_order_number():
    """
    Наступний номер для наказу 'ATTESTATION' у форматі 'N/YYYY'
    (рахуємо тільки в межах поточного року за даними documents.context_json → $.order_number).
    """
    y = date.today().year
    row = fetch_one(
        """
        SELECT COALESCE(
            MAX(
                CAST(
                    SUBSTR(
                        json_extract(context_json, '$.order_number'),
                        1,
                        INSTR(json_extract(context_json, '$.order_number'), '/') - 1
                    ) AS INTEGER
                )
            ),
            0
        ) AS max_seq
        FROM documents
        WHERE type = 'ATTESTATION'
          AND json_extract(context_json, '$.order_number') LIKE ?
        """,
        (f'%/{y}',)
    )
    next_seq = (row["max_seq"] if row else 0) + 1
    return f"{next_seq}/{y}"






def order_number_exists_p1(order_no: str) -> bool:
    """
    Чи існує вже такий номер у П-1 (у context_json)?
    """
    row = fetch_one(
        """
        SELECT COUNT(*) AS c
        FROM documents
        WHERE type = 'P1'
          AND json_extract(context_json, '$.order_number') = ?
        """,
        (order_no,)
    )
    return (row and row["c"] > 0)





# ===== Internships =====
def list_internships(status: str | None = None, search: str | None = None):
    q = """
        SELECT i.id, i.employee_id, i.start_date, i.months,
               i.planned_end_date, i.status, IFNULL(i.notes,'') AS notes,
               (e.last_name || ' ' || e.first_name || ' ' || IFNULL(e.middle_name,'')) AS full_name,
               d.name AS department_name, p.name AS position_name
        FROM internships i
        JOIN employees e ON e.id = i.employee_id
        LEFT JOIN departments d ON d.id = e.department_id
        LEFT JOIN positions   p ON p.id = e.position_id
        WHERE 1=1
    """
    params = []
    if status and status != "усі":
        q += " AND i.status = ?"
        params.append(status)
    if search:
        like = f"%{search}%"
        q += " AND (full_name LIKE ? OR IFNULL(d.name,'') LIKE ? OR IFNULL(p.name,'') LIKE ?)"
        params.extend([like, like, like])
    q += " ORDER BY i.status DESC, i.planned_end_date ASC"
    return fetch_all(q, tuple(params))


def auto_complete_overdue():
    """Усі active з простроченим planned_end_date → completed."""
    return execute_query("""
        UPDATE internships
           SET status='completed', updated_at=CURRENT_TIMESTAMP
         WHERE status='active' AND DATE(planned_end_date) < DATE('now')
    """)


def extend_internship(internship_id: int, add_months: int, note: str = ""):
    """+N місяців до planned_end_date; статус лишається active."""
    return execute_query("""
        UPDATE internships
           SET months = months + ?,
               planned_end_date = DATE(planned_end_date, '+' || ? || ' months'),
               notes = TRIM(COALESCE(notes,'') || CASE WHEN ?='' THEN '' ELSE CHAR(10) || ? END),
               updated_at = CURRENT_TIMESTAMP
         WHERE id = ? AND status = 'active'
    """, (add_months, add_months, note, note, internship_id))


def complete_internship_now(internship_id: int, note: str = ""):
    return execute_query("""
        UPDATE internships
           SET status='completed',
               notes = TRIM(COALESCE(notes,'') || CASE WHEN ?='' THEN '' ELSE CHAR(10) || ? END),
               updated_at=CURRENT_TIMESTAMP
         WHERE id = ? AND status='active'
    """, (note, note, internship_id))


def fail_internship(internship_id: int, note: str = ""):
    return execute_query("""
        UPDATE internships
           SET status='failed',
               notes = TRIM(COALESCE(notes,'') || CASE WHEN ?='' THEN '' ELSE CHAR(10) || ? END),
               updated_at=CURRENT_TIMESTAMP
         WHERE id = ? AND status='active'
    """, (note, note, internship_id))


def auto_complete_overdue() -> int:
    """
    Завершує всі активні стажування, у яких planned_end_date < сьогодні.
    Повертає кількість оновлених рядків.
    """
    from contextlib import closing
    with closing(sqlite3.connect(DB_PATH)) as con, closing(con.cursor()) as cur:
        cur.execute("""
            UPDATE internships
            SET status = 'completed',
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'active'
              AND DATE(planned_end_date) < DATE('now')
        """)
        con.commit()
        return cur.rowcount or 0


# лічильники
def internships_overdue_count():
    row = fetch_one("""
        SELECT COUNT(*) AS c
        FROM internships
        WHERE status='active' AND DATE(planned_end_date) < DATE('now')
    """)
    return row["c"] if row else 0

def internships_soon_count():
    row = fetch_one("""
        SELECT COUNT(*) AS c
        FROM internships
        WHERE status='active'
          AND DATE(planned_end_date) BETWEEN DATE('now') AND DATE('now','+14 day')
    """)
    return row["c"] if row else 0

def docs_sent_count():
    row = fetch_one("""
        SELECT COUNT(*) AS c
        FROM documents
        WHERE status='sent'
    """)
    return row["c"] if row else 0



def get_employee_brief_list_by_department(dep_id: int):
    """
    Повертає список [(id, 'Прізвище Імʼя По батькові'), ...] тільки для вказаного відділення,
    лише активні працівники.
    """
    if not dep_id:
        return []
    rows = fetch_all("""
        SELECT e.id,
               TRIM(
                 COALESCE(e.last_name,'') || ' ' || COALESCE(e.first_name,'') ||
                 CASE WHEN IFNULL(e.middle_name,'')<>'' THEN ' '||e.middle_name ELSE '' END
               ) AS full_name
        FROM employees e
        WHERE e.department_id = ?
          AND e.employment_status = 'активний'
        ORDER BY e.last_name, e.first_name, e.middle_name
    """, (dep_id,))
    # уніфікуємо формат під [(id, name), ...]
    return [(r["id"], r["full_name"]) for r in rows]





def add_attestation_plan_for_new_employee(employee_id: int, hire_date_iso: str | None, created_by: str):
    """
    Створює запис у attestations_plan:
      - action='confirmation' (підтвердження)
      - schedule='planned'    (планова)
      - planned_date = hire_date + 5 років (або від сьогодні, якщо hire_date порожня)
    Повертає id вставленого рядка.
    """
    if not hire_date_iso:
        hire_date_iso = date.today().isoformat()

    return execute_query("""
        INSERT INTO attestations_plan
            (employee_id, action, schedule, planned_date,
             commission_name, commission_place, basis_text,
             document_id, created_by)
        VALUES (?, 'confirmation', 'planned', DATE(?, '+5 years'),
                NULL, NULL, NULL,
                NULL, ?)
    """, (employee_id, hire_date_iso, created_by))


# === Attestations: find due without document =================================
def list_attestations_due_without_doc(days: int = 30):
    """
    Кого потрібно автоматично направити на атестацію:
    - у плані немає document_id
    - planned_date у діапазоні [сьогодні ; сьогодні + days]
    - працівник активний
    Повертає масив dict (поля з ap + ПІБ/посада/відділення).
    """
    return fetch_all("""
        SELECT
            ap.id,
            ap.employee_id,
            ap.action,
            ap.schedule,
            ap.planned_date,
            IFNULL(ap.commission_name,'')  AS commission_name,
            IFNULL(ap.commission_place,'') AS commission_place,
            IFNULL(ap.basis_text,'')       AS basis_text,
            -- мета по працівнику
            (e.last_name || ' ' || e.first_name ||
             CASE WHEN IFNULL(e.middle_name,'')<>'' THEN ' '||e.middle_name ELSE '' END
            ) AS employee_name,
            d.name AS department_name,
            p.name AS position_name
        FROM attestations_plan ap
        JOIN employees e     ON e.id = ap.employee_id
        LEFT JOIN departments d ON d.id = e.department_id
        LEFT JOIN positions   p ON p.id = e.position_id
        WHERE ap.document_id IS NULL
          AND e.employment_status = 'активний'
          AND DATE(ap.planned_date) BETWEEN DATE('now') AND DATE('now','+' || ? || ' day')
        ORDER BY ap.planned_date ASC, employee_name ASC
    """, (days,))






def get_department_head_by_department(department_id: int):
    """
    Повертає dict з даними завідувача відділення (id, full_name) для заданого department_id
    або None, якщо не знайдено.
    """
    if not department_id:
        return None

    row = fetch_one("""
        SELECT 
            e.id,
            TRIM(
                COALESCE(e.last_name, '') || ' ' ||
                COALESCE(e.first_name, '') || ' ' ||
                COALESCE(e.middle_name, '')
            ) AS full_name
        FROM employees e
        JOIN positions p ON p.id = e.position_id
        WHERE e.department_id = ?
          AND p.name = 'Завідувач відділення'
          AND (e.employment_status IS NULL OR e.employment_status <> 'звільнений')
        ORDER BY e.id
        LIMIT 1
    """, (department_id,))

    return row  # або None

def get_department_head_for_employee(employee_id: int):
    """
    Повертає dict з даними завідувача відділення для конкретного працівника:
    { "id": ..., "full_name": ... } або None.
    """
    if not employee_id:
        return None

    emp = fetch_one("""
        SELECT department_id
        FROM employees
        WHERE id = ?
    """, (employee_id,))
    if not emp or not emp.get("department_id"):
        return None

    return get_department_head_by_department(emp["department_id"])

def get_internship_evaluations(internship_id: int):
    return fetch_all(
        """
        SELECT *
        FROM internship_evaluations
        WHERE internship_id = ?
        ORDER BY period_no ASC, created_at ASC
        """,
        (internship_id,)
    )

def save_internship_evaluation(
    internship_id: int,
    period_no: int,
    data: dict,
    created_by: str | None = None,
) -> int:
    """
    Створює або оновлює оцінку за конкретний період стажування.

    Очікує, що в data МАЮТЬ/МОЖУТЬ бути ключі:
      - period_start (YYYY-MM-DD або None)
      - period_end   (YYYY-MM-DD або None)
      - score_professional
      - score_discipline
      - score_communication
      - score_growth
      - total_score
      - recommendation
      - comment

    Повертає id запису в internship_evaluations.
    """
    created_by = created_by or "dept_head"

    # Перевіряємо, чи вже є запис для цього стажування та періоду
    row = fetch_one(
        """
        SELECT id
        FROM internship_evaluations
        WHERE internship_id = ? AND period_no = ?
        """,
        (internship_id, period_no)
    )

    params = {
        "internship_id":      internship_id,
        "period_no":          period_no,
        "period_start":       data.get("period_start"),
        "period_end":         data.get("period_end"),
        "score_professional": data.get("score_professional"),
        "score_discipline":   data.get("score_discipline"),
        "score_communication": data.get("score_communication"),
        "score_growth":       data.get("score_growth"),
        "total_score":        data.get("total_score"),
        "recommendation":     data.get("recommendation") or "",
        "comment":            data.get("comment") or "",
        "created_by":         created_by,
    }

    if row:
        # UPDATE існуючого запису (created_at/created_by не чіпаємо)
        eval_id = row["id"]
        execute_query(
            """
            UPDATE internship_evaluations
            SET
                period_start        = :period_start,
                period_end          = :period_end,
                score_professional  = :score_professional,
                score_discipline    = :score_discipline,
                score_communication = :score_communication,
                score_growth        = :score_growth,
                total_score         = :total_score,
                recommendation      = :recommendation,
                comment             = :comment
            WHERE id = ?
            """,
            {**params, "id": eval_id}
        )
        return eval_id
    else:
        # INSERT нового запису
        eval_id = execute_query(
            """
            INSERT INTO internship_evaluations (
                internship_id,
                period_no,
                period_start,
                period_end,
                score_professional,
                score_discipline,
                score_communication,
                score_growth,
                total_score,
                recommendation,
                comment,
                created_by
            ) VALUES (
                :internship_id,
                :period_no,
                :period_start,
                :period_end,
                :score_professional,
                :score_discipline,
                :score_communication,
                :score_growth,
                :total_score,
                :recommendation,
                :comment,
                :created_by
            )
            """,
            params
        )
        return eval_id


# === Internship evaluation helpers ===

def _get_internship_formula_defaults():
    # дефолтні ваги та пороги; згодом зʼєднаємо з app_settings
    return {
        "weights": {
            "professional": 0.40,
            "discipline":   0.25,
            "communication":0.20,
            "growth":       0.15,
        },
        "thresholds": {
            "hire":   75.0,
            "extend": 60.0,
        }
    }

def calc_internship_total_and_recommendation(score_prof, score_disc, score_comm, score_growth):
    # можна буде зчитувати з app_settings; зараз дефолти
    cfg = _get_internship_formula_defaults()
    w = cfg["weights"]; thr = cfg["thresholds"]

    # шкала 1..5 → нормалізуємо до 100
    total = 100.0 * (
        w["professional"] * float(score_prof) +
        w["discipline"]   * float(score_disc) +
        w["communication"]* float(score_comm) +
        w["growth"]       * float(score_growth)
    ) / 5.0
    total = round(total, 2)

    if total >= thr["hire"]:
        rec = "hire"
    elif total >= thr["extend"]:
        rec = "extend"
    else:
        rec = "deny"
    return total, rec


def upsert_internship_evaluation(
    internship_id: int,
    period_no: int,
    score_professional: float,
    score_discipline: float,
    score_communication: float,
    score_growth: float,
    comment: str | None,
    created_by: str | None,
    period_start: str | None = None,   # YYYY-MM-DD
    period_end: str | None = None      # YYYY-MM-DD
) -> int:
    """Створити або оновити оцінку за період. Повертає id запису."""
    total, rec = calc_internship_total_and_recommendation(
        score_professional, score_discipline, score_communication, score_growth
    )

    existing = fetch_one(
        "SELECT id FROM internship_evaluations WHERE internship_id = ? AND period_no = ?",
        (internship_id, period_no)
    )

    if existing and existing.get("id"):
        eval_id = int(existing["id"])
        execute_query(
            """
            UPDATE internship_evaluations
            SET period_start = :period_start,
                period_end   = :period_end,
                score_professional  = :sp,
                score_discipline    = :sd,
                score_communication = :sc,
                score_growth        = :sg,
                total_score         = :total,
                recommendation      = :rec,
                comment             = :comment
            WHERE id = :id
            """,
            {
                "period_start": period_start,
                "period_end":   period_end,
                "sp": score_professional,
                "sd": score_discipline,
                "sc": score_communication,
                "sg": score_growth,
                "total": total,
                "rec": rec,
                "comment": comment or "",
                "id": eval_id,
            }
        )
        return eval_id
    else:
        return execute_query(
            """
            INSERT INTO internship_evaluations(
                internship_id, period_no, period_start, period_end,
                score_professional, score_discipline, score_communication, score_growth,
                total_score, recommendation, comment, created_by
            ) VALUES (
                :internship_id, :period_no, :period_start, :period_end,
                :sp, :sd, :sc, :sg,
                :total, :rec, :comment, :created_by
            )
            """,
            {
                "internship_id": internship_id,
                "period_no": period_no,
                "period_start": period_start,
                "period_end":   period_end,
                "sp": score_professional,
                "sd": score_discipline,
                "sc": score_communication,
                "sg": score_growth,
                "total": total,
                "rec": rec,
                "comment": comment or "",
                "created_by": created_by or "",
            }
        )






def get_internship_employee_id(internship_id: int) -> int | None:
    row = fetch_one("SELECT employee_id FROM internships WHERE id = ?", (internship_id,))
    return int(row["employee_id"]) if row and row.get("employee_id") is not None else None


def outcome_hire(internship_id: int,
                 decided_by: str,
                 final_score: float | None,
                 final_recommendation: str | None,
                 comment: str | None = None):
    """
    Завершити стажування позитивно: позначити internship як 'completed',
    зафіксувати outcome; статус працівника гарантуємо 'активний'.
    """
    emp_id = get_internship_employee_id(internship_id)
    if emp_id is None:
        raise RuntimeError("Не знайдено працівника для стажування.")

    # 1) статус стажування -> completed
    execute_query(
        "UPDATE internships SET status='completed', updated_at=CURRENT_TIMESTAMP WHERE id = ?",
        (internship_id,)
    )

    # 2) статус працівника (на всяк випадок гарантуємо 'активний')
    execute_query(
        "UPDATE employees SET employment_status = 'активний' WHERE id = ?",
        (emp_id,)
    )

    # 3) журнал outcome
    execute_query(
        """
        INSERT INTO internship_outcomes
            (internship_id, decision, final_total_score, final_recommendation, comment, decided_by)
        VALUES (?, 'hire', ?, ?, ?, ?)
        """,
        (internship_id, final_score, final_recommendation, comment, decided_by)
    )


def outcome_decline(internship_id: int,
                    decided_by: str,
                    final_score: float | None,
                    final_recommendation: str | None,
                    comment: str | None = None):
    """
    Завершити стажування відмовою: internship -> 'completed',
    працівника позначити 'звільнений', зафіксувати outcome.
    """
    emp_id = get_internship_employee_id(internship_id)
    if emp_id is None:
        raise RuntimeError("Не знайдено працівника для стажування.")

    execute_query(
        "UPDATE internships SET status='completed', updated_at=CURRENT_TIMESTAMP WHERE id = ?",
        (internship_id,)
    )

    execute_query(
        "UPDATE employees SET employment_status = 'звільнений' WHERE id = ?",
        (emp_id,)
    )

    execute_query(
        """
        INSERT INTO internship_outcomes
            (internship_id, decision, final_total_score, final_recommendation, comment, decided_by)
        VALUES (?, 'decline', ?, ?, ?, ?)
        """,
        (internship_id, final_score, final_recommendation, comment, decided_by)
    )


def outcome_extend(internship_id: int,
                   months_to_add: int,
                   decided_by: str,
                   comment: str | None = None):
    """
    Подовжити стажування на N місяців: збільшити i.months, пересунути planned_end_date,
    outcome = 'extend'. Статус лишається 'active'.
    """
    if months_to_add <= 0:
        raise ValueError("Кількість місяців для подовження має бути > 0.")

    # 1) збільшуємо months і зміщуємо дату завершення
    execute_query(
        """
        UPDATE internships
        SET months = COALESCE(months,0) + :add,
            planned_end_date = DATE(planned_end_date, '+' || :add || ' months'),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = :iid
        """,
        {"add": months_to_add, "iid": internship_id}
    )

    # 2) журнал outcome
    execute_query(
        """
        INSERT INTO internship_outcomes
            (internship_id, decision, extend_months, comment, decided_by)
        VALUES (?, 'extend', ?, ?, ?)
        """,
        (internship_id, months_to_add, comment, decided_by)
    )
