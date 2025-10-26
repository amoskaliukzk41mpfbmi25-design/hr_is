# src/employee_main_window.py
import customtkinter as ctk
from tkinter import messagebox
import db_manager as db
from docxtpl import DocxTemplate
from pathlib import Path
import os, sys, subprocess, json

TEMPLATES_MAP = {
    "P1": Path("data/templates/hire_order_P1.docx"),  # ← за потреби змінити назву файла шаблону
    "P4": Path("data/templates/dismissal_order_P4.docx"),  
    "INTERNSHIP_REFERRAL": Path("data/templates/internship_assignment.docx"),
    "TRAINING": Path("data/templates/training_referral.docx"),
    "VACATION": Path("data/templates/vacation_order.docx"), 
}



TMP_DIR = Path("data/tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)

DOCS_DIR = Path("data/documents")
DOCS_DIR.mkdir(parents=True, exist_ok=True)



class EmployeeMainWindow(ctk.CTk):
    """
    Головне вікно для ролі 'employee'.
    Поки реалізована тільки вкладка 'Профіль' (перегляд даних працівника).
    Очікує current_user з ключами: {"username": "...", "role": "employee", "employee_id": int?}
    """
    def __init__(self, current_user: dict):
        super().__init__()
        self.title("Кабінет працівника | Інформаційна система лікарні")
        self.minsize(900, 600)
        self.state("zoomed")
        self.after(0, lambda: self.state("zoomed"))

        self.current_user = current_user or {}
        if self.current_user.get("role") != "employee":
            messagebox.showerror("Доступ", "Це вікно лише для ролі 'employee'.")
            self.destroy()
            return

        # ---- Визначаємо employee_id ----
        self.employee_id = self.current_user.get("employee_id")
        if not self.employee_id:
            # Якщо не передали employee_id — знайдемо за username
            u = db.fetch_one("SELECT id, employee_id FROM users WHERE username=? LIMIT 1",
                             (self.current_user.get("username") or "",))
            if not u or not u.get("employee_id"):
                messagebox.showerror("Профіль", "Не вдається визначити профіль співробітника для цього користувача.")
                self.destroy()
                return
            self.employee_id = u["employee_id"]

        # ---- Tabview ----
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=16)

        self.tab_profile = self.tabview.add("Профіль")
        self.tab_docs = self.tabview.add("Документи")



        # ---- Профіль ----
        self._build_profile_tab()
        self.load_profile()

        # ---- Документи ----
        self._build_docs_tab()
        self.refresh_docs()

    # ===================== Профіль =====================
    def _build_profile_tab(self):
        wrap = ctk.CTkFrame(self.tab_profile, corner_radius=10)
        wrap.pack(fill="both", expand=True, padx=10, pady=10)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_columnconfigure(1, weight=2)

        # Заголовок і кнопки
        header = ctk.CTkFrame(wrap)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 4))
        ctk.CTkLabel(header, text="Мій профіль", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=6)
        ctk.CTkButton(header, text="Оновити", width=120, command=self.load_profile).pack(side="right", padx=6)

        # Лейбли полів (ліва колонка)
        labels = [
            ("ПІБ", "full_name"),
            ("Email", "email"),
            ("Телефон", "phone"),
            ("Відділення", "department_name"),
            ("Посада", "position_name"),
            ("Дата народження", "birth_date"),
            ("Дата прийняття", "hire_date"),
            ("Статус зайнятості", "employment_status"),
        ]
        self._profile_vars = {}
        for i, (title, key) in enumerate(labels, start=1):
            ctk.CTkLabel(wrap, text=title, anchor="w").grid(row=i, column=0, sticky="ew", padx=(12, 6), pady=6)
            var = ctk.StringVar(value="—")
            entry = ctk.CTkEntry(wrap, textvariable=var)
            entry.configure(state="disabled")
            entry.grid(row=i, column=1, sticky="ew", padx=(6, 12), pady=6)
            self._profile_vars[key] = var

        # Низ сторінки — примітка
        note = ctk.CTkLabel(
            wrap,
            text="За потреби змінити контактні дані зверніться до HR.",
            text_color=("#6B7280", "#CBD5E1")
        )
        note.grid(row=len(labels)+1, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 12))


        # ==== Стажування (коротка секція) ====
        sep = ctk.CTkFrame(wrap, height=2)
        sep.grid(row=len(labels)+2, column=0, columnspan=2, sticky="ew", padx=12, pady=(4,6))

        ctk.CTkLabel(wrap, text="Стажування", font=ctk.CTkFont(size=14, weight="bold"))\
            .grid(row=len(labels)+3, column=0, columnspan=2, sticky="w", padx=12, pady=(2,6))

        self._internship_vars = {
            "period": ctk.StringVar(value="—"),
            "mentor": ctk.StringVar(value="—"),
            "status": ctk.StringVar(value="—"),
        }

        rowi = len(labels)+4
        ctk.CTkLabel(wrap, text="Період", anchor="w")\
            .grid(row=rowi, column=0, sticky="ew", padx=(12,6), pady=4)
        e1 = ctk.CTkEntry(wrap, textvariable=self._internship_vars["period"]); e1.configure(state="disabled")
        e1.grid(row=rowi, column=1, sticky="ew", padx=(6,12), pady=4)

        rowi += 1
        ctk.CTkLabel(wrap, text="Наставник", anchor="w")\
            .grid(row=rowi, column=0, sticky="ew", padx=(12,6), pady=4)
        e2 = ctk.CTkEntry(wrap, textvariable=self._internship_vars["mentor"]); e2.configure(state="disabled")
        e2.grid(row=rowi, column=1, sticky="ew", padx=(6,12), pady=4)

        rowi += 1
        ctk.CTkLabel(wrap, text="Статус", anchor="w")\
            .grid(row=rowi, column=0, sticky="ew", padx=(12,6), pady=4)
        e3 = ctk.CTkEntry(wrap, textvariable=self._internship_vars["status"]); e3.configure(state="disabled")
        e3.grid(row=rowi, column=1, sticky="ew", padx=(6,12), pady=4)

        rowi += 1
        self.btn_preview_intern = ctk.CTkButton(
            wrap, text="Переглянути направлення", width=240, command=self.preview_internship_doc
        )
        self.btn_preview_intern.grid(row=rowi, column=1, sticky="e", padx=(6,12), pady=(6,12))


        rowi += 1
        # Інфо-рядок про відпустку (ховаємо за замовчуванням)
        self._vacation_note_var = ctk.StringVar(value="")
        self.vacation_note = ctk.CTkLabel(
            wrap,
            textvariable=self._vacation_note_var,
            wraplength=720,
            # трішки помітніший колір, добре читається в обох темах
            text_color=("#b45309", "#fbbf24")   # помаранчевий у світлій / бурштин у темній
        )
        self.vacation_note.grid(row=rowi, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 12))
        self.vacation_note.grid_remove()  # поки що не показуємо



        # ==== Підвищення кваліфікації (нагадування) ====
        sep2 = ctk.CTkFrame(wrap, height=2)
        sep2.grid(row=rowi+1, column=0, columnspan=2, sticky="ew", padx=12, pady=(4,6))

        self.training_frame = ctk.CTkFrame(wrap, corner_radius=8)
        self.training_frame.grid(row=rowi+2, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 12))
        self.training_frame.grid_columnconfigure(0, weight=1)
        self.training_frame.grid_remove()  # спочатку приховано

        # Заголовок і бейджик-статус
        top_tr = ctk.CTkFrame(self.training_frame)
        top_tr.grid(row=0, column=0, sticky="ew", padx=10, pady=(8,4))
        top_tr.grid_columnconfigure(0, weight=1)

        self._tr_title_var = ctk.StringVar(value="")
        ctk.CTkLabel(top_tr, textvariable=self._tr_title_var, font=ctk.CTkFont(size=14, weight="bold"))\
            .grid(row=0, column=0, sticky="w")

        self._tr_badge_var = ctk.StringVar(value="")
        self._tr_badge = ctk.CTkLabel(top_tr, textvariable=self._tr_badge_var)
        self._tr_badge.grid(row=0, column=1, sticky="e", padx=(6,0))

        # Метадані (провайдер / формат / місце)
        self._tr_meta_var = ctk.StringVar(value="")
        ctk.CTkLabel(self.training_frame, textvariable=self._tr_meta_var)\
            .grid(row=1, column=0, sticky="w", padx=10)

        # Період і «залишилось N дн.»
        self._tr_period_var = ctk.StringVar(value="")
        ctk.CTkLabel(self.training_frame, textvariable=self._tr_period_var, text_color=("#6B7280", "#CBD5E1"))\
            .grid(row=2, column=0, sticky="w", padx=10, pady=(0,6))

        # Дії
        actions_tr = ctk.CTkFrame(self.training_frame)
        actions_tr.grid(row=3, column=0, sticky="e", padx=10, pady=(4,10))
        ctk.CTkButton(actions_tr, text="Переглянути", width=160, command=self.preview_training_doc)\
            .pack(side="right", padx=(6,0))
        # Кнопку "Підписати" додамо наступним кроком


    def _build_docs_tab(self):
        wrap = ctk.CTkFrame(self.tab_docs, corner_radius=10)
        wrap.pack(fill="both", expand=True, padx=10, pady=10)

        # Верхня панель: фільтр + оновити
        top = ctk.CTkFrame(wrap)
        top.pack(fill="x", padx=8, pady=(8, 6))

        ctk.CTkLabel(top, text="Статус:").pack(side="left", padx=(6, 6))
        self.docs_status_var = ctk.StringVar(value="sent")  # за замовчуванням показуємо "очікують підпису"
        self.docs_status_filter = ctk.CTkComboBox(
            top,
            values=["усі", "sent", "signed"],
            variable=self.docs_status_var,
            width=140,
            command=lambda _=None: self.refresh_docs()
        )
        self.docs_status_filter.pack(side="left")

        ctk.CTkButton(top, text="Оновити", width=120, command=self.refresh_docs).pack(side="right", padx=6)

        # Таблиця
        table = ctk.CTkFrame(wrap)
        table.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        from tkinter import ttk  # локальний імпорт, щоб не ламати існуючу структуру
        cols = ("id", "type", "title", "status", "created_at", "signed_at")
        self.docs_tree = ttk.Treeview(table, columns=cols, show="headings", height=18)
        headings = {
            "id": "ID",
            "type": "Тип",
            "title": "Назва",
            "status": "Статус",
            "created_at": "Створено",
            "signed_at": "Підписано",
        }
        for k, v in headings.items():
            self.docs_tree.heading(k, text=v)
            self.docs_tree.column(k, width=120 if k not in ("title",) else 300, stretch=True)
        self.docs_tree.pack(side="left", fill="both", expand=True)

        yscroll = ttk.Scrollbar(table, orient="vertical", command=self.docs_tree.yview)
        self.docs_tree.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side="right", fill="y")

        # Кнопки дій
        actions = ctk.CTkFrame(wrap)
        actions.pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkButton(actions, text="Переглянути", width=160, command=self.preview_selected_doc).pack(side="left", padx=6)
        
        # Підпис:
        self.btn_sign = ctk.CTkButton(actions, text="Підписати", width=120, command=self.sign_selected_doc)
        self.btn_sign.pack(side="left", padx=(6, 0))




    def load_profile(self):
        """
        Читає з БД дані працівника і підставляє у форму.
        """
        try:
            # Беремо максимально повний набір для відображення
            row = db.get_employee_raw(self.employee_id)  # повертає dict або None
            if not row:
                raise RuntimeError("Профіль не знайдено.")

            # Доведемо до зручних ключів для UI:
            full_name = " ".join(filter(None, [row.get("last_name"), row.get("first_name"), row.get("middle_name")])).strip()
            # Відділення/посада назвами:
            dep_pos = db.fetch_one("""
                SELECT d.name AS department_name, p.name AS position_name
                FROM employees e
                LEFT JOIN departments d ON d.id = e.department_id
                LEFT JOIN positions   p ON p.id = e.position_id
                WHERE e.id = ?
            """, (self.employee_id,))
            department_name = (dep_pos or {}).get("department_name") or "—"
            position_name   = (dep_pos or {}).get("position_name") or "—"

            data = {
                "full_name": full_name or "—",
                "email": row.get("email") or "—",
                "phone": row.get("phone") or "—",
                "department_name": department_name,
                "position_name": position_name,
                "birth_date": row.get("birth_date") or "—",
                "hire_date": row.get("hire_date") or "—",
                "employment_status": row.get("employment_status") or "—",
            }
            for k, v in data.items():
                self._profile_vars[k].set(v)

            # стажування
            self.load_internship_summary()
            self.load_training_reminder()
            self.load_vacation_note()



        except Exception as e:
            messagebox.showerror("Профіль", f"Не вдалося завантажити дані профілю: {e}")

    def refresh_docs(self):
        """
        Підтягує документи лише поточного працівника.
        Фільтр статусу: 'усі' | 'sent' | 'signed'
        """
        status = self.docs_status_var.get()
        where = "WHERE employee_id = ?"
        params = [self.employee_id]
        if status != "усі":
            where += " AND status = ?"
            params.append(status)

        rows = db.fetch_all(f"""
            SELECT id, type, title, status, created_at, signed_at
            FROM documents
            {where}
            ORDER BY created_at DESC
        """, tuple(params))

        # Очистити і заповнити таблицю
        for iid in self.docs_tree.get_children():
            self.docs_tree.delete(iid)

        # Якщо хочеш людську назву типу: можна підмінити тут або через JOIN документів і document_types
        TYPE_LABELS = {
            "P1": "П-1: Прийняття на роботу",
            "P4": "П-4: Звільнення",
            "INTERNSHIP_REFERRAL": "Направлення на стажування",
            "TRAINING": "Підвищення кваліфікації", 
            "VACATION": "Надання відпустки", 
        }

        for r in rows:
            show_type = TYPE_LABELS.get(r.get("type"), r.get("type"))
            self.docs_tree.insert("", "end", values=(
                r.get("id"), show_type, r.get("title"), r.get("status"),
                r.get("created_at") or "", r.get("signed_at") or ""
            ))

        try:
            self.load_training_reminder()
            self.load_vacation_note()
        except Exception:
            pass


    def _open_with_default_app(self, path: str):
        """Відкрити файл системним переглядачем кросплатформенно."""
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as e:
            messagebox.showerror("Перегляд", f"Не вдалося відкрити файл: {e}")

    def _render_preview_docx(self, doc_type: str, context: dict, employee_id: int, doc_id: int) -> str:
        """
        Генерує ТИМЧАСОВИЙ DOCX-прев'ю для документа працівника.
        Нормалізує payload під шаблон П-1:
        - department.name / position.name
        - hire_date_str / start_date_str / contract_until_str (ДД.ММ.РРРР)
        - чекбокси cb_*
        - salary/work/інші текстові поля
        - плейсхолдери підпису sign_employee_* і director_full_name
        Нічого не змінює в БД.
        """
        from datetime import datetime, date

        def fmt_dmy(iso: str | None) -> str:
            if not iso:
                return ""
            try:
                d = datetime.strptime(iso, "%Y-%m-%d")
                return f"{d.day:02d}.{d.month:02d}.{d.year}"
            except Exception:
                return iso  # якщо формат інший — повертаємо як є

        def cb(flag: bool) -> str:
            return "☑" if bool(flag) else "☐"

        tpl_path = TEMPLATES_MAP.get(doc_type)
        if not tpl_path or not tpl_path.exists():
            raise RuntimeError(f"Не знайдено шаблон для типу '{doc_type}'. Перевір TEMPLATES_MAP.")

        # --- вихідний payload із БД ---
        src = dict(context or {})
        emp = (src.get("employee") or {}) if isinstance(src.get("employee"), dict) else {}

        # --- нормалізований контекст під шаблон ---
        ctx = dict(src)

        # 1) Об'єкти з .name для {{ department.name }} і {{ position.name }}
        ctx.setdefault("department", {"name": emp.get("department_name", "")})
        ctx.setdefault("position",   {"name": emp.get("position_name", "")})

        # 2) ПІБ у плоских полях (на всякий випадок)
        ctx.setdefault("last_name",   emp.get("last_name", ""))
        ctx.setdefault("first_name",  emp.get("first_name", ""))
        ctx.setdefault("middle_name", emp.get("middle_name", ""))

        # 3) Рядкові дати з ISO → ДД.ММ.РРРР
        # hire_date_str у шапці (“від …”) — беремо з order_date, якщо є, інакше hire_date
        ctx.setdefault("hire_date_str",  fmt_dmy(src.get("order_date") or src.get("hire_date")))
        # start_date_str (“Прийняти на роботу з …”) — з hire_date
        ctx.setdefault("start_date_str", fmt_dmy(src.get("hire_date")))
        ctx.setdefault("contract_until_str", fmt_dmy(src.get("contract_until")))

        # 4) Чекбокси умов
        ctx["cb_competition"] = cb(src.get("is_competition"))
        ctx["cb_contract"]    = cb(src.get("is_contract"))
        ctx["cb_probation"]   = cb(src.get("is_probation"))
        ctx["cb_absence"]     = cb(src.get("is_absence"))
        ctx["cb_reserve"]     = cb(src.get("is_reserve"))
        ctx["cb_internship"]  = cb(src.get("is_internship"))
        ctx["cb_transfer"]    = cb(src.get("is_transfer"))
        ctx["cb_other"]       = cb(src.get("is_other"))

        is_main = bool(src.get("is_main_job"))
        ctx["cb_work_main"]      = cb(is_main)
        ctx["cb_work_secondary"] = cb(not is_main)
        # якщо треба — тут можна вивести логіку повного робочого часу
        ctx["cb_worktime_full"]  = cb(False)

        # 5) Текстові/числові поля
        ctx.setdefault("probation_months", src.get("probation_months", ""))
        ctx.setdefault("other_text",       src.get("other_text", ""))
        ctx.setdefault("work_hours",       src.get("work_hours", ""))
        ctx.setdefault("work_minutes",     src.get("work_minutes", ""))
        ctx.setdefault("salary_grn",       src.get("salary_grn", ""))
        ctx.setdefault("salary_kop",       src.get("salary_kop", ""))
        ctx.setdefault("order_number",     src.get("order_number", ""))

        # 6) Підпис працівника (для прев’ю порожньо)
        ctx.setdefault("employee_sign_day",   "")
        ctx.setdefault("employee_sign_month", "")
        ctx.setdefault("employee_sign_year",  "")

        # Якщо хочеш автодату в прев'ю:
        # t = date.today()
        # ctx.setdefault("sign_employee_day",   f"{t.day:02d}")
        # ctx.setdefault("sign_employee_month", f"{t.month:02d}")
        # ctx.setdefault("sign_employee_year",  f"{t.year}")

        # 7) Директор (поки порожньо — можна підвантажувати з налаштувань)
        ctx.setdefault("director_full_name", "")

        # --- шлях для тимчасового прев'ю ---
        out_path = TMP_DIR / f"emp_{employee_id:04d}_doc_{doc_id:06d}_preview.docx"


        # --- НОРМАЛІЗАЦІЯ ДЛЯ TRAINING (прев'ю) ---
        if doc_type == "TRAINING":
            src = dict(context or {})
            tr = dict((src.get("training") or {}))

            # Дати: ДД.ММ.РРРР
            ctx["order_date_str"] = fmt_dmy(src.get("order_date"))
            s = fmt_dmy(tr.get("start_date"))
            e = fmt_dmy(tr.get("end_date"))
            tr["start_date_str"] = s
            tr["end_date_str"]   = e
            tr["period_str"]     = f"{s} — {e}" if (s and e) else (s or e or "")

            # Підписані ярлики (щоб у шаблоні було просто підставити)
            tr["format_label"]  = tr.get("format")  or ""
            tr["mode_label"]    = tr.get("mode")    or ""
            tr["funding_label"] = tr.get("funding") or ""

            # Години / вартість
            hours_raw = (tr.get("planned_hours") or "").strip()
            tr["hours_str"] = f"{hours_raw} акад. год." if hours_raw else ""

            cost_raw = (tr.get("estimated_cost") or "").strip()
            tr["estimated_cost"] = cost_raw  # (якщо хочеш, додай ' грн' прямо в шаблоні)

            # Повертаємо в контекст
            ctx["training"] = tr

        # --- Fallback для ПІБ керівника: payload -> DIRECTOR_FULL_NAME -> director_employee_id -> штатний директор ---
        if not ctx.get("director_full_name"):
            val = None
            # 1) текстове налаштування (якщо комусь так зручніше)
            try:
                val = db.get_setting("DIRECTOR_FULL_NAME")
            except Exception:
                val = None
            # 2) id працівника- директора → ПІБ з employees
            if not val:
                try:
                    dir_id = db.get_setting("director_employee_id")
                    if dir_id:
                        row = db.fetch_one("""
                            SELECT TRIM(
                                COALESCE(last_name,'') || ' ' ||
                                COALESCE(first_name,'') || 
                                CASE WHEN IFNULL(middle_name,'')<>'' THEN ' '||middle_name ELSE '' END
                            ) AS full_name
                            FROM employees
                            WHERE id = ?
                        """, (dir_id,))
                        val = (row or {}).get("full_name")
                except Exception:
                    pass
            # 3) резервний спосіб (якщо реалізовано в db_manager)
            if not val:
                try:
                    val = db.get_active_director_name()
                except Exception:
                    val = None
            ctx["director_full_name"] = val or ""



        # --- НОРМАЛІЗАЦІЯ ДЛЯ VACATION (прев'ю) ---
        if doc_type == "VACATION":
            src = dict(context or {})
            vac = dict(src.get("vacation") or {})

            # Дата наказу у формат ДД.ММ.РРРР (якщо використовуєш у шаблоні)
            ctx["order_date_str"] = fmt_dmy(src.get("order_date"))

            def _range_str(a, b):
                a_str = fmt_dmy(a); b_str = fmt_dmy(b)
                if a_str and b_str:
                    return f"{a_str} — {b_str}"
                return a_str or b_str or ""

            # Періоди у зручних рядках
            vac["work_period_str"] = _range_str(vac.get("work_period_from"), vac.get("work_period_to"))
            vac["period_str"]      = _range_str(vac.get("start_date"),       vac.get("end_date"))

            # Кількість днів + чекбокс матдопомоги
            td = (vac.get("total_days") or "").strip()
            vac["total_days_str"]    = f"{td} календарних днів" if td else ""
            vac["material_aid_mark"] = "☑" if vac.get("material_aid") else "☐"
            vac["work_period_start_str"] = fmt_dmy(vac.get("work_period_from"))
            vac["work_period_end_str"]   = fmt_dmy(vac.get("work_period_to"))
            vac["start_date_str"]        = fmt_dmy(vac.get("start_date"))
            vac["end_date_str"]          = fmt_dmy(vac.get("end_date"))
            vac["type_label"]            = vac.get("type") or ""
            ctx["cb_health_aid"]         = "☑" if vac.get("material_aid") else "☐"
            vac.setdefault("health_aid_amount", "")



            # Повертаємо в контекст
            ctx["vacation"] = vac


        # --- рендер ---
        from docxtpl import DocxTemplate
        tpl = DocxTemplate(str(tpl_path))
        tpl.render(ctx)
        tpl.save(str(out_path))
        return str(out_path)



    def preview_selected_doc(self):
        """Хендлер кнопки 'Переглянути'."""
        sel = self.docs_tree.selection()
        if not sel:
            messagebox.showwarning("Перегляд", "Оберіть документ у списку.")
            return

        # беремо id з першої колонки таблиці
        values = self.docs_tree.item(sel[0], "values")
        try:
            doc_id = int(values[0])
        except Exception:
            messagebox.showerror("Перегляд", "Некоректний вибір документа.")
            return

        # Перевірка власності та отримання контексту
        doc = db.fetch_one("""
            SELECT id, employee_id, type, title, status, context_json
            FROM documents
            WHERE id = ?
        """, (doc_id,))
        if not doc:
            messagebox.showerror("Перегляд", "Документ не знайдено.")
            return
        if int(doc.get("employee_id") or 0) != int(self.employee_id):
            messagebox.showerror("Перегляд", "Ви не маєте доступу до цього документа.")
            return

        try:
            ctx = json.loads(doc.get("context_json") or "{}")
        except Exception as e:
            messagebox.showerror("Перегляд", f"Пошкоджений вміст документа (JSON): {e}")
            return

        try:
            path = self._render_preview_docx(
                doc_type=doc.get("type"),
                context=ctx,
                employee_id=int(doc.get("employee_id") or 0),
                doc_id=doc_id
            )
            self._open_with_default_app(path)
        except Exception as e:
            messagebox.showerror("Перегляд", f"Не вдалося згенерувати прев'ю: {e}")


    def sign_selected_doc(self):
        """
        Підпис документа працівником:
        - дозволено лише для статусу 'sent'
        - проставляє дату підпису в контекст (sign_employee_day/month/year)
        - рендерить фінальний DOCX у data/documents
        - оновлює documents.status='signed', signed_by, signed_at, file_docx, context_json
        - оновлює таблицю
        """
        import json
        from datetime import datetime, date
        from tkinter import messagebox

        sel = self.docs_tree.selection()
        if not sel:
            messagebox.showwarning("Підпис", "Оберіть документ у списку.")
            return

        values = self.docs_tree.item(sel[0], "values")
        doc_id = int(values[0])   # перша колонка — ID

        try:
            doc = db.get_document(doc_id)
            if not doc:
                messagebox.showerror("Підпис", "Документ не знайдено.")
                return

            if doc.get("status") != "sent":
                messagebox.showwarning("Підпис", "Підписувати можна лише документи зі статусом 'sent'.")
                return

            # --- вихідні дані з БД ---
            doc_type = doc.get("type")
            employee_id = doc.get("employee_id")
            raw_ctx = doc.get("context_json") or {}
            context = raw_ctx if isinstance(raw_ctx, dict) else json.loads(raw_ctx)

            # --- додати дату підпису працівника у payload ---
            today = date.today()
            context["employee_sign_day"]   = f"{today.day:02d}"
            context["employee_sign_month"] = f"{today.month:02d}"
            context["employee_sign_year"]  = f"{today.year}"


            # ---------- НОРМАЛІЗАЦІЯ КОНТЕКСТУ ПІД ШАБЛОН (ідентично прев'ю) ----------
            def fmt_dmy(iso: str | None) -> str:
                if not iso:
                    return ""
                try:
                    d = datetime.strptime(iso, "%Y-%m-%d")
                    return f"{d.day:02d}.{d.month:02d}.{d.year}"
                except Exception:
                    return iso

            def cb(flag: bool) -> str:
                return "☑" if bool(flag) else "☐"

            src = dict(context or {})
            emp = (src.get("employee") or {}) if isinstance(src.get("employee"), dict) else {}
            ctx = dict(src)

            # 1) department/position як об'єкти з .name
            ctx.setdefault("department", {"name": emp.get("department_name", "")})
            ctx.setdefault("position",   {"name": emp.get("position_name", "")})

            # 2) ПІБ (на всяк)
            ctx.setdefault("last_name",   emp.get("last_name", ""))
            ctx.setdefault("first_name",  emp.get("first_name", ""))
            ctx.setdefault("middle_name", emp.get("middle_name", ""))

            # 3) Дати у рядок
            ctx.setdefault("hire_date_str",  fmt_dmy(src.get("order_date") or src.get("hire_date")))
            ctx.setdefault("start_date_str", fmt_dmy(src.get("hire_date")))
            ctx.setdefault("contract_until_str", fmt_dmy(src.get("contract_until")))

            # 4) Чекбокси
            ctx["cb_competition"] = cb(src.get("is_competition"))
            ctx["cb_contract"]    = cb(src.get("is_contract"))
            ctx["cb_probation"]   = cb(src.get("is_probation"))
            ctx["cb_absence"]     = cb(src.get("is_absence"))
            ctx["cb_reserve"]     = cb(src.get("is_reserve"))
            ctx["cb_internship"]  = cb(src.get("is_internship"))
            ctx["cb_transfer"]    = cb(src.get("is_transfer"))
            ctx["cb_other"]       = cb(src.get("is_other"))

            is_main = bool(src.get("is_main_job"))
            ctx["cb_work_main"]      = cb(is_main)
            ctx["cb_work_secondary"] = cb(not is_main)
            ctx["cb_worktime_full"]  = cb(False)

            # 5) Текстові поля
            ctx.setdefault("probation_months", src.get("probation_months", ""))
            ctx.setdefault("other_text",       src.get("other_text", ""))
            ctx.setdefault("work_hours",       src.get("work_hours", ""))
            ctx.setdefault("work_minutes",     src.get("work_minutes", ""))
            ctx.setdefault("salary_grn",       src.get("salary_grn", ""))
            ctx.setdefault("salary_kop",       src.get("salary_kop", ""))
            ctx.setdefault("order_number",     src.get("order_number", ""))

            # 6) Підпис працівника (переконуємось, що є в ctx)
            ctx.setdefault("employee_sign_day",   context["employee_sign_day"])
            ctx.setdefault("employee_sign_month", context["employee_sign_month"])
            ctx.setdefault("employee_sign_year",  context["employee_sign_year"])


            # 7) Директор (поки порожньо; можна підтягувати з налаштувань)
            ctx.setdefault("director_full_name", src.get("director_full_name", ""))

            # --- НОРМАЛІЗАЦІЯ ДЛЯ TRAINING (фінальний рендер) ---
            if doc_type == "TRAINING":
                # беремо вихідний context і секцію training
                src = dict(context or {})
                tr = dict((src.get("training") or {}))

                # форматування дат у ДД.ММ.РРРР
                def _fmt(iso):
                    if not iso:
                        return ""
                    try:
                        d = datetime.strptime(iso, "%Y-%m-%d")
                        return f"{d.day:02d}.{d.month:02d}.{d.year}"
                    except Exception:
                        return iso

                # шапка наказу
                ctx["order_date_str"] = _fmt(src.get("order_date"))

                # період навчання
                s = _fmt(tr.get("start_date"))
                e = _fmt(tr.get("end_date"))
                tr["start_date_str"] = s
                tr["end_date_str"]   = e
                tr["period_str"]     = f"{s} — {e}" if (s and e) else (s or e or "")

                # підписані ярлики (щоб у шаблоні підставляти готові рядки)
                tr["format_label"]  = tr.get("format")  or ""
                tr["mode_label"]    = tr.get("mode")    or ""
                tr["funding_label"] = tr.get("funding") or ""

                # години / вартість (відображення як у прев’ю)
                hours_raw = (tr.get("planned_hours") or "").strip()
                tr["hours_str"] = f"{hours_raw} акад. год." if hours_raw else ""

                cost_raw = (tr.get("estimated_cost") or "").strip()
                tr["estimated_cost"] = cost_raw  # суфікс "грн" можна додати у шаблоні

                # повертаємо секцію назад у контекст
                ctx["training"] = tr

            # --- НОРМАЛІЗАЦІЯ ДЛЯ VACATION (sign) ---
            if doc_type == "VACATION":
                vac = dict(src.get("vacation") or {})

                # Дата наказу (якщо використовуєш у шаблоні)
                ctx["order_date_str"] = fmt_dmy(src.get("order_date"))

                # Періоди у форматі ДД.ММ.РРРР
                vac["work_period_start_str"] = fmt_dmy(vac.get("work_period_from"))
                vac["work_period_end_str"]   = fmt_dmy(vac.get("work_period_to"))
                vac["start_date_str"]        = fmt_dmy(vac.get("start_date"))
                vac["end_date_str"]          = fmt_dmy(vac.get("end_date"))

                # Підписані ярлики/чекбокси
                vac["type_label"]    = vac.get("type") or ""
                ctx["cb_health_aid"] = "☑" if vac.get("material_aid") else "☐"
                vac.setdefault("health_aid_amount", "")

                # Повернути в контекст
                ctx["vacation"] = vac

            # ---------- РЕНДЕР ФІНАЛЬНОГО DOCX ----------
            tpl_path = TEMPLATES_MAP.get(doc_type)
            if not tpl_path or not tpl_path.exists():
                messagebox.showerror("Підпис", f"Не знайдено шаблон для типу '{doc_type}'.")
                return


            # --- Fallback для ПІБ керівника: payload -> DIRECTOR_FULL_NAME -> director_employee_id -> штатний директор ---
            if not ctx.get("director_full_name"):
                val = None
                try:
                    val = db.get_setting("DIRECTOR_FULL_NAME")
                except Exception:
                    val = None
                if not val:
                    try:
                        dir_id = db.get_setting("director_employee_id")
                        if dir_id:
                            row = db.fetch_one("""
                                SELECT TRIM(
                                    COALESCE(last_name,'') || ' ' ||
                                    COALESCE(first_name,'') || 
                                    CASE WHEN IFNULL(middle_name,'')<>'' THEN ' '||middle_name ELSE '' END
                                ) AS full_name
                                FROM employees
                                WHERE id = ?
                            """, (dir_id,))
                            val = (row or {}).get("full_name")
                    except Exception:
                        pass
                if not val:
                    try:
                        val = db.get_active_director_name()
                    except Exception:
                        val = None
                ctx["director_full_name"] = val or ""

        



            from docxtpl import DocxTemplate
            out_path = DOCS_DIR / f"emp_{employee_id:04d}_doc_{doc_id:06d}_signed.docx"
            tpl = DocxTemplate(str(tpl_path))
            tpl.render(ctx)
            tpl.save(str(out_path))

            # ---------- ОНОВЛЕННЯ БД ----------
            signed_by = (self.current_user or {}).get("username", "")
            db.execute_query(
                "UPDATE documents SET status='signed', signed_by=?, signed_at=CURRENT_TIMESTAMP, "
                "file_docx=?, context_json=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (signed_by, str(out_path), json.dumps(context, ensure_ascii=False), doc_id)
            )

            # щоб блок «Стажування» оновився без натискання «Оновити»
            try:
                self.load_internship_summary()
                self.load_training_reminder()
                self.load_vacation_note()
            except Exception:
                pass

            # Після оновлення documents → signed
            if doc_type == "P4":
                # 1) помітити працівника як звільненого
                db.execute_query("""
                    UPDATE employees
                    SET dismissal_date = DATE('now'),
                        employment_status = 'звільнений',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (employee_id,))

                # 2) (необов'язково) деактивувати користувача
                db.execute_query("""
                    UPDATE users
                    SET is_active = 0
                    WHERE employee_id = ?
                """, (employee_id,))

                # 5) Автооновити вкладки після підпису
                try:
                    self.load_profile()   # статус, дати тощо
                    self.refresh_docs()   # список документів
                    # (не обов'язково, але можна ще раз підстрахуватися)
                    self.load_internship_summary()
                except Exception:
                    pass




            # === проставляємо дату прийняття в employees, якщо ще не стоїть ===
            hire_date = context.get("hire_date") or context.get("start_date")
            if hire_date:
                db.execute_query(
                    "UPDATE employees SET hire_date = COALESCE(hire_date, ?) WHERE id = ?",
                    (hire_date, employee_id)
                )



                        # ---------- [NEW] ЛОГ У signatures ----------
            # хто підписав
            row = db.fetch_one("SELECT id, role FROM users WHERE username = ?", (signed_by,))
            user_id = row["id"] if row else None
            role_for_log = (row["role"] if row else "employee") or "employee"

            # хеш фінального DOCX (для контролю цілісності)
            import hashlib, json as _json
            with open(out_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            db.execute_query(
                "INSERT INTO signatures(document_id, user_id, role, signature_data) "
                "VALUES (?, ?, ?, ?)",
                (
                    doc_id,
                    user_id,
                    role_for_log,
                    _json.dumps(
                        {
                            "method": "click-to-sign",
                            "file_hash_sha256": file_hash,
                            "file_path": str(out_path)
                        },
                        ensure_ascii=False
                    )
                )
            )


            # Оновити список
            self.refresh_docs()
            messagebox.showinfo("Підпис", "Документ успішно підписано.")

        except Exception as e:
            messagebox.showerror("Підпис", f"Не вдалося підписати: {e}")



    # методи для стажування
    def load_internship_summary(self):
        """Підтягує останнє/активне стажування працівника і оновлює блок у профілі."""
        self._internship_doc_id = None
        try:
            # Спершу пробуємо з вʼю 
            row = db.fetch_one("""
                SELECT *
                FROM v_internships_full
                WHERE employee_id = ?
                ORDER BY (status='active') DESC, DATE(planned_end_date) DESC, internship_id DESC
                LIMIT 1
            """, (self.employee_id,))

            # Якщо вʼю немає — fallback на джойни
            if not row:
                row = db.fetch_one("""
                    SELECT i.id AS internship_id, i.start_date, i.planned_end_date, i.status, i.doc_id,
                           m.last_name || ' ' || m.first_name ||
                           CASE WHEN IFNULL(m.middle_name,'') <> '' THEN ' '||m.middle_name ELSE '' END AS mentor_full_name,
                           md.name AS mentor_department_name,
                           mp.name AS mentor_position_name,
                           NULL AS document_status
                    FROM internships i
                    LEFT JOIN employees  m  ON m.id  = i.mentor_employee_id
                    LEFT JOIN departments md ON md.id = m.department_id
                    LEFT JOIN positions  mp ON mp.id  = m.position_id
                    WHERE i.employee_id = ?
                    ORDER BY (i.status='active') DESC, DATE(i.planned_end_date) DESC, i.id DESC
                    LIMIT 1
                """, (self.employee_id,))

            def fmt(iso):
                if not iso: return ""
                from datetime import datetime
                try:
                    d = datetime.strptime(iso, "%Y-%m-%d")
                    return f"{d.day:02d}.{d.month:02d}.{d.year}"
                except Exception:
                    return iso

            if not row:
                # нічого не знайдено
                self._internship_vars["period"].set("—")
                self._internship_vars["mentor"].set("—")
                self._internship_vars["status"].set("—")
                self.btn_preview_intern.configure(state="disabled")
                return

            # Період
            self._internship_vars["period"].set(
                f"{fmt(row.get('start_date'))} — {fmt(row.get('planned_end_date'))}"
            )

            # Наставник
            mentor_line = row.get("mentor_full_name") or ""
            extra = ", ".join(filter(None, [
                row.get("mentor_department_name"),
                row.get("mentor_position_name"),
            ]))
            if extra:
                mentor_line = f"{mentor_line} ({extra})" if mentor_line else extra
            self._internship_vars["mentor"].set(mentor_line or "—")

            # Статус + статус документа
            status = row.get("status") or "—"
            doc_status = row.get("document_status") or None
            if status == "active" and doc_status == "sent":
                status_text = "активне • направлення очікує підпису"
            elif doc_status == "signed":
                status_text = f"{status} • направлення підписано"
            else:
                status_text = status
            self._internship_vars["status"].set(status_text)

            # Документ для кнопки "Переглянути"
            self._internship_doc_id = row.get("doc_id")
            self.btn_preview_intern.configure(
                state=("normal" if self._internship_doc_id else "disabled")
            )

        except Exception as e:
            self._internship_vars["period"].set("—")
            self._internship_vars["mentor"].set("—")
            self._internship_vars["status"].set(f"Помилка: {e}")
            self.btn_preview_intern.configure(state="disabled")

    def preview_internship_doc(self):
        """Відкрити превʼю направлення на стажування (якщо є doc_id)."""
        if not getattr(self, "_internship_doc_id", None):
            messagebox.showwarning("Перегляд", "Немає прив'язаного документа.")
            return
        doc = db.get_document(self._internship_doc_id)
        if not doc:
            messagebox.showerror("Перегляд", "Документ не знайдено.")
            return
        try:
            ctx = json.loads(doc.get("context_json") or "{}")
        except Exception as e:
            messagebox.showerror("Перегляд", f"Пошкоджений вміст документа: {e}")
            return
        try:
            path = self._render_preview_docx(
                doc_type=doc.get("type"),
                context=ctx,
                employee_id=int(doc.get("employee_id") or 0),
                doc_id=int(doc.get("id") or 0),
            )
            self._open_with_default_app(path)
        except Exception as e:
            messagebox.showerror("Перегляд", f"Не вдалося згенерувати прев'ю: {e}")


    def load_training_reminder(self):
        """Шукає найближчий TRAINING (sent/signed) з майбутньою датою старту і показує компактну плашку."""
        self._training_doc_id = None
        try:
            rows = db.fetch_all("""
                SELECT id, type, status, context_json
                FROM documents
                WHERE employee_id = ?
                  AND type = 'TRAINING'
                  AND status IN ('sent','signed')
                ORDER BY created_at DESC
            """, (self.employee_id,))

            from datetime import datetime, date
            today = date.today()

            best = None  # (doc, ctx, tr, start_date_obj)
            for r in rows:
                try:
                    ctx = json.loads(r.get("context_json") or "{}")
                except Exception:
                    ctx = {}

                tr = (ctx.get("training") or {}) if isinstance(ctx.get("training"), dict) else {}
                s_iso = (tr.get("start_date") or "").strip()
                if not s_iso:
                    continue
                try:
                    s_dt = datetime.strptime(s_iso, "%Y-%m-%d").date()
                except Exception:
                    continue
                # показуємо тільки майбутні/сьогоднішні
                if s_dt >= today:
                    if (best is None) or (s_dt < best[3]):
                        best = (r, ctx, tr, s_dt)

            if not best:
                # немає що показувати
                self.training_frame.grid_remove()
                return

            r, ctx, tr, s_dt = best
            e_iso = (tr.get("end_date") or "").strip()

            # форматування
            def fmt(iso):
                if not iso: return ""
                try:
                    d = datetime.strptime(iso, "%Y-%m-%d")
                    return f"{d.day:02d}.{d.month:02d}.{d.year}"
                except Exception:
                    return iso

            s_str = fmt(tr.get("start_date"))
            e_str = fmt(tr.get("end_date"))

            # заголовок
            title = f"Підвищення кваліфікації: {tr.get('title','')}".strip()
            self._tr_title_var.set(title or "Підвищення кваліфікації")

            # мета-рядок
            meta_bits = [tr.get("provider",""), tr.get("format",""), tr.get("place","")]
            self._tr_meta_var.set(" • ".join([b for b in meta_bits if b]).strip(" •"))

            # період + дні до старту
            days_left = (s_dt - today).days
            left_txt = f" • залишилось {days_left} дн." if days_left >= 0 else ""
            period = f"{s_str}" + (f" — {e_str}" if e_str else "")
            self._tr_period_var.set((period + left_txt).strip())

            # бейдж статусу
            badge = "Потрібен підпис" if (r.get("status") == "sent") else "Підтверджено"
            self._tr_badge_var.set(badge)

            # збережемо doc_id для кнопки
            self._training_doc_id = r.get("id")

            # показати плашку
            self.training_frame.grid()

        except Exception as e:
            # у разі помилки просто сховаємо
            self.training_frame.grid_remove()

    def preview_training_doc(self):
        """Відкрити превʼю TRAINING із плашки-нагадування."""
        if not getattr(self, "_training_doc_id", None):
            messagebox.showwarning("Перегляд", "Немає прив'язаного документа.")
            return
        doc = db.get_document(self._training_doc_id)
        if not doc:
            messagebox.showerror("Перегляд", "Документ не знайдено.")
            return
        try:
            ctx = json.loads(doc.get("context_json") or "{}")
        except Exception as e:
            messagebox.showerror("Перегляд", f"Пошкоджений вміст документа: {e}")
            return
        try:
            path = self._render_preview_docx(
                doc_type=doc.get("type"),
                context=ctx,
                employee_id=int(doc.get("employee_id") or 0),
                doc_id=int(doc.get("id") or 0),
            )
            self._open_with_default_app(path)
        except Exception as e:
            messagebox.showerror("Перегляд", f"Не вдалося згенерувати прев'ю: {e}")


    def load_vacation_note(self):
        """Показує коротке повідомлення у профілі, якщо працівник зараз у відпустці (за підписаним наказом VACATION)."""
        import json
        from datetime import date, datetime

        # за замовчуванням ховаємо
        self._vacation_note_var.set("")
        try:
            self.vacation_note.grid_remove()
        except Exception:
            pass

        try:
            rows = db.fetch_all("""
                SELECT id, status, context_json
                FROM documents
                WHERE employee_id = ? AND type = 'VACATION' AND status = 'signed'
                ORDER BY COALESCE(signed_at, created_at) DESC
            """, (self.employee_id,))
        except Exception:
            rows = []

        today = date.today()

        for r in rows:
            try:
                ctx = r.get("context_json") or {}
                if not isinstance(ctx, dict):
                    ctx = json.loads(ctx)
                vac = (ctx.get("vacation") or {})
                s = vac.get("start_date")
                e = vac.get("end_date")
                if not (s and e):
                    continue

                sdt = datetime.strptime(s, "%Y-%m-%d").date()
                edt = datetime.strptime(e, "%Y-%m-%d").date()

                if sdt <= today <= edt:
                    # формат дати ДД.ММ.РРРР
                    def fmt(d): return f"{d.day:02d}.{d.month:02d}.{d.year}"
                    days_left = (edt - today).days + 1
                    vac_type = vac.get("type") or ""
                    note = f"Зараз у відпустці{f' ({vac_type})' if vac_type else ''} до {fmt(edt)} • залишилось {days_left} дн."
                    self._vacation_note_var.set(note)
                    self.vacation_note.grid()   # показати рядок
                    return
            except Exception:
                continue
        # Якщо актуальної відпустки не знайшли — залишаємо прихованим




if __name__ == "__main__":
    # Варіант А: дати тільки username — employee_id підтягнеться сам із таблиці users
    app = EmployeeMainWindow(current_user={
        "username": "lesia.romaniuk",   # ← заміни на логін твого працівника з таблиці users
        "role": "employee"
    })
    app.mainloop()
