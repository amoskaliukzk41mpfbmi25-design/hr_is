# src/vacation_form.py
import customtkinter as ctk
from tkinter import messagebox
from datetime import date
import db_manager as db


class VacationForm(ctk.CTkToplevel):
    """
    Форма: Наказ про надання відпустки.
    Викликає зовнішній колбек self.on_submit(emp_id: int, payload: dict).
    """
    def __init__(self, master):
        super().__init__(master)
        self.title("Надання відпустки")
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
        self.emp_box.configure(command=lambda _=None: self._refresh_work_period())


        # ===== 2) Реквізити наказу =====
        ctk.CTkLabel(root, text="Реквізити", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(10,6))
        row_ord = ctk.CTkFrame(root); row_ord.pack(fill="x", pady=4)
        self.order_number = ctk.CTkEntry(row_ord, placeholder_text="Номер наказу (наприклад, 7/2025)", width=220)
        self.order_number.pack(side="left", padx=(0,8))
        self.order_date = ctk.CTkEntry(row_ord, placeholder_text="Дата наказу (YYYY-MM-DD)", width=180)
        self.order_date.pack(side="left")
        self.order_date.insert(0, date.today().isoformat())

        # автопідстановка номеру наказу (як у попередніх документах)
        try:
            suggested_no = db.get_next_vacation_order_number()
        except Exception:
            suggested_no = ""
        if suggested_no:
            self.order_number.insert(0, suggested_no)



        # ===== 3) Вид та періоди =====
        ctk.CTkLabel(root, text="Параметри відпустки", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(10,6))

        row_type = ctk.CTkFrame(root); row_type.pack(fill="x", pady=4)
        ctk.CTkLabel(row_type, text="Вид відпустки:").pack(side="left", padx=(0,8))
        self.vac_type_var = ctk.StringVar(value="щорічна основна")
        self.vac_type = ctk.CTkComboBox(
            row_type,
            values=["щорічна основна", "щорічна додаткова", "навчальна", "без збереження заробітної плати", "інше"],
            variable=self.vac_type_var, width=320
        )
        self.vac_type.pack(side="left")

        row_wp = ctk.CTkFrame(root); row_wp.pack(fill="x", pady=4)
        self.work_from = ctk.CTkEntry(row_wp, placeholder_text='Період роботи: з (YYYY-MM-DD)', width=220); self.work_from.pack(side="left", padx=(0,8))
        self.work_to   = ctk.CTkEntry(row_wp, placeholder_text='… по (YYYY-MM-DD)',             width=220); self.work_to.pack(side="left")
        self.work_from.configure(state="disabled")
        self.work_to.configure(state="disabled")


        row_vp = ctk.CTkFrame(root); row_vp.pack(fill="x", pady=4)
        self.vac_from  = ctk.CTkEntry(row_vp, placeholder_text='Відпустка: з (YYYY-MM-DD)', width=220); self.vac_from.pack(side="left", padx=(0,8))
        self.vac_to    = ctk.CTkEntry(row_vp, placeholder_text='… по (YYYY-MM-DD)',         width=220); self.vac_to.pack(side="left", padx=(0,16))

        # створюємо поле для к-сті днів і робимо його нередагованим
        self.total_days = ctk.CTkEntry(row_vp, placeholder_text='К-сть календарних днів', width=220)
        self.total_days.pack(side="left")
        self.total_days.configure(state="disabled")


        # коли змінюються дати — перераховуємо період роботи + к-сть днів
        for w in (self.vac_from, self.vac_to):
            w.bind("<FocusOut>",  lambda e: (self._refresh_work_period(), self._recalc_total_days()))
            w.bind("<KeyRelease>", lambda e: self._recalc_total_days())



        row_opts = ctk.CTkFrame(root); row_opts.pack(fill="x", pady=6)
        self.material_aid_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row_opts, text="Надати мат. допомогу на оздоровлення", variable=self.material_aid_var).pack(side="left")

        # ===== Кнопки =====
        btns = ctk.CTkFrame(root); btns.pack(fill="x", pady=12)
        ctk.CTkButton(btns, text="Скасувати", fg_color="#666", hover_color="#555", command=self.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Зберегти", command=self._submit).pack(side="right")

        # початкове автозаповнення (за замовчуванням по обраному працівнику і сьогоднішній даті)
        self.after(10, lambda: (self._refresh_work_period(), self._recalc_total_days()))




    def _get_selected_employee_id(self):
        """Повертає id обраного працівника з комбобоксу."""
        name = self.emp_var.get()
        for _id, _name in self.employees:
            if _name == name:
                return _id
        return None

    def _safe_anniversary(self, base: date, year: int) -> date:
        """Річниця з урахуванням 29 лютого (переносимо на 28.02, якщо треба)."""
        try:
            return date(year, base.month, base.day)
        except ValueError:
            # якщо 29 лютого у невисокосний рік
            return date(year, 2, 28)

    def _compute_work_year(self, hire_iso: str | None, anchor: date) -> tuple[str, str]:
        """
        Рахує робочий рік:
        - якщо hire_date є: [річниця в рік anchor; річниця+1 рік - 1 день]
        - якщо hire_date немає: календарний рік anchor
        Повертає два ISO-рядки YYYY-MM-DD.
        """
        if hire_iso:
            try:
                y, m, d = map(int, hire_iso.split("-"))
                hd = date(y, m, d)
                start = self._safe_anniversary(hd, anchor.year)
                if anchor < start:
                    start = self._safe_anniversary(hd, anchor.year - 1)
                # кінець = рік потому мінус 1 день
                from datetime import timedelta
                end = self._safe_anniversary(hd, start.year + 1) - timedelta(days=1)
                return (start.isoformat(), end.isoformat())
            except Exception:
                pass  # впадемо у календарний рік

        # fallback: календарний рік
        start = date(anchor.year, 1, 1)
        end   = date(anchor.year, 12, 31)
        return (start.isoformat(), end.isoformat())

    def _set_ro_entry(self, entry: ctk.CTkEntry, text: str):
        """Акуратно записуємо в disabled-entry: тимчасово вмикаємо -> вставляємо -> знову вимикаємо."""
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, text)
        entry.configure(state="disabled")

    def _refresh_work_period(self):
        """
        Перерахувати 'Період роботи з/по' коли:
        - змінено працівника;
        - змінилася дата 'Відпустка: з';
        """
        emp_id = self._get_selected_employee_id()
        if not emp_id:
            return

        # тягнемо hire_date
        hire_iso = None
        try:
            raw = db.get_employee_raw(emp_id)  # очікуємо поле 'hire_date'
            hire_iso = (raw or {}).get("hire_date")
        except Exception:
            pass

        # якір — дата початку відпустки, якщо вже введена; інакше сьогодні
        from datetime import date as _date
        anch = _date.today()
        try:
            s = (self.vac_from.get() or "").strip()
            if len(s) == 10:
                y, m, d = map(int, s.split("-"))
                anch = _date(y, m, d)
        except Exception:
            pass

        w_from, w_to = self._compute_work_year(hire_iso, anch)
        self._set_ro_entry(self.work_from, w_from)
        self._set_ro_entry(self.work_to,   w_to)

    def _recalc_total_days(self):
        """Автоматично рахує 'К-сть календарних днів' = (end - start + 1), якщо обидві дати валідні."""
        try:
            s = (self.vac_from.get() or "").strip()
            e = (self.vac_to.get()   or "").strip()
            if len(s) == 10 and len(e) == 10:
                from datetime import date as _date, timedelta
                ys, ms, ds = map(int, s.split("-"))
                ye, me, de = map(int, e.split("-"))
                d1 = _date(ys, ms, ds)
                d2 = _date(ye, me, de)
                if d2 >= d1:
                    days = (d2 - d1).days + 1
                    self._set_ro_entry(self.total_days, str(days))
                    return
        except Exception:
            pass
        # якщо щось не так — очищаємо
        self._set_ro_entry(self.total_days, "")


    # ---------- helpers ----------
    def _validate(self) -> str | None:
        if not self.employees:
            return "У базі немає працівників."
        if not self.order_number.get().strip():
            return "Вкажіть номер наказу."
        if not self.order_date.get().strip() or len(self.order_date.get().strip()) != 10:
            return "Дата наказу має формат YYYY-MM-DD."
        if not self.vac_from.get().strip() or not self.vac_to.get().strip():
            return "Вкажіть період відпустки (початок і кінець)."
        for v in (self.vac_from.get().strip(), self.vac_to.get().strip()):
            if len(v) != 10:
                return "Дати відпустки мають формат YYYY-MM-DD."
        return None



    # --- Налаштування політики (за потреби поміняй 24 на 30) ---
    MAX_ANNUAL_DAYS = 24

    def _find_overlapping_signed_vacations(self, emp_id, start_date, end_date):
        """
        Повертає список перетинів підписаних відпусток для employee_id з інтервалом [start_date; end_date] (включно).
        Кожен елемент: (doc_id, start_iso, end_iso, days)
        """
        rows = db.fetch_all("""
            SELECT id, context_json
            FROM documents
            WHERE employee_id = ?
              AND type = 'VACATION'
              AND status = 'signed'
        """, (emp_id,))

        overlaps = []
        from datetime import datetime
        for r in rows or []:
            try:
                import json
                ctx = json.loads(r.get("context_json") or "{}")
                vac = (ctx.get("vacation") or {})
                s = vac.get("start_date")
                e = vac.get("end_date")
                if not s or not e:
                    continue
                s_d = datetime.strptime(s, "%Y-%m-%d").date()
                e_d = datetime.strptime(e, "%Y-%m-%d").date()
                # інтервали перетинаються, якщо max(start) <= min(end)
                if max(start_date, s_d) <= min(end_date, e_d):
                    days = (e_d - s_d).days + 1
                    overlaps.append((r.get("id"), s, e, days))
            except Exception:
                continue
        return overlaps


    def _submit(self):
        err = self._validate()
        if err:
            messagebox.showerror("Перевірка", err, parent=self)
            return

        # employee_id за назвою
        name = self.emp_var.get()
        emp_id = None
        for _id, _name in self.employees:
            if _name == name:
                emp_id = _id
                break
        if not emp_id:
            messagebox.showerror("Помилка", "Не вдалося визначити працівника.", parent=self)
            return

        # ПІБ керівника (як у TRAINING)
        director_full_name = ""
        try:
            dir_id = db.get_setting("director_employee_id")
        except Exception:
            dir_id = None
        if dir_id:
            row = db.fetch_one("""
                SELECT TRIM(COALESCE(last_name,'') || ' ' || COALESCE(first_name,'') || ' ' || COALESCE(middle_name,'')) AS full_name
                FROM employees
                WHERE id = ?
            """, (dir_id,))
            director_full_name = (row or {}).get("full_name", "") or ""

        # --- АВТО: обчислюємо тривалість відпустки (включно) ---
        from datetime import datetime
        start_s = self.vac_from.get().strip()
        end_s   = self.vac_to.get().strip()
        try:
            d1 = datetime.strptime(start_s, "%Y-%m-%d").date()
            d2 = datetime.strptime(end_s, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Перевірка", "Дати відпустки мають формат YYYY-MM-DD.", parent=self)
            return

        days_count = (d2 - d1).days + 1
        if days_count <= 0:
            messagebox.showerror("Перевірка", "Кінцева дата має бути не раніше за початкову.", parent=self)
            return
        # -------------------------------------------------------
        # 1) Перевірка перетину з уже підписаними відпустками
        overlaps = self._find_overlapping_signed_vacations(emp_id, d1, d2)
        if overlaps:
            lines = []
            for oid, s, e, dd in overlaps:
                lines.append(f"- Документ #{oid}: {s} — {e} ({dd} дн.)")
            messagebox.showerror(
                "Перетин із наявною відпусткою",
                "Обрані дати перекривають уже ПІДПИСАНІ відпустки:\n\n" + "\n".join(lines),
                parent=self
            )
            return

        # 2) Попередження про ліміт для «щорічна основна»
        vac_type = (self.vac_type_var.get() or "").strip().lower()
        if vac_type == "щорічна основна" and days_count > self.MAX_ANNUAL_DAYS:
            from tkinter import messagebox as mb
            if not mb.askyesno(
                "Попередження",
                f"Тривалість {days_count} дн. перевищує типові {self.MAX_ANNUAL_DAYS} днів для щорічної основної.\n"
                "Продовжити оформлення?",
                parent=self
            ):
                return



        payload = {
            "order_number": self.order_number.get().strip(),
            "order_date":   self.order_date.get().strip(),

            "employee": db.get_employee_min(emp_id),  # { last_name, first_name, middle_name, department_name, position_name }

            "vacation": {
                "type": self.vac_type_var.get().strip(),
                "work_period_from": self.work_from.get().strip(),
                "work_period_to":   self.work_to.get().strip(),
                "start_date": self.vac_from.get().strip(),
                "end_date":   self.vac_to.get().strip(),
                "total_days": str(days_count),  
                "material_aid": bool(self.material_aid_var.get()),
            },

            "director_full_name": director_full_name,

            # підпис працівника додасться під час sign
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
