# src/attestations_tab.py
from tkinter import ttk, messagebox
import customtkinter as ctk
import db_manager as db
from datetime import date as _date, datetime as _dt

# Мапи код↔ярлик
ACTION_LABEL = {
    "assignment": "присвоєння",
    "confirmation": "підтвердження",
    "other": "інше",
}
SCHEDULE_LABEL = {
    "planned": "планова",
    "unscheduled": "позачергова",
}
# Зворотні мапи для фільтрів
ACTION_CODE_BY_LABEL = {v: k for k, v in ACTION_LABEL.items()}
SCHEDULE_CODE_BY_LABEL = {v: k for k, v in SCHEDULE_LABEL.items()}


class AttestationsTab(ctk.CTkFrame):
    """
    Перегляд атестацій: План / Історія.
    Пошук + фільтри (тип, вид, відділення, посада) + таблиця.
    """
    def __init__(self, master):
        super().__init__(master)
        self.pack_propagate(False)

        # ===== Верхня панель (Перемикач + пошук) =====
        bar = ctk.CTkFrame(self, corner_radius=8)
        bar.pack(fill="x", padx=10, pady=(10, 6))

        self.view_var = ctk.StringVar(value="plan")  # plan|history
        self.segment = ctk.CTkSegmentedButton(bar, values=["План", "Історія"],
                                              command=self._on_view_change)
        # map labels→values
        self.segment._values_dict = {"План": "plan", "Історія": "history"}
        self.segment.set("План")
        self.segment.pack(side="left", padx=8, pady=8)

        ctk.CTkLabel(bar, text="   Пошук:").pack(side="left", padx=(12, 4))
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            bar, textvariable=self.search_var, width=320,
            placeholder_text="ПІБ, відділення, посада, комісія, підстава…"
        )
        self.search_entry.pack(side="left", padx=(0, 6))
        self.search_entry.bind("<Return>", lambda e: self.refresh())

        ctk.CTkButton(bar, text="Знайти", width=90, command=self.refresh).pack(side="left", padx=(0, 6))
        ctk.CTkButton(bar, text="Оновити", width=110, command=self.refresh).pack(side="right", padx=6)

        # ===== Панель фільтрів =====
        fbar = ctk.CTkFrame(self, corner_radius=8)
        fbar.pack(fill="x", padx=10, pady=(0, 6))

        # Тип
        ctk.CTkLabel(fbar, text="Тип:").pack(side="left", padx=(10, 4))
        self.action_var = ctk.StringVar(value="Усі")
        self.action_menu = ctk.CTkOptionMenu(
            fbar, values=["Усі", "присвоєння", "підтвердження", "інше"],
            variable=self.action_var, width=160,
            command=lambda _=None: self.refresh()
        )
        self.action_menu.pack(side="left", padx=(0, 10))

        # Вид
        ctk.CTkLabel(fbar, text="Вид:").pack(side="left", padx=(10, 4))
        self.schedule_var = ctk.StringVar(value="Усі")
        self.schedule_menu = ctk.CTkOptionMenu(
            fbar, values=["Усі", "планова", "позачергова"],
            variable=self.schedule_var, width=160,
            command=lambda _=None: self.refresh()
        )
        self.schedule_menu.pack(side="left", padx=(0, 10))

        # Відділення
        ctk.CTkLabel(fbar, text="Відділення:").pack(side="left", padx=(10, 4))
        deps = db.get_departments()
        self._dep_by_name = {d["name"]: d["id"] for d in deps}
        dep_values = ["Усі"] + [d["name"] for d in deps]
        self.dep_var = ctk.StringVar(value="Усі")
        self.dep_menu = ctk.CTkOptionMenu(
            fbar, values=dep_values, variable=self.dep_var, width=220,
            command=lambda _=None: (self._reload_position_filter(), self.refresh())
        )
        self.dep_menu.pack(side="left", padx=(0, 10))

        # Посада (залежить від відділення)
        ctk.CTkLabel(fbar, text="Посада:").pack(side="left", padx=(10, 4))
        self.pos_var = ctk.StringVar(value="Усі")
        self.pos_menu = ctk.CTkOptionMenu(
            fbar, values=["Усі"], variable=self.pos_var, width=220,
            command=lambda _=None: self.refresh()
        )
        self.pos_menu.pack(side="left", padx=(0, 10))

        # первинне наповнення списку посад
        self._reload_position_filter()

        # ===== Таблиця =====
        table_wrap = ctk.CTkFrame(self, corner_radius=8)
        table_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ("employee","department","position","action","schedule","planned_date",
                "commission_name","commission_place","basis_text","doc")
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings", height=18)
        self.tree.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        headings = {
            "employee": "Працівник",
            "department": "Відділення",
            "position": "Посада",
            "action": "Тип",
            "schedule": "Вид",
            "planned_date": "Дата проведення",
            "commission_name": "Комісія",
            "commission_place": "Місце",
            "basis_text": "Підстава",
            "doc": "Документ",
        }
        widths = {
            "employee": 220, "department": 180, "position": 180,
            "action": 120, "schedule": 120, "planned_date": 120,
            "commission_name": 200, "commission_place": 160, "basis_text": 260, "doc": 100
        }
        anchors = {
            "employee":"w","department":"w","position":"w",
            "action":"center","schedule":"center","planned_date":"center",
            "commission_name":"w","commission_place":"w","basis_text":"w","doc":"center"
        }
        for col in cols:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor=anchors[col], stretch=True)

        yscroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._open_row_details)
        
        # --- Підсвітка рядків за тегами ---
        # мʼякий жовтий (скоро) і мʼякий червоний (горить/прострочено)
        self.tree.tag_configure("soon",   background="#FFF7CC")   # pale yellow
        self.tree.tag_configure("urgent", background="#FFE2E2")   # pale red



        # первинне завантаження
        self.refresh()

    # ---------------- filters helpers ----------------
    def _reload_position_filter(self):
        """Оновлює список посад у фільтрі з урахуванням обраного відділення."""
        sel_dep = self.dep_var.get()
        if sel_dep == "Усі":
            try:
                poss = db.get_all_positions()
            except Exception:
                poss = []
        else:
            dep_id = self._dep_by_name.get(sel_dep)
            try:
                poss = db.get_positions_by_department(dep_id) if dep_id else []
            except Exception:
                poss = []

        pos_values = ["Усі"] + [p["name"] for p in poss]
        # зберігаємо попередній вибір, якщо він ще є у списку
        prev = self.pos_var.get()
        self.pos_menu.configure(values=pos_values)
        if prev in pos_values:
            self.pos_var.set(prev)
        else:
            self.pos_var.set("Усі")

    # ---------------- data flow ----------------
    def _on_view_change(self, label_clicked: str):
        # Перетворюємо label → value
        v = self.segment._values_dict.get(label_clicked, "plan")
        self.view_var.set(v)
        self.refresh()

    def refresh(self):
        # 1) зчитати з БД
        rows = self._load_from_db(plan=(self.view_var.get() == "plan"))
        if not rows:
            # очистити таблицю
            for iid in self.tree.get_children():
                self.tree.delete(iid)
            return

        # 2) застосувати пошук
        q = (self.search_var.get() or "").strip().lower()
        if q:
            def match_text(r):
                hay = " ".join([
                    r.get("employee_name",""), r.get("department_name",""), r.get("position_name",""),
                    r.get("commission_name",""), r.get("commission_place",""), r.get("basis_text",""),
                    r.get("planned_date",""), r.get("action_label",""), r.get("schedule_label","")
                ]).lower()
                return q in hay
            rows = [r for r in rows if match_text(r)]

        # 3) застосувати фільтри
        # Тип
        fa = self.action_var.get()
        if fa != "Усі":
            code = ACTION_CODE_BY_LABEL.get(fa)
            rows = [r for r in rows if r.get("action") == code]
        # Вид
        fs = self.schedule_var.get()
        if fs != "Усі":
            code = SCHEDULE_CODE_BY_LABEL.get(fs)
            rows = [r for r in rows if r.get("schedule") == code]
        # Відділення
        fd = self.dep_var.get()
        if fd != "Усі":
            rows = [r for r in rows if r.get("department_name") == fd]
        # Посада
        fp = self.pos_var.get()
        if fp != "Усі":
            rows = [r for r in rows if r.get("position_name") == fp]

        # 4) рендер
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for r in rows:
            # Теги підсвітки тільки для вкладки "План"
            tags = ()
            if self.view_var.get() == "plan":
                pd = (r.get("planned_date") or "").strip()
                if pd:
                    try:
                        d_plan = _dt.strptime(pd, "%Y-%m-%d").date()
                        days_left = (d_plan - _date.today()).days
                        if days_left <= 0:
                            tags = ("urgent",)
                        elif days_left <= 14:
                            tags = ("soon",)
                    except Exception:
                        pass  # якщо дата крива — без підсвітки

            self.tree.insert("", "end", iid=str(r["id"]), values=(
                r.get("employee_name",""),
                r.get("department_name",""),
                r.get("position_name",""),
                r.get("action_label",""),
                r.get("schedule_label",""),
                r.get("planned_date",""),
                r.get("commission_name",""),
                r.get("commission_place",""),
                self._shorten(r.get("basis_text",""), 120),
                (f"#{r['doc_id']}" if r.get("doc_id") else "")
            ), tags=tags)


    def _load_from_db(self, plan: bool = True):
        """
        Читає з attestations_plan або attestations_history + JOIN на працівника/довідники.
        Повертає масив dict з уже підставленими label'ами.
        """
        table = "attestations_plan" if plan else "attestations_history"
        try:
            rows = db.fetch_all(f"""
                SELECT a.id, a.employee_id, a.action, a.schedule, a.planned_date,
                       IFNULL(a.commission_name,'')  AS commission_name,
                       IFNULL(a.commission_place,'') AS commission_place,
                       IFNULL(a.basis_text,'')       AS basis_text,
                       a.document_id,
                       (e.last_name || ' ' || e.first_name || ' ' || IFNULL(e.middle_name,'')) AS employee_name,
                       IFNULL(d.name,'') AS department_name,
                       IFNULL(p.name,'') AS position_name,
                       a.created_at
                FROM {table} a
                JOIN employees e ON e.id = a.employee_id
                LEFT JOIN departments d ON d.id = e.department_id
                LEFT JOIN positions   p ON p.id = e.position_id
                ORDER BY a.planned_date ASC, employee_name ASC
            """)
        except Exception as ex:
            messagebox.showerror("Помилка", f"Не вдалося завантажити дані атестацій: {ex}")
            return []

        # підставляємо читабельні мітки
        for r in rows:
            r["action_label"] = ACTION_LABEL.get(r.get("action"), r.get("action") or "")
            r["schedule_label"] = SCHEDULE_LABEL.get(r.get("schedule"), r.get("schedule") or "")
        return rows

    def _shorten(self, s: str, n: int) -> str:
        s = (s or "").strip()
        return s if len(s) <= n else s[:n-1] + "…"

    def _open_row_details(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        rid = sel[0]
        vals = self.tree.item(rid, "values")
        # простий огляд деталей
        detail = (
            f"Працівник: {vals[0]}\n"
            f"Відділення: {vals[1]}\n"
            f"Посада: {vals[2]}\n"
            f"Тип/Вид: {vals[3]} • {vals[4]}\n"
            f"Дата: {vals[5]}\n"
            f"Комісія: {vals[6]}\n"
            f"Місце: {vals[7]}\n"
            f"Підстава: {vals[8]}\n"
            f"Документ: {vals[9] or '—'}"
        )
        messagebox.showinfo("Атестація", detail)
