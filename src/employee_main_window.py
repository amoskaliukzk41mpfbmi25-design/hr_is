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
            text_color=("gray70", "gray50")
        )
        note.grid(row=len(labels)+1, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 12))

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
        TYPE_LABELS = {"P1": "П-1: Прийняття на роботу"}  # тимчасова мапа
        for r in rows:
            show_type = TYPE_LABELS.get(r.get("type"), r.get("type"))
            self.docs_tree.insert("", "end", values=(
                r.get("id"), show_type, r.get("title"), r.get("status"),
                r.get("created_at") or "", r.get("signed_at") or ""
            ))




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

            # ---------- РЕНДЕР ФІНАЛЬНОГО DOCX ----------
            tpl_path = TEMPLATES_MAP.get(doc_type)
            if not tpl_path or not tpl_path.exists():
                messagebox.showerror("Підпис", f"Не знайдено шаблон для типу '{doc_type}'.")
                return

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





if __name__ == "__main__":
    # Варіант А: дати тільки username — employee_id підтягнеться сам із таблиці users
    app = EmployeeMainWindow(current_user={
        "username": "ivanov",   # ← заміни на логін твого працівника з таблиці users
        "role": "employee"
    })
    app.mainloop()
