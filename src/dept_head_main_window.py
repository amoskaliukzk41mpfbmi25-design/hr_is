# src/dept_head_main_window.py
import customtkinter as ctk
from tkinter import messagebox
from tkinter import ttk
import db_manager as db
from docxtpl import DocxTemplate
from pathlib import Path
import os, sys, subprocess, json

TEMPLATES_MAP = {
    "INTERNSHIP_REFERRAL": Path("data/templates/internship_assignment.docx"),
}

TMP_DIR = Path("data/tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)


DOCS_DIR = Path("data/documents")
DOCS_DIR.mkdir(parents=True, exist_ok=True)


class InternEvaluationForm(ctk.CTkToplevel):
    """
    Форма внесення / редагування оцінки за один місяць стажування.
    """
    def __init__(self, master, internship_row: dict, period_no: int, eval_row: dict | None = None):
        super().__init__(master)
        self.title(f"Оцінка стажування – місяць {period_no}")
        self.geometry("620x480")
        self.grab_set()

        self.master_window = master      # DeptHeadMainWindow
        self.internship_row = internship_row or {}
        self.period_no = period_no
        self.eval_row = eval_row or {}
        self.on_submit = None

        wrap = ctk.CTkFrame(self, corner_radius=10)
        wrap.pack(fill="both", expand=True, padx=16, pady=16)

        # заголовок + ПІБ
        full_name = " ".join(filter(None, [
            self.internship_row.get("last_name"),
            self.internship_row.get("first_name"),
            self.internship_row.get("middle_name"),
        ])).strip() or "—"

        ctk.CTkLabel(
            wrap,
            text=f"{full_name}\nМісяць {period_no}",
            font=ctk.CTkFont(size=16, weight="bold"),
            justify="left"
        ).pack(anchor="w", padx=4, pady=(0, 12))

        # блок полів
        form = ctk.CTkFrame(wrap, corner_radius=8)
        form.pack(fill="x", padx=4, pady=(0, 12))

        self.prof_var = ctk.StringVar(value=self._fmt_score(self.eval_row.get("score_professional")))
        self.disc_var = ctk.StringVar(value=self._fmt_score(self.eval_row.get("score_discipline")))
        self.comm_var = ctk.StringVar(value=self._fmt_score(self.eval_row.get("score_communication")))
        self.growth_var = ctk.StringVar(value=self._fmt_score(self.eval_row.get("score_growth")))

        row = 0
        ctk.CTkLabel(form, text="Професійні навички (0–5):").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ctk.CTkEntry(form, textvariable=self.prof_var, width=80).grid(row=row, column=1, sticky="w", padx=8, pady=4)

        row += 1
        ctk.CTkLabel(form, text="Дисципліна, дотримання правил (0–5):").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ctk.CTkEntry(form, textvariable=self.disc_var, width=80).grid(row=row, column=1, sticky="w", padx=8, pady=4)

        row += 1
        ctk.CTkLabel(form, text="Комунікація / робота в команді (0–5):").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ctk.CTkEntry(form, textvariable=self.comm_var, width=80).grid(row=row, column=1, sticky="w", padx=8, pady=4)

        row += 1
        ctk.CTkLabel(form, text="Динаміка розвитку (0–5):").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ctk.CTkEntry(form, textvariable=self.growth_var, width=80).grid(row=row, column=1, sticky="w", padx=8, pady=4)

        # коментар
        ctk.CTkLabel(wrap, text="Коментар керівника (необов'язково):").pack(anchor="w", padx=4, pady=(4, 4))
        self.comment_box = ctk.CTkTextbox(wrap, height=120)
        self.comment_box.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        if self.eval_row.get("comment"):
            self.comment_box.insert("1.0", self.eval_row.get("comment"))

        # кнопки
        btns = ctk.CTkFrame(wrap)
        btns.pack(fill="x", padx=4, pady=(8, 0))
        ctk.CTkButton(btns, text="Скасувати", fg_color="#6B7280", hover_color="#4B5563",
                      command=self.destroy).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Зберегти оцінку", command=self._on_save).pack(side="right", padx=4)

    @staticmethod
    def _fmt_score(v):
        if v is None:
            return ""
        try:
            return f"{float(v):.1f}".rstrip("0").rstrip(".")
        except Exception:
            return str(v)

    def _on_save(self):
        # валідатор балів
        try:
            s_prof = float((self.prof_var.get() or "0").replace(",", "."))
            s_disc = float((self.disc_var.get() or "0").replace(",", "."))
            s_comm = float((self.comm_var.get() or "0").replace(",", "."))
            s_growth = float((self.growth_var.get() or "0").replace(",", "."))
        except ValueError:
            messagebox.showerror("Перевірка", "Усі бали мають бути числом (0–5).", parent=self)
            return

        for name, val in [
            ("Професійні навички", s_prof),
            ("Дисципліна", s_disc),
            ("Комунікація", s_comm),
            ("Динаміка розвитку", s_growth),
        ]:
            if val < 0 or val > 5:
                messagebox.showerror("Перевірка", f"{name}: значення має бути в діапазоні 0–5.", parent=self)
                return

        # формула – делегуємо головному вікну
        total = self.master_window._calc_total_score(s_prof, s_disc, s_comm, s_growth)
        rec = self.master_window._calc_recommendation(total)

        comment = self.comment_box.get("1.0", "end").strip()

        data = {
            "score_professional": s_prof,
            "score_discipline": s_disc,
            "score_communication": s_comm,
            "score_growth": s_growth,
            "total_score": total,
            "recommendation": rec,
            "comment": comment,
            "period_start": None,
            "period_end": None,
        }

        if callable(self.on_submit):
            try:
                self.on_submit(data)
            except Exception as e:
                messagebox.showerror("Збереження", f"Не вдалося зберегти оцінку: {e}", parent=self)
                return

        self.destroy()


class DeptHeadMainWindow(ctk.CTk):
    """
    Головне вікно для ролі 'dept_head' (завідувач відділення).
    Очікує current_user з ключами: {"username": "...", "role": "dept_head", "employee_id": int?}
    """
    def __init__(self, current_user: dict):
        super().__init__()
        self.title("Кабінет завідувача відділення | Інформаційна система лікарні")
        self.minsize(1000, 600)
        self.state("zoomed")
        self.after(0, lambda: self.state("zoomed"))

        self.current_user = current_user or {}
        if self.current_user.get("role") != "dept_head":
            messagebox.showerror("Доступ", "Це вікно лише для ролі 'dept_head'.")
            self.destroy()
            return

        # ---- Визначаємо employee_id для цього користувача ----
        self.employee_id = self.current_user.get("employee_id")
        if not self.employee_id:
            # Якщо не передали employee_id — підтягуємо за username
            u = db.fetch_one(
                "SELECT id, employee_id FROM users WHERE username = ? LIMIT 1",
                (self.current_user.get("username") or "",)
            )
            if not u or not u.get("employee_id"):
                messagebox.showerror(
                    "Профіль",
                    "Не вдається визначити профіль співробітника для цього користувача."
                )
                self.destroy()
                return
            self.employee_id = u["employee_id"]

        # ---- Визначаємо department_id, яким керує заввідділення ----
        self.department_id = None
        try:
            row_emp = db.get_employee_raw(self.employee_id)
            if not row_emp:
                raise RuntimeError("Не знайдено запису працівника.")
            self.department_id = row_emp.get("department_id")
        except Exception as e:
            messagebox.showerror("Профіль", f"Не вдалося визначити відділення завідувача: {e}")
            self.destroy()
            return

        # ---- Tabview ----
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=16)

        self.tab_home = self.tabview.add("Головна")
        self.tab_interns = self.tabview.add("Стажери")
        self.tab_vacations = self.tabview.add("Відпустки")
        self.tab_docs = self.tabview.add("Документи")



        # ---- Будуємо вкладки ----
        self._build_home_tab()
        self._build_interns_tab()
        self._build_vacations_tab()
        self._build_docs_tab()
        self.refresh_docs()


        # початкове завантаження
        self.load_profile()
        self.load_department_staff()
        self.refresh_interns()  

    # =========================================================
    #                    Вкладка "Головна"
    # =========================================================
    def _build_home_tab(self):
        wrap = ctk.CTkFrame(self.tab_home, corner_radius=10)
        wrap.pack(fill="both", expand=True, padx=10, pady=10)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_columnconfigure(1, weight=2)

        # ---- Заголовок ----
        header = ctk.CTkFrame(wrap)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 6))
        ctk.CTkLabel(
            header,
            text="Кабінет завідувача відділення",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left", padx=6)
        ctk.CTkButton(header, text="Оновити", width=120,
                      command=lambda: (self.load_profile(), self.load_department_staff()))\
            .pack(side="right", padx=6)
        
        # ---- Блок "Про мене" ----
        ctk.CTkLabel(
            wrap,
            text="Мої дані",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(4, 4))

        labels = [
            ("ПІБ", "full_name"),
            ("Email", "email"),
            ("Телефон", "phone"),
            ("Відділення", "department_name"),
            ("Посада", "position_name"),
        ]
        self._profile_vars = {}
        for i, (title, key) in enumerate(labels, start=2):
            ctk.CTkLabel(wrap, text=title, anchor="w")\
                .grid(row=i, column=0, sticky="ew", padx=(12, 6), pady=4)
            var = ctk.StringVar(value="—")
            entry = ctk.CTkEntry(wrap, textvariable=var)
            entry.configure(state="disabled")
            entry.grid(row=i, column=1, sticky="ew", padx=(6, 12), pady=4)
            self._profile_vars[key] = var

        # ---- Блок про відділення ----
        sep1 = ctk.CTkFrame(wrap, height=2)
        sep1.grid(row=len(labels) + 2, column=0, columnspan=2,
                  sticky="ew", padx=12, pady=(6, 6))

        row_dep = len(labels) + 3
        ctk.CTkLabel(
            wrap,
            text="Відділення",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=row_dep, column=0, columnspan=2, sticky="w", padx=12, pady=(2, 4))

        self._dep_name_var = ctk.StringVar(value="—")
        self._dep_stats_var = ctk.StringVar(value="")

        ctk.CTkLabel(wrap, text="Назва", anchor="w")\
            .grid(row=row_dep + 1, column=0, sticky="ew", padx=(12, 6), pady=4)
        dep_name_entry = ctk.CTkEntry(wrap, textvariable=self._dep_name_var)
        dep_name_entry.configure(state="disabled")
        dep_name_entry.grid(row=row_dep + 1, column=1, sticky="ew", padx=(6, 12), pady=4)

        ctk.CTkLabel(wrap, text="Коротка статистика", anchor="w")\
            .grid(row=row_dep + 2, column=0, sticky="ew", padx=(12, 6), pady=4)
        dep_stats_entry = ctk.CTkEntry(wrap, textvariable=self._dep_stats_var)
        dep_stats_entry.configure(state="disabled")
        dep_stats_entry.grid(row=row_dep + 2, column=1, sticky="ew", padx=(6, 12), pady=4)

        # ---- Таблиця працівників відділення ----
        sep2 = ctk.CTkFrame(wrap, height=2)
        sep2.grid(row=row_dep + 3, column=0, columnspan=2,
                  sticky="ew", padx=12, pady=(8, 6))

        ctk.CTkLabel(
            wrap,
            text="Працівники мого відділення",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=row_dep + 4, column=0, columnspan=2, sticky="w", padx=12, pady=(2, 4))

        staff_frame = ctk.CTkFrame(wrap, corner_radius=8)
        staff_frame.grid(row=row_dep + 5, column=0, columnspan=2,
                         sticky="nsew", padx=10, pady=(4, 10))
        wrap.grid_rowconfigure(row_dep + 5, weight=1)

        self.staff_tree = ttk.Treeview(
            staff_frame,
            columns=("full_name", "position", "status"),
            show="headings",
            height=10,
            selectmode="browse"
        )
        self.staff_tree.heading("full_name", text="ПІБ")
        self.staff_tree.heading("position", text="Посада")
        self.staff_tree.heading("status", text="Статус")

        self.staff_tree.column("full_name", width=260, anchor="w")
        self.staff_tree.column("position", width=220, anchor="w")
        self.staff_tree.column("status", width=120, anchor="center")

        self.staff_tree.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        yscroll = ttk.Scrollbar(staff_frame, orient="vertical",
                                command=self.staff_tree.yview)
        self.staff_tree.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side="right", fill="y")

    # =========================================================
    #                    Вкладка "Стажери"
    # =========================================================
    def _build_interns_tab(self):
        wrap = ctk.CTkFrame(self.tab_interns, corner_radius=10)
        wrap.pack(fill="both", expand=True, padx=10, pady=10)
        wrap.grid_rowconfigure(1, weight=1)   # таблиця тягнеться
        wrap.grid_rowconfigure(2, weight=0)   # картка внизу
        wrap.grid_columnconfigure(0, weight=1)

        # ----- Верхній хедер + кнопка "Оновити" -----
        header = ctk.CTkFrame(wrap)
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 6))
        ctk.CTkLabel(
            header,
            text="Стажери вашого відділення",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=(4, 8))

        ctk.CTkButton(
            header,
            text="Оновити",
            width=120,
            command=self.refresh_interns
        ).pack(side="right", padx=(4, 4))

        self._btn_finalize = ctk.CTkButton(
            header,
            text="Завершення…",
            width=140,
            state="disabled",
            command=self.open_finalize_dialog
        )
        self._btn_finalize.pack(side="right", padx=(4, 4))

        # ----- Таблиця стажерів (зверху) -----
        top_frame = ctk.CTkFrame(wrap)
        top_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 6))
        top_frame.grid_rowconfigure(0, weight=1)
        top_frame.grid_columnconfigure(0, weight=1)

        cols = ("employee", "position", "period", "intern_status")
        self.interns_tree = ttk.Treeview(
            top_frame,
            columns=cols,
            show="headings",
            height=8,
            selectmode="browse"
        )
        headings = {
            "employee": "Стажер",
            "position": "Посада",
            "period": "Період стажування",
            "intern_status": "Статус",
        }
        for k, v in headings.items():
            self.interns_tree.heading(k, text=v)
        self.interns_tree.column("employee", width=260, anchor="w")
        self.interns_tree.column("position", width=200, anchor="w")
        self.interns_tree.column("period", width=220, anchor="w")
        self.interns_tree.column("intern_status", width=160, anchor="center")

        self.interns_tree.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=2)

        yscroll = ttk.Scrollbar(top_frame, orient="vertical", command=self.interns_tree.yview)
        self.interns_tree.configure(yscrollcommand=yscroll.set)
        yscroll.grid(row=0, column=1, sticky="ns")

        # реакція на вибір стажера
        self.interns_tree.bind("<<TreeviewSelect>>", self._on_intern_selected)

        # мапа internship_id -> рядок (для швидкого доступу у _on_intern_selected)
        self._internships_by_iid = {}

        # ----- Картка стажера (знизу, на всю ширину) -----
        card = ctk.CTkFrame(wrap, corner_radius=10)
        card.grid(row=2, column=0, sticky="ew", padx=4, pady=(6, 0))
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)

        # Ліва половина — паспорт стажування
        left = ctk.CTkFrame(card, corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(left, text="Дані стажера", font=ctk.CTkFont(size=14, weight="bold"))\
            .grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 8))

        self._int_name_var = ctk.StringVar(value="—")
        self._int_position_var = ctk.StringVar(value="—")
        self._int_period_var = ctk.StringVar(value="—")
        self._int_status_var = ctk.StringVar(value="—")
        self._int_mentor_var = ctk.StringVar(value="—")

        row = 1
        ctk.CTkLabel(left, text="ПІБ:", anchor="w").grid(row=row, column=0, sticky="w", padx=(8, 4), pady=2)
        ctk.CTkLabel(left, textvariable=self._int_name_var, anchor="w")\
            .grid(row=row, column=1, sticky="w", padx=(4, 8), pady=2)

        row += 1
        ctk.CTkLabel(left, text="Посада:", anchor="w").grid(row=row, column=0, sticky="w", padx=(8, 4), pady=2)
        ctk.CTkLabel(left, textvariable=self._int_position_var, anchor="w")\
            .grid(row=row, column=1, sticky="w", padx=(4, 8), pady=2)

        row += 1
        ctk.CTkLabel(left, text="Період стажування:", anchor="w")\
            .grid(row=row, column=0, sticky="w", padx=(8, 4), pady=2)
        ctk.CTkLabel(left, textvariable=self._int_period_var, anchor="w")\
            .grid(row=row, column=1, sticky="w", padx=(4, 8), pady=2)

        row += 1
        ctk.CTkLabel(left, text="Статус стажування:", anchor="w")\
            .grid(row=row, column=0, sticky="w", padx=(8, 4), pady=2)
        ctk.CTkLabel(left, textvariable=self._int_status_var, anchor="w")\
            .grid(row=row, column=1, sticky="w", padx=(4, 8), pady=2)

        row += 1
        ctk.CTkLabel(left, text="Наставник:", anchor="w")\
            .grid(row=row, column=0, sticky="w", padx=(8, 4), pady=2)
        ctk.CTkLabel(left, textvariable=self._int_mentor_var, anchor="w")\
            .grid(row=row, column=1, sticky="w", padx=(4, 8), pady=(2, 8))

        # Права половина — для майбутнього оцінювання
        right = ctk.CTkFrame(card, corner_radius=8)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(3, weight=1)  # список оцінок буде розтягуватись

        top_row = ctk.CTkFrame(right)
        top_row.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 4))
        top_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_row,
            text="Оцінювання стажування",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        # підпис/пояснення
        self._eval_hint_var = ctk.StringVar(
            value="Оберіть стажера у таблиці вище, щоб переглянути деталі стажування."
        )
        ctk.CTkLabel(
            right,
            textvariable=self._eval_hint_var,
            wraplength=420,
            text_color=("#6B7280", "#CBD5E1")
        ).grid(row=1, column=0, sticky="w", padx=8, pady=(4, 8))

        # ---- ПІДСУМКИ: прогрес-бар + інтегральний індекс ----
        self._eval_progress_var = ctk.StringVar(value="Оцінки ще не внесено.")
        self._eval_index_var = ctk.StringVar(value="Інтегральний показник: —")

        summary = ctk.CTkFrame(right, corner_radius=6)
        summary.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        summary.grid_columnconfigure(0, weight=1)

        # прогрес-бар (частка заповнених оцінок)
        self._eval_progress_bar = ctk.CTkProgressBar(summary)
        self._eval_progress_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 4))
        self._eval_progress_bar.set(0.0)

        # текст: "Заповнено X з N періодів"
        self._eval_progress_label = ctk.CTkLabel(
            summary,
            textvariable=self._eval_progress_var,
            anchor="w"
        )
        self._eval_progress_label.grid(row=1, column=0, sticky="w", padx=8, pady=(2, 4))

        # текст: "Інтегральний показник: ..."
        self._eval_index_label = ctk.CTkLabel(
            summary,
            textvariable=self._eval_index_var,
            anchor="w"
        )
        self._eval_index_label.grid(row=2, column=0, sticky="w", padx=8, pady=(0, 6))

        # рамка для списку місячних оцінок (переносимо на row=3)
        self._eval_list_frame = ctk.CTkFrame(right, corner_radius=6)
        self._eval_list_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._eval_list_frame.grid_columnconfigure(0, weight=1)





        # поточний вибраний стажування id
        self._current_internship_id = None

        # скидаємо картку на старті
        self._clear_intern_card()


    def refresh_interns(self):
        """
        Підтягує активні стажування працівників мого відділення
        і заповнює таблицю зверху.
        """
        # очистити таблицю
        if hasattr(self, "interns_tree"):
            for iid in self.interns_tree.get_children():
                self.interns_tree.delete(iid)
        self._internships_by_iid = {}
        self._current_internship_id = None
        self._clear_intern_card()
        if hasattr(self, "_btn_finalize"):
            self._btn_finalize.configure(state="disabled")


        if not self.department_id:
            return

        try:
            from datetime import datetime

            rows = db.fetch_all("""
                SELECT
                    i.id AS internship_id,
                    i.employee_id,
                    i.start_date,
                    i.planned_end_date,
                    i.status AS internship_status,
                    i.months,
                    e.last_name, e.first_name, e.middle_name,
                    e.employment_status,
                    p.name AS position_name,
                    m.last_name || ' ' || m.first_name || ' ' || IFNULL(m.middle_name,'') AS mentor_full_name
                FROM internships i
                JOIN employees e ON e.id = i.employee_id
                LEFT JOIN positions p ON p.id = e.position_id
                LEFT JOIN employees m ON m.id = i.mentor_employee_id
                WHERE e.department_id = ?
                AND i.status = 'active'          -- показуємо лише активні
                ORDER BY DATE(i.start_date) ASC, i.id ASC
            """, (self.department_id,))

        except Exception as e:
            self._eval_hint_var.set(f"Помилка завантаження стажувань: {e}")
            return

        def fmt(iso):
            if not iso:
                return ""
            try:
                d = datetime.strptime(iso, "%Y-%m-%d").date()
                return f"{d.day:02d}.{d.month:02d}.{d.year}"
            except Exception:
                return iso

        for r in rows:
            iid = str(r.get("internship_id"))
            self._internships_by_iid[iid] = r

            full_name = " ".join(filter(None, [
                r.get("last_name"), r.get("first_name"), r.get("middle_name")
            ])).strip()

            period = f"{fmt(r.get('start_date'))} — {fmt(r.get('planned_end_date'))}"

            status_raw = r.get("internship_status") or ""
            if status_raw == "active":
                status_text = "активне стажування"
            elif status_raw == "completed":
                status_text = "завершено"
            else:
                status_text = status_raw or "—"

            self.interns_tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    full_name,
                    r.get("position_name") or "",
                    period,
                    status_text
                )
            )

        if not rows:
            self._eval_hint_var.set("Активних стажерів у вашому відділенні зараз немає.")


    def _clear_intern_card(self):
        """Скидає всі поля картки стажера і очищає список оцінок."""
        # ліва частина картки
        if hasattr(self, "_int_name_var"):
            self._int_name_var.set("—")
        if hasattr(self, "_int_position_var"):
            self._int_position_var.set("—")
        if hasattr(self, "_int_period_var"):
            self._int_period_var.set("—")
        if hasattr(self, "_int_status_var"):
            self._int_status_var.set("—")
        if hasattr(self, "_int_mentor_var"):
            self._int_mentor_var.set("—")

        # правий блок – підказка
        if hasattr(self, "_eval_hint_var"):
            self._eval_hint_var.set(
                "Оберіть стажера у таблиці вище, щоб переглянути деталі стажування."
            )

        # індикатори прогресу та інтегрального показника
        if hasattr(self, "_eval_progress_var"):
            self._eval_progress_var.set("Оцінки ще не внесено.")
        if hasattr(self, "_eval_progress_bar"):
            try:
                self._eval_progress_bar.set(0.0)
            except Exception:
                pass

        if hasattr(self, "_eval_index_var"):
            self._eval_index_var.set("Інтегральний показник: —")
        if hasattr(self, "_eval_index_label"):
            # СІРИЙ колір за замовчуванням (light / dark)
            self._eval_index_label.configure(text_color=("#6B7280", "#9CA3AF"))

        if hasattr(self, "_btn_finalize"):
            self._btn_finalize.configure(state="disabled")


        # стан вибраного стажування
        self._current_internship_id = None

        # очистити список місячних оцінок (правий низ)
        self._clear_eval_list()



    def _clear_eval_list(self):
        """Очищає список місячних оцінок у правому блоці."""
        if hasattr(self, "_eval_list_frame"):
            for w in self._eval_list_frame.winfo_children():
                w.destroy()


    def _fill_intern_card(self, row: dict):
        """Заповнити картку даними конкретного стажування."""
        from datetime import datetime

        def fmt(iso):
            if not iso:
                return ""
            try:
                d = datetime.strptime(iso, "%Y-%m-%d").date()
                return f"{d.day:02d}.{d.month:02d}.{d.year}"
            except Exception:
                return iso

        full_name = " ".join(filter(None, [
            row.get("last_name"),
            row.get("first_name"),
            row.get("middle_name"),
        ])).strip() or "—"

        pos = row.get("position_name") or "—"
        period = f"{fmt(row.get('start_date'))} — {fmt(row.get('planned_end_date'))}"

        st_raw = (row.get("internship_status") or "").lower()
        if st_raw == "active":
            status_text = "активне стажування"
        elif st_raw == "completed":
            status_text = "завершено"
        elif st_raw == "overdue":
            status_text = "прострочене"
        else:
            status_text = st_raw or "—"

        mentor = row.get("mentor_full_name") or "—"

        self._int_name_var.set(full_name)
        self._int_position_var.set(pos)
        self._int_period_var.set(period)
        self._int_status_var.set(status_text)
        self._int_mentor_var.set(mentor)

        # поки що просто текст-заглушка — далі тут будуть оцінки й індекс
        self._eval_hint_var.set(
            "У майбутньому тут буде відображено помісячні оцінки стажування "
            "та інтегральний показник успішності."
        )

    def _on_intern_selected(self, event=None):
        """Оновити картку та список оцінок при виборі стажера."""
        sel = self.interns_tree.selection() if hasattr(self, "interns_tree") else []
        if not sel:
            self._clear_intern_card()
            return

        iid = sel[0]  # iid = internship_id як рядок
        row = (self._internships_by_iid or {}).get(iid)
        if not row:
            self._clear_intern_card()
            return

        from datetime import datetime

        def fmt(iso):
            if not iso:
                return ""
            try:
                d = datetime.strptime(iso, "%Y-%m-%d").date()
                return f"{d.day:02d}.{d.month:02d}.{d.year}"
            except Exception:
                return iso

        full_name = " ".join(filter(None, [
            row.get("last_name"),
            row.get("first_name"),
            row.get("middle_name"),
        ])).strip()

        position = row.get("position_name") or "—"
        mentor_full = row.get("mentor_full_name") or "—"
        period = f"{fmt(row.get('start_date'))} — {fmt(row.get('planned_end_date'))}"

        status_raw = (row.get("internship_status") or "").lower()
        if status_raw == "active":
            status_text = "активне стажування"
        elif status_raw == "completed":
            status_text = "завершено"
        else:
            status_text = status_raw or "—"

        # оновлюємо ліву частину картки
        self._int_name_var.set(full_name or "—")
        self._int_position_var.set(position)
        self._int_period_var.set(period or "—")
        self._int_status_var.set(status_text)
        self._int_mentor_var.set(mentor_full)

        # збережемо поточний internship_id
        try:
            self._current_internship_id = int(row.get("internship_id"))
        except Exception:
            self._current_internship_id = None

        # керування доступністю кнопки "Завершення…"
        if hasattr(self, "_btn_finalize"):
            if self._current_internship_id:
                self._btn_finalize.configure(state="normal")
            else:
                self._btn_finalize.configure(state="disabled")


        # оновлюємо список оцінок
        if self._current_internship_id:
            self._load_intern_evaluations(
                internship_id=self._current_internship_id,
                internship_row=row
            )
        else:
            self._clear_eval_list()

    def _load_intern_evaluations(self, internship_id: int, internship_row: dict | None = None):
        """
        Показує в правому блоці список періодів стажування і наявні оцінки
        для заданого internship_id + підраховує прогрес та інтегральний показник.
        """
        from datetime import datetime

        # очищаємо список рядків праворуч
        self._clear_eval_list()

        # кількість місяців стажування з поля internships.months (якщо є)
        months = None
        if internship_row:
            try:
                months = int(internship_row.get("months") or 0)
            except Exception:
                months = None

        # тягнемо оцінки з БД
        try:
            eval_rows = db.get_internship_evaluations(internship_id) or []
        except Exception as e:
            self._eval_hint_var.set(f"Помилка завантаження оцінок: {e}")
            # підстрахуємо й підсумкові індикатори
            if hasattr(self, "_eval_progress_var"):
                self._eval_progress_var.set("Оцінки ще не внесено.")
            if hasattr(self, "_eval_index_var"):
                self._eval_index_var.set("Інтегральний показник: —")
            if hasattr(self, "_eval_progress_bar"):
                self._eval_progress_bar.set(0.0)
            return

        # мапа period_no -> запис оцінки (на випадок кількох — беремо останній за created_at)
        eval_by_period: dict[int, dict] = {}
        for ev in eval_rows:
            p = ev.get("period_no")
            if p is None:
                continue
            try:
                key = int(p)
            except Exception:
                continue

            old = eval_by_period.get(key)
            if not old:
                eval_by_period[key] = ev
            else:
                if (ev.get("created_at") or "") > (old.get("created_at") or ""):
                    eval_by_period[key] = ev

        # якщо кількість місяців невідома – візьмемо максимум з наявних періодів
        if not months:
            months = max(eval_by_period.keys(), default=0)

        # --------- ПРОГРЕС ЗАПОВНЕННЯ ---------
        filled_periods = len(eval_by_period)

        if months and hasattr(self, "_eval_progress_bar"):
            self._eval_progress_bar.set(filled_periods / months)
        elif hasattr(self, "_eval_progress_bar"):
            self._eval_progress_bar.set(0.0)

        if months:
            self._eval_progress_var.set(f"Заповнено {filled_periods} з {months} періодів стажування.")
        else:
            self._eval_progress_var.set("Оцінки стажування ще не внесено.")

        # --------- ІНТЕГРАЛЬНИЙ ПОКАЗНИК ---------
        scores = [ev.get("total_score") for ev in eval_rows if ev.get("total_score") is not None]

        if scores:
            avg = sum(scores) / len(scores)
            self._eval_index_var.set(f"Інтегральний показник: {avg:.1f}")

            # колір індикатора: зелений / жовтий / червоний
            if hasattr(self, "_eval_index_label"):
                if avg >= 80:
                    color = ("#15803D", "#22C55E")   # зелений
                elif avg >= 65:
                    color = ("#CA8A04", "#FACC15")   # жовтий
                else:
                    color = ("#B91C1C", "#FCA5A5")   # червоний
                self._eval_index_label.configure(text_color=color)
        else:
            self._eval_index_var.set("Інтегральний показник: —")
            if hasattr(self, "_eval_index_label"):
                self._eval_index_label.configure(text_color=("#6B7280", "#9CA3AF"))

        # якщо взагалі не знаємо тривалість стажування — показали підсумки й вийшли
        if not months:
            if eval_rows:
                self._eval_hint_var.set("Є оцінки стажування, але тривалість стажування не визначено.")
            else:
                self._eval_hint_var.set("Оцінки стажування ще не внесено.")
            return

        # оновлюємо хінт про тривалість
        self._eval_hint_var.set(
            f"Стажування тривалістю {months} міс. "
            f"Оцінки заповнюються наприкінці кожного місяця."
        )

        # --------- ПОМІСЯЧНІ РЯДКИ ---------
        for p in range(1, months + 1):
            ev = eval_by_period.get(p)

            row_frame = ctk.CTkFrame(self._eval_list_frame, corner_radius=6)
            row_frame.grid(row=p - 1, column=0, sticky="ew", padx=4, pady=2)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=1)

            # назва періоду
            ctk.CTkLabel(
                row_frame,
                text=f"Місяць {p}",
                font=ctk.CTkFont(weight="bold")
            ).grid(row=0, column=0, sticky="w", padx=8, pady=4)

            # Колонка 2: статус / бал / рекомендація + кнопка
            if ev:
                total = ev.get("total_score")
                rec = (ev.get("recommendation") or "").strip()

                parts = []
                if total is not None:
                    parts.append(f"Інтегральний бал: {float(total):.2f}")
                if rec:
                    # невелике людське тлумачення
                    rec_human = {"hire":"Рекомендувати прийняття", "extend":"Подовжити стажування", "deny":"Відмовити"}.get(rec, rec)
                    parts.append(f"Рекомендація: {rec_human}")

                text = " • ".join(parts) if parts else "Оцінка внесена."
                ctk.CTkLabel(row_frame, text=text, anchor="w").grid(row=0, column=1, sticky="w", padx=8, pady=4)

                # кнопка редагування
                ctk.CTkButton(
                    row_frame, text="Редагувати",
                    width=110,
                    command=lambda _p=p, _ev=ev: self._open_eval_dialog(internship_id, _p, internship_row, existing_ev=_ev)
                ).grid(row=0, column=2, sticky="e", padx=8, pady=4)
            else:
                ctk.CTkLabel(
                    row_frame, text="Оцінка ще не внесена.", anchor="w",
                    text_color=("#9CA3AF", "#9CA3AF")
                ).grid(row=0, column=1, sticky="w", padx=8, pady=4)

                ctk.CTkButton(
                    row_frame, text="Виставити оцінку",
                    width=140,
                    command=lambda _p=p: self._open_eval_dialog(internship_id, _p, internship_row, existing_ev=None)
                ).grid(row=0, column=2, sticky="e", padx=8, pady=4)


    def _add_months(self, d, months):
        import calendar
        from datetime import date
        y = d.year + (d.month - 1 + months) // 12
        m = (d.month - 1 + months) % 12 + 1
        day = min(d.day, calendar.monthrange(y, m)[1])
        return date(y, m, day)

    def _calc_period_bounds(self, internship_row: dict, period_no: int):
        """Рахує межі періоду (місяця) стажування №period_no (1..N). Повертає (start_iso, end_iso)."""
        from datetime import datetime, timedelta

        start_iso = internship_row.get("start_date")
        planned_end_iso = internship_row.get("planned_end_date")
        if not start_iso:
            return None, None

        start_d = datetime.strptime(start_iso, "%Y-%m-%d").date()
        p_start = self._add_months(start_d, period_no - 1)
        p_end   = self._add_months(p_start, 1) - timedelta(days=1)

        if planned_end_iso:
            planned_end = datetime.strptime(planned_end_iso, "%Y-%m-%d").date()
            if p_end > planned_end:
                p_end = planned_end

        return p_start.isoformat(), p_end.isoformat()

    def _open_eval_dialog(self, internship_id: int, period_no: int, internship_row: dict, existing_ev: dict | None = None):
        """Модальне вікно для внесення/редагування оцінки за місяць."""
        import customtkinter as ctk
        from tkinter import messagebox

        ps, pe = self._calc_period_bounds(internship_row, period_no)

        win = ctk.CTkToplevel(self)
        win.title(f"Оцінка: місяць {period_no}")
        win.geometry("520x420")
        win.grab_set()

        # заголовок
        ctk.CTkLabel(win, text=f"Місяць {period_no} ({ps or '—'} — {pe or '—'})",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=14, pady=(12, 8))

        # поля (комбо 1..5)
        row = ctk.CTkFrame(win); row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(row, text="Проф. навички").pack(side="left")
        prof_cb = ctk.CTkComboBox(row, values=["1","2","3","4","5"], width=80)
        prof_cb.pack(side="right")

        row = ctk.CTkFrame(win); row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(row, text="Дисципліна").pack(side="left")
        disc_cb = ctk.CTkComboBox(row, values=["1","2","3","4","5"], width=80)
        disc_cb.pack(side="right")

        row = ctk.CTkFrame(win); row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(row, text="Комунікація").pack(side="left")
        comm_cb = ctk.CTkComboBox(row, values=["1","2","3","4","5"], width=80)
        comm_cb.pack(side="right")

        row = ctk.CTkFrame(win); row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(row, text="Розвиток").pack(side="left")
        grow_cb = ctk.CTkComboBox(row, values=["1","2","3","4","5"], width=80)
        grow_cb.pack(side="right")

        # коментар
        ctk.CTkLabel(win, text="Коментар (необовʼязково):").pack(anchor="w", padx=14, pady=(12, 0))
        comment_txt = ctk.CTkTextbox(win, height=90)
        comment_txt.pack(fill="both", expand=False, padx=14, pady=(4, 8))

        # якщо редагуємо — підставляємо
        if existing_ev:
            def _set(cb, val):
                try: cb.set(str(int(val)))
                except Exception: cb.set(str(val))
            _set(prof_cb, existing_ev.get("score_professional") or 3)
            _set(disc_cb, existing_ev.get("score_discipline") or 3)
            _set(comm_cb, existing_ev.get("score_communication") or 3)
            _set(grow_cb, existing_ev.get("score_growth") or 3)
            if existing_ev.get("comment"):
                comment_txt.insert("1.0", existing_ev["comment"])
        else:
            prof_cb.set("3"); disc_cb.set("3"); comm_cb.set("3"); grow_cb.set("3")

        # кнопки
        btns = ctk.CTkFrame(win); btns.pack(fill="x", padx=14, pady=10)
        ctk.CTkButton(btns, text="Скасувати", fg_color="#6B7280", hover_color="#4B5563",
                    command=win.destroy).pack(side="left")

        def save():
            try:
                sp = float(prof_cb.get()); sd = float(disc_cb.get())
                sc = float(comm_cb.get()); sg = float(grow_cb.get())
                # валідація 1..5
                for v in (sp, sd, sc, sg):
                    if v < 1 or v > 5:
                        raise ValueError("Оцінки мають бути у діапазоні 1..5.")
            except Exception as ex:
                messagebox.showerror("Помилка", f"Некоректні значення оцінок: {ex}", parent=win)
                return

            try:
                db.upsert_internship_evaluation(
                    internship_id=internship_id,
                    period_no=period_no,
                    score_professional=sp,
                    score_discipline=sd,
                    score_communication=sc,
                    score_growth=sg,
                    comment=comment_txt.get("1.0", "end").strip(),
                    created_by=(self.current_user or {}).get("username", "dept_head"),
                    period_start=ps,
                    period_end=pe
                )
            except Exception as ex:
                messagebox.showerror("Збереження", f"Не вдалося зберегти оцінку: {ex}", parent=win)
                return

            win.destroy()
            # оновлюємо поточний список періодів
            self._load_intern_evaluations(internship_id, internship_row)

        ctk.CTkButton(btns, text="Зберегти", command=save).pack(side="right")



    def open_formula_settings(self):
        """Тимчасове вікно-заглушка для налаштувань формули оцінювання стажування."""
        win = ctk.CTkToplevel(self)
        win.title("Налаштування формули стажування")
        win.geometry("600x400")
        win.grab_set()

        ctk.CTkLabel(
            win,
            text="Тут зʼявляться налаштування ваг критеріїв та порогів для рекомендацій.\n\n"
                 "Поки що це лише попередній перегляд інтерфейсу. "
                 "На наступних кроках підвʼяжемо сюди збереження формули в БД.",
            wraplength=560,
        ).pack(fill="both", expand=True, padx=20, pady=20)


    # =========================================================
    #      Формула інтегрального показника стажування
    # =========================================================
    def _calc_total_score(self, s_prof, s_disc, s_comm, s_growth) -> float:
        """
        Чернова формула:
        - всі бали 0–5
        - нормалізуємо до 0–1 і зважуємо:
          професійні 40%, дисципліна 30%, комунікація 20%, розвиток 10%.
        Потім переводимо у шкалу 0–100.
        """
        max_score = 5.0
        p = max(0.0, min(max_score, float(s_prof)))
        d = max(0.0, min(max_score, float(s_disc)))
        c = max(0.0, min(max_score, float(s_comm)))
        g = max(0.0, min(max_score, float(s_growth)))

        p /= max_score
        d /= max_score
        c /= max_score
        g /= max_score

        total_0_1 = 0.4 * p + 0.3 * d + 0.2 * c + 0.1 * g
        return round(total_0_1 * 100, 2)

    def _calc_recommendation(self, total_score: float) -> str:
        """
        Чернова шкала рекомендацій (потім винесемо в налаштування).
        """
        if total_score >= 80:
            return "Рекомендувати до прийняття на роботу"
        elif total_score >= 65:
            return "Рекомендувати продовжити стажування"
        else:
            return "Не рекомендувати до прийняття"


    def _open_eval_form(self, period_no: int, internship_id: int, eval_row: dict | None, internship_row: dict):
        """
        Відкрити вікно внесення / редагування оцінки для заданого місяця стажування.
        """
        form = InternEvaluationForm(
            master=self,
            internship_row=internship_row,
            period_no=period_no,
            eval_row=eval_row or {}
        )

        username = (self.current_user or {}).get("username", "dept_head")

        def _on_submit(data: dict):
            # збереження в БД (INSERT або UPDATE — всередині db_manager)
            db.save_internship_evaluation(
                internship_id=internship_id,
                period_no=period_no,
                data=data,
                created_by=username,
            )
            # після збереження пере-завантажимо список оцінок
            self._load_intern_evaluations(internship_id, internship_row)

        form.on_submit = _on_submit






    def open_finalize_dialog(self):
        """
        Модалка 'Завершення…' для вибраного стажування:
        - зліва паспорт стажування (ПІБ, посада, період, наставник, статус)
        - справа підсумок (індекс, авто-рекомендація, готовність) + read-only список оцінок
        Кнопки 'Прийняти' / 'Відмовити' активуються, якщо усі періоди оцінені або настав кінець стажування.
        Реальні запис/зміни у БД додамо наступним кроком.
        """
        # 0) Вибір у таблиці
        sel = self.interns_tree.selection() if hasattr(self, "interns_tree") else []
        if not sel:
            messagebox.showwarning("Завершення", "Оберіть стажера у таблиці.")
            return

        iid = sel[0]  # iid = internship_id (рядок)
        row = (self._internships_by_iid or {}).get(iid)
        if not row:
            messagebox.showerror("Завершення", "Не вдалося знайти дані стажування для вибраного рядка.")
            return

        # 1) Допоміжні форматери
        from datetime import datetime as _dt, date as _date

        def _fmt(iso: str | None) -> str:
            if not iso:
                return "—"
            try:
                d = _dt.strptime(iso, "%Y-%m-%d").date()
                return f"{d.day:02d}.{d.month:02d}.{d.year}"
            except Exception:
                return iso

        # 2) Вихідні атрибути
        internship_id = int(row.get("internship_id"))
        full_name = " ".join(filter(None, [row.get("last_name"), row.get("first_name"), row.get("middle_name")])) or "—"
        position  = row.get("position_name") or "—"
        mentor    = row.get("mentor_full_name") or "—"
        period    = f"{_fmt(row.get('start_date'))} — {_fmt(row.get('planned_end_date'))}"

        st_raw = (row.get("internship_status") or "").lower()
        if st_raw == "active":
            status_text = "активне стажування"
        elif st_raw == "completed":
            status_text = "завершено"
        elif st_raw == "overdue":
            status_text = "прострочене"
        else:
            status_text = st_raw or "—"

        # 3) Вікно
        win = ctk.CTkToplevel(self)
        win.title("Завершення стажування")
        win.geometry("920x640")
        win.grab_set()

        # Кореневий грід
        wrap = ctk.CTkFrame(win)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_columnconfigure(1, weight=2)
        wrap.grid_rowconfigure(1, weight=1)

        # ---- Хедер
        header = ctk.CTkFrame(wrap)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 8))
        ctk.CTkLabel(header, text="Завершення стажування", font=ctk.CTkFont(size=16, weight="bold"))\
            .pack(side="left", padx=6)

        # ---- Ліва колонка (паспорт стажування)
        left = ctk.CTkFrame(wrap, corner_radius=10)
        left.grid(row=1, column=0, sticky="nsew", padx=(4, 8), pady=4)
        left.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(left, text="Дані стажера", font=ctk.CTkFont(size=14, weight="bold"))\
            .grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 10))

        row_i = 1
        for label, value in [
            ("ПІБ:", full_name),
            ("Посада:", position),
            ("Період:", period),
            ("Наставник:", mentor),
            ("Статус:", status_text),
        ]:
            ctk.CTkLabel(left, text=label).grid(row=row_i, column=0, sticky="w", padx=10, pady=4)
            ctk.CTkLabel(left, text=value).grid(row=row_i, column=1, sticky="w", padx=10, pady=4)
            row_i += 1

        # ---- Права колонка (підсумок + оцінки)
        right = ctk.CTkFrame(wrap, corner_radius=10)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 4), pady=4)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        # 4) Підтягнути оцінки + розрахувати індекс та готовність
        try:
            months = int(row.get("months") or 0)
        except Exception:
            months = 0

        try:
            eval_rows = db.get_internship_evaluations(internship_id) or []
        except Exception as e:
            eval_rows = []
            messagebox.showerror("Завершення", f"Не вдалося завантажити оцінки: {e}", parent=win)

        eval_by_period = {}
        for ev in eval_rows:
            p = ev.get("period_no")
            if p is not None:
                try:
                    eval_by_period[int(p)] = ev
                except Exception:
                    pass

        if months <= 0:
            months = max(eval_by_period.keys(), default=0)

        def _safe_float(x):
            try:
                return float(x)
            except Exception:
                return None

        def _avg(nums):
            vals = [n for n in nums if n is not None]
            return (sum(vals) / len(vals)) if vals else None

        period_totals = []
        for p in range(1, months + 1):
            ev = eval_by_period.get(p)
            if not ev:
                continue
            total = _safe_float(ev.get("total_score"))
            if total is None:
                crits = [
                    _safe_float(ev.get("score_professional")),
                    _safe_float(ev.get("score_discipline")),
                    _safe_float(ev.get("score_communication")),
                    _safe_float(ev.get("score_growth")),
                ]
                total = _avg(crits)
            if total is not None:
                period_totals.append(total)

        final_index = _avg(period_totals)

        final_rec = "н/д"
        rec_color = "#9CA3AF"
        if final_index is not None:
            if final_index >= 4.0:
                final_rec = "Рекомендувати прийняття"
                rec_color = "#16A34A"
            elif final_index >= 3.0:
                final_rec = "Рекомендувати подовження"
                rec_color = "#D97706"
            else:
                final_rec = "Рекомендувати відмову"
                rec_color = "#DC2626"

        planned_end_iso = row.get("planned_end_date")
        planned_end_date = None
        if planned_end_iso:
            try:
                planned_end_date = _dt.strptime(planned_end_iso, "%Y-%m-%d").date()
            except Exception:
                planned_end_date = None

        all_periods_scored = (months > 0 and all(p in eval_by_period for p in range(1, months + 1)))
        time_window_reached = (planned_end_date is not None and _date.today() >= planned_end_date)
        can_finalize = bool(all_periods_scored or time_window_reached)

        # 5) Блок "Підсумок"
        summary = ctk.CTkFrame(right, corner_radius=8)
        summary.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        summary.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(summary, text="Підсумок", font=ctk.CTkFont(size=14, weight="bold"))\
            .grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(6, 8))

        ctk.CTkLabel(summary, text="Інтегральний бал:").grid(row=1, column=0, sticky="w", padx=10, pady=2)
        ctk.CTkLabel(summary, text=(f"{final_index:.2f}" if final_index is not None else "—"))\
            .grid(row=1, column=1, sticky="w", padx=10, pady=2)

        ctk.CTkLabel(summary, text="Авто-рекомендація:").grid(row=2, column=0, sticky="w", padx=10, pady=2)
        ctk.CTkLabel(summary, text=final_rec, text_color=rec_color)\
            .grid(row=2, column=1, sticky="w", padx=10, pady=2)

        ctk.CTkLabel(summary, text="Готовність до завершення:").grid(row=3, column=0, sticky="w", padx=10, pady=(2, 8))
        ready_text = "усі періоди оцінено" if all_periods_scored else ("настав строк завершення" if time_window_reached else "ще не готово")
        ready_color = "#16A34A" if can_finalize else "#9CA3AF"
        ctk.CTkLabel(summary, text=ready_text, text_color=ready_color)\
            .grid(row=3, column=1, sticky="w", padx=10, pady=(2, 8))

        # 6) Read-only список оцінок
        eval_box = ctk.CTkScrollableFrame(right, corner_radius=6)
        eval_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        right.grid_rowconfigure(1, weight=1)

        max_rows = max(months, 1)
        for p in range(1, max_rows + 1):
            ev = eval_by_period.get(p)
            rowf = ctk.CTkFrame(eval_box, corner_radius=6)
            rowf.pack(fill="x", expand=False, padx=6, pady=4)

            ctk.CTkLabel(rowf, text=f"Місяць {p}", font=ctk.CTkFont(weight="bold"))\
                .grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))

            if ev:
                total = ev.get("total_score")
                total_str = f"{float(total):.2f}" if total is not None else "—"
                rec = (ev.get("recommendation") or "—").strip()
                ctk.CTkLabel(rowf, text=f"Інтегральний бал: {total_str} • Рекомендація: {rec}")\
                    .grid(row=0, column=1, sticky="w", padx=8, pady=(6, 2))

                # критерії
                crits = []
                for k, label in [
                    ("score_professional",  "Проф."),
                    ("score_discipline",    "Дисцип."),
                    ("score_communication", "Комунікація"),
                    ("score_growth",        "Ріст"),
                ]:
                    v = ev.get(k)
                    if v is not None:
                        try:
                            crits.append(f"{label}: {float(v):.1f}")
                        except Exception:
                            pass
                if crits:
                    ctk.CTkLabel(rowf, text="; ".join(crits), text_color=("#6B7280", "#CBD5E1"))\
                        .grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 4))

                comment = (ev.get("comment") or "").strip()
                if comment:
                    ctk.CTkLabel(rowf, text=f"Коментар: {comment}", wraplength=520)\
                        .grid(row=2, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8))
            else:
                ctk.CTkLabel(rowf, text="Оцінку ще не внесено.", text_color=("#9CA3AF", "#9CA3AF"))\
                    .grid(row=0, column=1, sticky="w", padx=8, pady=(6, 2))

        # 7) Низ: панель дій
        footer = ctk.CTkFrame(wrap)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 4))
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            footer,
            text="Підказка: завершення стане доступним, коли заповнено всі періоди або настане дата завершення.",
            wraplength=620
        ).grid(row=0, column=0, sticky="w", padx=8, pady=6)

        btns = ctk.CTkFrame(footer)
        btns.grid(row=0, column=1, sticky="e", padx=4, pady=4)

        # 3 кнопки вибору дії
        username = (self.current_user or {}).get("username", "dept_head")

        def _do_hire():
            if not can_finalize:
                messagebox.showwarning("Завершення", "Ще не можна завершити стажування.", parent=win)
                return
            if not messagebox.askyesno("Підтвердження",
                                    "Підтвердити прийняття працівника після стажування?",
                                    parent=win):
                return
            try:
                db.outcome_hire(
                    internship_id=internship_id,
                    decided_by=username,
                    final_score=final_index,
                    final_recommendation=final_rec,
                    comment=None
                )
                messagebox.showinfo("Готово", "Стажування завершено: працівника прийнято.", parent=win)
                win.destroy()
                self.refresh_interns()
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося завершити стажування: {e}", parent=win)

        def _do_decline():
            if not can_finalize:
                messagebox.showwarning("Завершення", "Ще не можна завершити стажування.", parent=win)
                return
            # опційний коментар
            comment = ""
            try:
                dlg = ctk.CTkInputDialog(text="Причина/коментар до відмови (необовʼязково):",
                                        title="Відмова")
                comment = dlg.get_input() or ""
            except Exception:
                pass

            if not messagebox.askyesno("Підтвердження",
                                    "Відмовити працівнику за результатами стажування?",
                                    parent=win):
                return
            try:
                db.outcome_decline(
                    internship_id=internship_id,
                    decided_by=username,
                    final_score=final_index,
                    final_recommendation=final_rec,
                    comment=comment
                )
                messagebox.showinfo("Готово", "Стажування завершено: працівнику відмовлено.", parent=win)
                win.destroy()
                self.refresh_interns()
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося завершити стажування: {e}", parent=win)

        def _do_extend():
            # запитати кількість місяців
            months_add = None
            try:
                dlg = ctk.CTkInputDialog(text="На скільки місяців подовжити? (1–6):",
                                        title="Подовження стажування")
                raw = (dlg.get_input() or "").strip()
                months_add = int(raw)
            except Exception:
                pass

            if not months_add or months_add <= 0 or months_add > 6:
                messagebox.showwarning("Подовження", "Вкажіть коректну кількість місяців (1–6).", parent=win)
                return

            comment = ""
            try:
                dlg2 = ctk.CTkInputDialog(text="Коментар до подовження (необовʼязково):",
                                        title="Подовження стажування")
                comment = dlg2.get_input() or ""
            except Exception:
                pass

            if not messagebox.askyesno("Підтвердження",
                                    f"Подовжити стажування на {months_add} міс.?",
                                    parent=win):
                return

            try:
                db.outcome_extend(
                    internship_id=internship_id,
                    months_to_add=months_add,
                    decided_by=username,
                    comment=comment
                )
                messagebox.showinfo("Готово", "Стажування подовжено.", parent=win)
                win.destroy()
                self.refresh_interns()
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося подовжити стажування: {e}", parent=win)

        btn_extend = ctk.CTkButton(btns, text="Подовжити…", width=120, command=_do_extend)
        btn_extend.pack(side="left", padx=4)

        btn_decline = ctk.CTkButton(btns, text="Відмовити", width=120,
                                    fg_color="#DC2626", hover_color="#B91C1C",
                                    state=("normal" if can_finalize else "disabled"),
                                    command=_do_decline)
        btn_decline.pack(side="left", padx=4)

        btn_hire = ctk.CTkButton(btns, text="Прийняти", width=120,
                                fg_color="#16A34A", hover_color="#15803D",
                                state=("normal" if can_finalize else "disabled"),
                                command=_do_hire)
        btn_hire.pack(side="left", padx=4)








    # =========================================================
    #                    Вкладка "Відпустки"
    # =========================================================
    def _build_vacations_tab(self):
        wrap = ctk.CTkFrame(self.tab_vacations, corner_radius=10)
        wrap.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            wrap,
            text="Контроль відпусток у відділенні",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=12, pady=(4, 8))

        ctk.CTkLabel(
            wrap,
            text="Тут зʼявиться аналіз покриття змін та погодження відпусток.",
            text_color=("#6B7280", "#CBD5E1")
        ).pack(anchor="w", padx=12, pady=(0, 4))





    def _build_docs_tab(self):
        """Вкладка 'Документи' для завідувача: бачить направлення на стажування свого відділення."""
        wrap = ctk.CTkFrame(self.tab_docs, corner_radius=10)
        wrap.pack(fill="both", expand=True, padx=10, pady=10)

        # Таблиця
        table = ctk.CTkFrame(wrap)
        table.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        from tkinter import ttk
        cols = ("id", "employee", "title", "status", "created_at", "signed_at")
        self.docs_tree = ttk.Treeview(table, columns=cols, show="headings", height=18)

        headings = {
            "id": "ID",
            "employee": "Працівник",
            "title": "Назва",
            "status": "Статус",
            "created_at": "Створено",
            "signed_at": "Підписано",
        }
        for k, v in headings.items():
            self.docs_tree.heading(k, text=v)
            width = 80
            if k == "employee":
                width = 200
            elif k == "title":
                width = 280
            elif k in ("created_at", "signed_at"):
                width = 140
            self.docs_tree.column(k, width=width, stretch=True)

        self.docs_tree.pack(side="left", fill="both", expand=True)

        yscroll = ttk.Scrollbar(table, orient="vertical", command=self.docs_tree.yview)
        self.docs_tree.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side="right", fill="y")

        # Кнопки дій під таблицею
        actions = ctk.CTkFrame(wrap)
        actions.pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkButton(actions, text="Переглянути", width=160,
                      command=self.preview_selected_doc).pack(side="left", padx=6)
        self.btn_sign = ctk.CTkButton(actions, text="Підписати", width=140,
                                      command=self.sign_selected_doc)
        self.btn_sign.pack(side="left", padx=6)




    def refresh_docs(self):
        """
        Показати документи типу INTERNSHIP_REFERRAL,
        де в context_json.dept_head_employee_id = employee_id цього завідувача.
        """
        if not hasattr(self, "employee_id") or self.employee_id is None:
            return

        try:
            rows = db.fetch_all("""
                SELECT d.id,
                       d.type,
                       d.title,
                       d.status,
                       d.created_at,
                       d.signed_at,
                       e.last_name || ' ' || e.first_name || ' ' || IFNULL(e.middle_name,'') AS employee_name
                FROM documents d
                JOIN employees e ON e.id = d.employee_id
                WHERE d.type = 'INTERNSHIP_REFERRAL'
                  AND json_extract(d.context_json, '$.dept_head_employee_id') = ?
                ORDER BY d.created_at DESC
            """, (self.employee_id,))
        except Exception as ex:
            messagebox.showerror("Документи", f"Не вдалося завантажити документи: {ex}")
            return

        # очистити таблицю
        for iid in self.docs_tree.get_children():
            self.docs_tree.delete(iid)

        for r in rows:
            self.docs_tree.insert(
                "",
                "end",
                values=(
                    r.get("id"),
                    r.get("employee_name") or "",
                    r.get("title") or "",
                    r.get("status") or "",
                    r.get("created_at") or "",
                    r.get("signed_at") or "",
                )
            )


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
        Спрощений рендер превʼю для документів керівника (поки що INTERNSHIP_REFERRAL).
        """
        tpl_path = TEMPLATES_MAP.get(doc_type)
        if not tpl_path or not tpl_path.exists():
            raise RuntimeError(f"Не знайдено шаблон для типу '{doc_type}'.")

        out_path = TMP_DIR / f"dept_{employee_id:04d}_doc_{doc_id:06d}_preview.docx"

        tpl = DocxTemplate(str(tpl_path))
        tpl.render(context or {})
        tpl.save(str(out_path))

        return str(out_path)

    def preview_selected_doc(self):
        """Відкрити превʼю вибраного документа (направлення на стажування)."""
        sel = self.docs_tree.selection()
        if not sel:
            messagebox.showwarning("Перегляд", "Оберіть документ у списку.")
            return

        values = self.docs_tree.item(sel[0], "values")
        try:
            doc_id = int(values[0])
        except Exception:
            messagebox.showerror("Перегляд", "Некоректний вибір документа.")
            return

        doc = db.get_document(doc_id)
        if not doc:
            messagebox.showerror("Перегляд", "Документ не знайдено.")
            return

        # (опційно) перевірка, що саме цей заввідділення є адресатом
        try:
            ctx_raw = doc.get("context_json") or {}
            if not isinstance(ctx_raw, dict):
                ctx = json.loads(ctx_raw)
            else:
                ctx = ctx_raw
        except Exception as e:
            messagebox.showerror("Перегляд", f"Пошкоджений вміст документа: {e}")
            return

        # якщо хочеш – можна додатково переконатися, що dept_head_employee_id == self.employee_id
        try:
            dept_id_in_ctx = ctx.get("dept_head_employee_id")
            if dept_id_in_ctx is not None and int(dept_id_in_ctx) != int(self.employee_id):
                messagebox.showerror("Перегляд", "У вас немає доступу до цього документа.")
                return
        except Exception:
            pass

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


    def sign_selected_doc(self):
        """
        Підпис документа завідувачем:
        - працює для INTERNSHIP_REFERRAL
        - ставить дату підпису dept_head_sign_day/month/year
        - перерендерює DOCX
        - оновлює documents + signatures
        """
        sel = self.docs_tree.selection()
        if not sel:
            messagebox.showwarning("Підпис", "Оберіть документ у списку.")
            return

        values = self.docs_tree.item(sel[0], "values")
        try:
            doc_id = int(values[0])
        except Exception:
            messagebox.showerror("Підпис", "Некоректний вибір документа.")
            return

        doc = db.get_document(doc_id)
        if not doc:
            messagebox.showerror("Підпис", "Документ не знайдено.")
            return

        doc_type = doc.get("type")
        if doc_type != "INTERNSHIP_REFERRAL":
            messagebox.showwarning("Підпис", "Підписання для цього типу документів ще не реалізовано.")
            return

        # ---- розбираємо контекст ----
        try:
            ctx_raw = doc.get("context_json") or {}
            if isinstance(ctx_raw, dict):
                ctx = dict(ctx_raw)
            else:
                ctx = json.loads(ctx_raw)
        except Exception as e:
            messagebox.showerror("Підпис", f"Пошкоджений вміст документа (JSON): {e}")
            return

        # перевірка, що цей документ адресований саме цьому заввідділенню
        target = ctx.get("dept_head_employee_id")
        try:
            if target is not None and int(target) != int(self.employee_id):
                messagebox.showerror("Підпис", "Ви не є адресатом цього документа.")
                return
        except Exception:
            pass

        # якщо вже є дата підпису керівника — запитаємо підтвердження
        if ctx.get("dept_head_sign_day") or ctx.get("dept_head_sign_month") or ctx.get("dept_head_sign_year"):
            from tkinter import messagebox as mb
            if not mb.askyesno(
                "Підпис",
                "У документі вже є дата підпису керівника.\nПоставити підпис ще раз (оновити дату)?"
            ):
                return

        # ---- ставимо дату підпису керівника ----
        from datetime import date
        today = date.today()
        ctx["dept_head_sign_day"] = f"{today.day:02d}"
        ctx["dept_head_sign_month"] = f"{today.month:02d}"
        ctx["dept_head_sign_year"] = f"{today.year}"

        # гарантуємо наявність ПІБ керівника у контексті
        if not ctx.get("dept_head_full_name"):
            try:
                me = db.get_employee_min(self.employee_id) or {}
                full_name = " ".join(filter(None, [
                    me.get("last_name"), me.get("first_name"), me.get("middle_name")
                ])).strip()
            except Exception:
                full_name = ""
            ctx["dept_head_full_name"] = full_name

        # ---- рендер фінального DOCX ----
        tpl_path = TEMPLATES_MAP.get(doc_type)
        if not tpl_path or not tpl_path.exists():
            messagebox.showerror("Підпис", f"Не знайдено шаблон для типу '{doc_type}'.")
            return

        try:
            employee_id = int(doc.get("employee_id") or 0)
        except Exception:
            employee_id = 0

        out_path = DOCS_DIR / f"emp_{employee_id:04d}_doc_{doc_id:06d}_signed.docx"

        try:
            tpl = DocxTemplate(str(tpl_path))
            tpl.render(ctx)
            tpl.save(str(out_path))
        except Exception as e:
            messagebox.showerror("Підпис", f"Не вдалося сформувати файл: {e}")
            return

        # ---- оновлюємо запис у documents ----
        signed_by = (self.current_user or {}).get("username", "")
        try:
            db.execute_query(
                "UPDATE documents "
                "SET status='signed', signed_by=?, signed_at=CURRENT_TIMESTAMP, "
                "    file_docx=?, context_json=?, updated_at=CURRENT_TIMESTAMP "
                "WHERE id=?",
                (signed_by, str(out_path), json.dumps(ctx, ensure_ascii=False), doc_id)
            )
        except Exception as e:
            messagebox.showerror("Підпис", f"Не вдалося оновити запис документа: {e}")
            return

        # ---- лог у signatures ----
        try:
            row = db.fetch_one("SELECT id, role FROM users WHERE username = ?", (signed_by,))
            user_id = row["id"] if row else None
            role_for_log = (row["role"] if row else "dept_head") or "dept_head"

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
                            "file_path": str(out_path),
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
        except Exception:
            # лог не критичний для юзера — просто мовчки пропустимо
            pass

        # оновити таблицю
        self.refresh_docs()
        messagebox.showinfo("Підпис", "Документ підписано.")




    # =========================================================
    #                 Завантаження даних
    # =========================================================
    def load_profile(self):
        """
        Читає з БД дані завідувача і підставляє у форму.
        """
        try:
            row = db.get_employee_raw(self.employee_id)
            if not row:
                raise RuntimeError("Профіль не знайдено.")

            full_name = " ".join(filter(None, [
                row.get("last_name"),
                row.get("first_name"),
                row.get("middle_name"),
            ])).strip()

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
            }
            for k, v in data.items():
                self._profile_vars[k].set(v)

            # заодно оновимо назву відділення у відповідному блоці
            self._dep_name_var.set(department_name)

        except Exception as e:
            messagebox.showerror("Профіль", f"Не вдалося завантажити дані профілю: {e}")

    def load_department_staff(self):
        """
        Підтягує працівників лише цього відділення і заповнює таблицю.
        Також рахує коротку статистику (к-сть активних).
        """
        if not self.department_id:
            self._dep_stats_var.set("Відділення не визначено.")
            return

        # очищаємо таблицю
        for iid in self.staff_tree.get_children():
            self.staff_tree.delete(iid)

        try:
            # список працівників
            rows = db.fetch_all("""
                SELECT e.id,
                       e.last_name, e.first_name, e.middle_name,
                       e.employment_status,
                       IFNULL(p.name, '') AS position_name
                FROM employees e
                LEFT JOIN positions p ON p.id = e.position_id
                WHERE e.department_id = ?
                ORDER BY position_name ASC, e.last_name ASC, e.first_name ASC
            """, (self.department_id,))

            # коротка статистика (к-сть активних)
            row_cnt = db.fetch_one("""
                SELECT COUNT(*) AS cnt
                FROM employees
                WHERE department_id = ? AND employment_status = 'активний'
            """, (self.department_id,))
            active_count = (row_cnt or {}).get("cnt", 0)

            self._dep_stats_var.set(f"Активних працівників: {active_count}")

            for r in rows:
                full_name = " ".join(filter(None, [
                    r.get("last_name"),
                    r.get("first_name"),
                    r.get("middle_name"),
                ])).strip()
                pos = r.get("position_name") or ""
                status = r.get("employment_status") or ""
                self.staff_tree.insert(
                    "",
                    "end",
                    iid=str(r["id"]),
                    values=(full_name, pos, status)
                )

        except Exception as e:
            self._dep_stats_var.set(f"Помилка завантаження працівників: {e}")


if __name__ == "__main__":
    # Тестовий запуск: сюди підстав логін завідувача, який є в таблиці users
    app = DeptHeadMainWindow(current_user={
        "username": "dmytro.sydorenko",  # АБО будь-який username з role = 'dept_head'
        "role": "dept_head",
        # "employee_id": 47,  # можна явно вказати, тоді username не обов'язковий
    })
    app.mainloop()
