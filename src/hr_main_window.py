# src/hr_main_window.py
from datetime import datetime
from tkinter import ttk
import customtkinter as ctk
import db_manager as db
from tkinter import messagebox
from documents_tab import DocumentsTab
from p1_create_form import P1CreateForm
from internships_tab import InternshipsTab
from attestations_tab import AttestationsTab
import json



class DashboardTab(ctk.CTkFrame):
    """Вкладка 'Головна' з KPI-картками та швидкими діями."""
    def __init__(self, master):
        super().__init__(master)
        self.pack_propagate(False)

        # Секція KPI (верх)
        kpi_wrap = ctk.CTkFrame(self, corner_radius=12)
        kpi_wrap.pack(fill="x", padx=10, pady=(10, 6))

        self.kpi_total = self._kpi_card(kpi_wrap, "Усього працівників", "—")
        self.kpi_hired = self._kpi_card(kpi_wrap, "Нові за 30 днів", "—")
        self.kpi_dismissed = self._kpi_card(kpi_wrap, "Звільнені за 30 днів", "—")
        self.kpi_deps = self._kpi_card(kpi_wrap, "Активні відділення", "—")

        # Рядком: розташуємо картки поруч
        for i, card in enumerate((self.kpi_total, self.kpi_hired, self.kpi_dismissed, self.kpi_deps)):
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            kpi_wrap.grid_columnconfigure(i, weight=1)

        # Завантажити дані KPI
        self.reload_kpis()

    def _kpi_card(self, parent, title, value_text):
        frame = ctk.CTkFrame(parent, corner_radius=12)
        title_lbl = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=16, weight="bold"))
        value_lbl = ctk.CTkLabel(frame, text=value_text, font=ctk.CTkFont(size=28, weight="bold"))
        title_lbl.pack(pady=(14, 6))
        value_lbl.pack(pady=(0, 14))
        # Збережемо посилання, щоб можна було оновити цифру:
        frame.value_lbl = value_lbl
        return frame

    def reload_kpis(self):
        try:
            total = db.count_employees_total()
            hired = db.count_employees_hired_last_30d()
            dismissed = db.count_employees_dismissed_last_30d()
            deps = db.count_departments()
        except Exception as e:
            total = hired = dismissed = deps = "—"
            print("KPI error:", e)

        self.kpi_total.value_lbl.configure(text=str(total))
        self.kpi_hired.value_lbl.configure(text=str(hired))
        self.kpi_dismissed.value_lbl.configure(text=str(dismissed))
        self.kpi_deps.value_lbl.configure(text=str(deps))


class EmployeesTab(ctk.CTkFrame):
    """Таблиця + сортування + пошук + фільтри + панель дій (Edit працює)."""
    def __init__(self, master):
        super().__init__(master)
        self.pack_propagate(False)

        # ---- Стан ----
        self.current_sort = {"col": None, "direction": "asc"}
        self.all_rows = []   # повний набір (з id!)
        self.rows = []       # відфільтрований набір
        self._search_after_id = None

        # ---- Верхня панель: пошук + фільтри ----
        filters_bar = ctk.CTkFrame(self, corner_radius=8)
        filters_bar.pack(fill="x", padx=10, pady=(10, 6))

        # Пошук
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            filters_bar, textvariable=self.search_var, width=360,
            placeholder_text="Пошук (ПІБ, email, телефон, відділення, посада)"
        )
        self.search_entry.pack(side="left", padx=(8, 4), pady=8)
        self.search_var.trace_add("write", lambda *_: self._debounced_search())
        self.search_entry.bind("<Return>", lambda e: self.apply_filters())

        self.btn_search = ctk.CTkButton(filters_bar, text="🔍 Знайти", width=110, command=self.apply_filters)
        self.btn_search.pack(side="left", padx=4, pady=8)

        ctk.CTkLabel(filters_bar, text="|").pack(side="left", padx=6)

        # Фільтри
        deps = ["Усі"] + [d["name"] for d in db.get_departments()]
        poss = ["Усі"] + [p["name"] for p in db.get_positions()]
        statuses = ["Усі", "активний", "відпустка", "звільнений", "призупинено"]

        self.dep_var = ctk.StringVar(value="Усі")
        self.pos_var = ctk.StringVar(value="Усі")
        self.status_var = ctk.StringVar(value="Усі")

        self.dep_menu = ctk.CTkOptionMenu(filters_bar, values=deps, variable=self.dep_var, width=180, command=lambda _: self.apply_filters())
        self.pos_menu = ctk.CTkOptionMenu(filters_bar, values=poss, variable=self.pos_var, width=180, command=lambda _: self.apply_filters())
        self.status_menu = ctk.CTkOptionMenu(filters_bar, values=statuses, variable=self.status_var, width=150, command=lambda _: self.apply_filters())

        ctk.CTkLabel(filters_bar, text="Відділення:").pack(side="left", padx=(10, 4))
        self.dep_menu.pack(side="left", padx=4, pady=8)

        ctk.CTkLabel(filters_bar, text="Посада:").pack(side="left", padx=(10, 4))
        self.pos_menu.pack(side="left", padx=4, pady=8)

        ctk.CTkLabel(filters_bar, text="Статус:").pack(side="left", padx=(10, 4))
        self.status_menu.pack(side="left", padx=4, pady=8)

        self.btn_clear = ctk.CTkButton(filters_bar, text="✖ Скинути", width=110, command=self.clear_filters)
        self.btn_clear.pack(side="right", padx=8, pady=8)

        self.btn_refresh = ctk.CTkButton(filters_bar, text="🔄 Оновити список", width=160, command=self.load_data)
        self.btn_refresh.pack(side="right", padx=8, pady=8)

        # ---- Другий рядок: панель дій ----
        actions_bar = ctk.CTkFrame(self, corner_radius=8)
        actions_bar.pack(fill="x", padx=10, pady=(0, 6))

        # self.btn_add = ctk.CTkButton(actions_bar, text="➕ Додати", width=120, state="disabled")
        # self.btn_add.pack(side="left", padx=6, pady=8)

        self.btn_edit = ctk.CTkButton(actions_bar, text="✏️ Редагувати", width=120, command=self.edit_selected)
        self.btn_edit.pack(side="left", padx=6, pady=8)

        # self.btn_delete = ctk.CTkButton(actions_bar, text="🗑 Видалити", width=120, state="disabled")
        # self.btn_delete.pack(side="left", padx=6, pady=8)

        # ---- Таблиця ----
        table_frame = ctk.CTkFrame(self, corner_radius=8)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(6, 10))

        self.tree_scroll_y = ctk.CTkScrollbar(table_frame); self.tree_scroll_y.pack(side="right", fill="y")
        self.tree_scroll_x = ctk.CTkScrollbar(table_frame, orientation="horizontal"); self.tree_scroll_x.pack(side="bottom", fill="x")

        self.columns = ("full_name", "email", "phone", "department", "position", "birth_date", "hire_date", "employment_status")
        self.tree = ttk.Treeview(table_frame, columns=self.columns, show="headings", height=20)
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        self.tree.configure(yscrollcommand=self.tree_scroll_y.set, xscrollcommand=self.tree_scroll_x.set)
        self.tree_scroll_y.configure(command=self.tree.yview)
        self.tree_scroll_x.configure(command=self.tree.xview)

        headings = {
            "full_name": "ПІБ",
            "email": "Email",
            "phone": "Телефон",
            "department": "Відділення",
            "birth_date": "Дата народження",
            "position": "Посада",
            "hire_date": "Дата прийняття",
            "employment_status": "Статус",
        }
        for col in self.columns:
            self.tree.heading(col, text=headings[col], command=lambda col=col: self.sort_by(col))

        self.tree.column("full_name",  width=260, anchor="w")
        self.tree.column("email",      width=220, anchor="w")
        self.tree.column("phone",      width=130, anchor="center")
        self.tree.column("department", width=220, anchor="w")
        self.tree.column("position",   width=180, anchor="w")
        self.tree.column("hire_date",  width=130, anchor="center")
        self.tree.column("employment_status", width=130, anchor="center")
        self.tree.column("birth_date", width=140, anchor="center")


        # Дані + події
        self.load_data()
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())

    # ---------- Дані ----------
    def load_data(self):
        """Читає з БД і готує self.all_rows (з id); застосовує пошук/фільтри/сортування і рендер."""
        emps = db.get_employees()  # тут є e.id
        self.all_rows = [{
            "id": e.get("id"),
            "full_name": e.get("full_name") or "",
            "email": e.get("email") or "",
            "phone": e.get("phone") or "",
            "department": e.get("department") or "",
            "birth_date": e.get("birth_date") or "",
            "position": e.get("position") or "",
            "hire_date": e.get("hire_date") or "",
            "employment_status": e.get("employment_status") or "",
        } for e in emps]
        self.apply_filters()

    # ---------- Пошук/фільтри ----------
    def _debounced_search(self):
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(300, self.apply_filters)

    def apply_filters(self):
        q = (self.search_var.get() or "").strip().lower()
        dep = self.dep_var.get(); pos = self.pos_var.get(); status = self.status_var.get()

        # 1) пошук
        if not q:
            filtered = list(self.all_rows)
        else:
            def matches(r):
                hay = " ".join([r["full_name"], r["email"], r["phone"], r["department"], r["position"], r["birth_date"]]).lower()
                return q in hay
            filtered = [r for r in self.all_rows if matches(r)]

        # 2) фільтри
        if dep != "Усі":     filtered = [r for r in filtered if r["department"] == dep]
        if pos != "Усі":     filtered = [r for r in filtered if r["position"] == pos]
        if status != "Усі":  filtered = [r for r in filtered if r["employment_status"] == status]

        self.rows = filtered

        # 3) сортування/рендер
        if self.current_sort["col"]:
            self.apply_sort()
        else:
            self.render_rows()

    def clear_filters(self):
        self.search_var.set("")
        self.dep_var.set("Усі"); self.pos_var.set("Усі"); self.status_var.set("Усі")
        self.rows = list(self.all_rows)
        if self.current_sort["col"]:
            self.apply_sort()
        else:
            self.render_rows()

    # ---------- Рендер ----------
    def render_rows(self):
        for row_id in self.tree.get_children():
            self.tree.delete(row_id)
        for r in self.rows:
            # ВАЖЛИВО: зберігаємо id у iid елемента
            self.tree.insert("", "end", iid=str(r["id"]), values=(
                r["full_name"], r["email"], r["phone"],
                r["department"], r["position"], r["birth_date"], r["hire_date"], r["employment_status"]
            ))


    # ---------- Сортування ----------
    def sort_by(self, col: str):
        if self.current_sort["col"] == col:
            self.current_sort["direction"] = "desc" if self.current_sort["direction"] == "asc" else "asc"
        else:
            self.current_sort = {"col": col, "direction": "asc"}
        self.apply_sort()

    def apply_sort(self):
        col = self.current_sort["col"]; reverse = (self.current_sort["direction"] == "desc")

        def key_func(r):
            val = r.get(col, "")
            if col in ("hire_date","birth_date") and val:
                try: return datetime.fromisoformat(val)
                except ValueError: return datetime.min
            return (val or "").lower()

        self.rows.sort(key=key_func, reverse=reverse)
        self.render_rows(); self.update_heading_arrows()

    def update_heading_arrows(self):
        headings = {
            "full_name": "ПІБ", "email": "Email", "phone": "Телефон",
            "department": "Відділення", "position": "Посада",
            "hire_date": "Дата прийняття", "employment_status": "Статус",
        }
        for col in self.columns:
            text = headings[col]
            if col == self.current_sort["col"]:
                text += " ▲" if self.current_sort["direction"] == "asc" else " ▼"
            self.tree.heading(col, text=text, command=lambda col=col: self.sort_by(col))

    # ---------- Дії ----------
    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Редагування", "Будь ласка, виберіть працівника у таблиці.")
            return
        emp_id = int(sel[0])
        data = db.get_employee_raw(emp_id)
        if not data:
            messagebox.showerror("Редагування", "Не вдалося отримати дані працівника.")
            return
        EditEmployeeDialog(self, emp_id, data, on_saved=self.load_data)


class EditEmployeeDialog(ctk.CTkToplevel):
    """Модальне вікно редагування працівника з фільтрацією посад за відділенням."""
    def __init__(self, master, emp_id: int, data: dict, on_saved=None):
        super().__init__(master)
        self.emp_id = emp_id
        self.on_saved = on_saved

        self.title("Редагування працівника")
        self.resizable(True, True)
        self.minsize(720, 520)

        # Центрування
        parent = master.winfo_toplevel()
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        w, h = 820, 560
        x = px + (pw - w) // 2
        y = py + (ph - h) // 3
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.transient(parent); self.grab_set(); self.focus_force()

        # Довідники
        self.deps = db.get_departments()
        self.poss = db.get_positions()

        # Мапи id <-> name
        self.dep_by_id = {d["id"]: d["name"] for d in self.deps}
        self.dep_by_name = {v: k for k, v in self.dep_by_id.items()}
        self.pos_by_id = {p["id"]: p["name"] for p in self.poss}
        self.pos_by_name = {v: k for k, v in self.pos_by_id.items()}

        # Значення
        self.last_name  = ctk.StringVar(value=data["last_name"])
        self.first_name = ctk.StringVar(value=data["first_name"])
        self.middle_name= ctk.StringVar(value=data["middle_name"] or "")
        self.birth_date = ctk.StringVar(value=data["birth_date"] or "")
        self.email      = ctk.StringVar(value=data["email"] or "")
        self.phone      = ctk.StringVar(value=data["phone"] or "")
        self.hire_date  = ctk.StringVar(value=data["hire_date"] or "")
        self.status     = ctk.StringVar(value=data["employment_status"] or "активний")

        dep_name_init = self.dep_by_id.get(data.get("department_id"), "—")
        pos_name_init = self.pos_by_id.get(data.get("position_id"), "—")
        self.dep_name_var = ctk.StringVar(value=dep_name_init or "—")
        self.pos_name_var = ctk.StringVar(value=pos_name_init or "—")

        # Розмітка (grid)
        form = ctk.CTkFrame(self, corner_radius=8)
        form.pack(fill="both", expand=True, padx=16, pady=16)
        form.grid_columnconfigure(1, weight=1)

        def row(r, label, widget):
            ctk.CTkLabel(form, text=label, anchor="w").grid(row=r, column=0, sticky="ew", padx=(6, 10), pady=6)
            widget.grid(row=r, column=1, sticky="ew", pady=6)

        row(0, "Прізвище", ctk.CTkEntry(form, textvariable=self.last_name))
        row(1, "Ім'я", ctk.CTkEntry(form, textvariable=self.first_name))
        row(2, "По батькові", ctk.CTkEntry(form, textvariable=self.middle_name))
        row(3, "Дата народження (YYYY-MM-DD)", ctk.CTkEntry(form, textvariable=self.birth_date))
        row(4, "Email", ctk.CTkEntry(form, textvariable=self.email))
        row(5, "Телефон", ctk.CTkEntry(form, textvariable=self.phone))

        # Меню "Відділення"
        self.dep_menu = ctk.CTkOptionMenu(form,
            values=["—"] + [d["name"] for d in self.deps],
            variable=self.dep_name_var,
            width=220,
            command=self.on_department_change  # ключове: реакція на вибір
        )
        row(6, "Відділення", self.dep_menu)

        # Меню "Посада" (значення підвантажимо в on_department_change)
        self.pos_menu = ctk.CTkOptionMenu(form,
            values=["—"],
            variable=self.pos_name_var,
            width=220
        )
        row(7, "Посада", self.pos_menu)

        row(8, "Дата прийняття (YYYY-MM-DD)", ctk.CTkEntry(form, textvariable=self.hire_date))
        status_menu = ctk.CTkOptionMenu(form, values=["активний","відпустка","звільнений","призупинено"], variable=self.status, width=220)
        row(9, "Статус", status_menu)

        # Кнопки
        btns = ctk.CTkFrame(self); btns.pack(fill="x", padx=16, pady=(0,16))
        ctk.CTkButton(btns, text="Скасувати", width=140, fg_color="gray", hover_color="darkgray",
                      command=self.destroy).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Зберегти", width=140, command=self.save).pack(side="right", padx=6)

        # Ініціалізуємо список посад під поточне відділення
        self.on_department_change(self.dep_name_var.get())

    # --- підвантаження посад за відділенням ---
    def on_department_change(self, selected_dep_name: str):
        dep_id = self.dep_by_name.get(selected_dep_name)
        if dep_id:
            allowed = db.get_positions_by_department(dep_id)
            options = ["—"] + [p["name"] for p in allowed]
        else:
            options = ["—"]
        self.pos_menu.configure(values=options)

        # якщо поточна посада не входить у дозволені — скинемо на "—"
        if self.pos_name_var.get() not in options:
            self.pos_name_var.set("—")

    def save(self):
        # мінімальна валідація
        if not self.last_name.get().strip() or not self.first_name.get().strip():
            messagebox.showwarning("Перевірка", "Ім'я та прізвище є обов'язковими.")
            return
        for dv in (self.birth_date.get().strip(), self.hire_date.get().strip()):
            if dv and len(dv) != 10:
                messagebox.showwarning("Перевірка", "Дати мають формат YYYY-MM-DD.")
                return

        dep_id = self.dep_by_name.get(self.dep_name_var.get())
        pos_id = self.pos_by_name.get(self.pos_name_var.get())

        # якщо обидва вибрані — перевіримо валідність зв'язку
        if dep_id and pos_id and not db.is_position_allowed_for_department(pos_id, dep_id):
            messagebox.showwarning("Перевірка", "Обрана посада не доступна для вибраного відділення.")
            return

        payload = {
            "last_name": self.last_name.get().strip(),
            "first_name": self.first_name.get().strip(),
            "middle_name": self.middle_name.get().strip() or None,
            "birth_date": self.birth_date.get().strip() or None,
            "email": self.email.get().strip() or None,
            "phone": self.phone.get().strip() or None,
            "department_id": dep_id,
            "position_id": pos_id,
            "hire_date": self.hire_date.get().strip() or None,
            "employment_status": self.status.get().strip() or "активний",
        }

        try:
            db.update_employee(self.emp_id, payload)
            if self.on_saved:
                self.after(1, self.on_saved)
            self.after(1, self.destroy)
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося зберегти зміни: {e}")




class HRMainWindow(ctk.CTk):
    def __init__(self, current_user=None):
        super().__init__()

        self.title("HR Панель | Інформаційна система лікарні")
        self.minsize(1024, 700)
        self.state("zoomed")
        self.after(0, lambda: self.state("zoomed"))

        self.current_user = current_user or {"username": "hr_user", "role": "hr"}

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        # Вкладки
        self.dashboard_tab = self.tabview.add("Головна")
        self.employees_tab = self.tabview.add("Працівники")
        self.internships_tab = self.tabview.add("Стажування")
        self.attestations_tab = self.tabview.add("Атестації")
        self.directories_tab = self.tabview.add("Довідники") 
        self.documents_tab = self.tabview.add("Документи")
        

        # Головна
        dash = DashboardTab(self.dashboard_tab)
        dash.pack(fill="both", expand=True)

        
        # Працівники
        self.employees_view = EmployeesTab(self.employees_tab)
        self.employees_view.pack(fill="both", expand=True)

        # Стажування
        intern_tab = InternshipsTab(self.internships_tab)
        intern_tab.pack(fill="both", expand=True)

        # Атестації
        att_tab = AttestationsTab(self.attestations_tab)
        att_tab.pack(fill="both", expand=True)


        # Довідники (нова split-view вкладка)
        dirs_tab = DirectoriesTab(self.directories_tab)
        dirs_tab.pack(fill="both", expand=True)


        # Документи (нова вкладка)
        docs_tab = DocumentsTab(self.documents_tab, current_user=self.current_user)
        docs_tab.pack(fill="both", expand=True)
        # 👉 колбек автооновлення вкладки "Працівники"
        docs_tab.on_employee_created = self.employees_view.load_data
        # 👉 автооновлення вкладки "Атестації" після створення направлення
        docs_tab.on_attestation_created = att_tab.refresh


        # ---- бейдж-числа на вкладках ----
        self._install_badge_updaters()


        # ---- АВТО-ЗАВЕРШЕННЯ ПРОСТРОЧЕНИХ СТАЖУВАНЬ ПРИ СТАРТІ ----
        try:
            import db_manager as db  
            db.auto_complete_overdue()   # переведе overdue → completed (за нашою політикою)
            self.internships_view.refresh()  # оновимо таблицю після автозміни
        except Exception:
            pass


     # для лічильників в назві вкладки       
    def _set_tab_text(self, tab_name: str, new_text: str):
        try:
            btn = self.tabview._segmented_button._buttons_dict[tab_name]
            btn.configure(text=new_text)
        except Exception:
            pass

    def refresh_tab_badges(self):
        try:
            over = db.internships_overdue_count()
            soon = db.internships_soon_count()
            docs = db.docs_sent_count()
        except Exception:
            over = soon = docs = 0

        total_intern_warn = (over or 0) + (soon or 0)
        intern_label = "Стажування" + (f" • {total_intern_warn}" if total_intern_warn > 0 else "")
        docs_label   = "Документи"  + (f" • {docs}"               if docs > 0               else "")

        self._set_tab_text("Стажування", intern_label)
        self._set_tab_text("Документи",  docs_label)

    def _install_badge_updaters(self):
        self.refresh_tab_badges()
        self.after(60_000, self._install_badge_updaters)




class DirectoriesTab(ctk.CTkFrame):
    """Split-view: ліворуч Відділення, праворуч Посади (фільтр за вибраним відділенням)."""
    def __init__(self, master):
        super().__init__(master)
        self.pack_propagate(False)

        # Верхній рядок з підказкою
        header = ctk.CTkFrame(self, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(header, text="Керуйте відділеннями та посадами. Вибір відділення фільтрує список посад праворуч.",
                     font=ctk.CTkFont(size=14)).pack(side="left", padx=10, pady=8)

        # Контейнер для двох панелей
        body = ctk.CTkFrame(self, corner_radius=8)
        body.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        body.grid_columnconfigure(0, weight=1)  # departments
        body.grid_columnconfigure(1, weight=1)  # positions
        body.grid_rowconfigure(1, weight=1)

        # ===== Ліва панель: Відділення =====
        ctk.CTkLabel(body, text="Відділення", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(10,0))

        dep_toolbar = ctk.CTkFrame(body, corner_radius=6)
        dep_toolbar.grid(row=1, column=0, sticky="new", padx=(10,6), pady=(6,6))
        dep_toolbar.grid_columnconfigure(0, weight=1)

        self.dep_search_var = ctk.StringVar()
        dep_search = ctk.CTkEntry(dep_toolbar, textvariable=self.dep_search_var, placeholder_text="Пошук відділення")
        dep_search.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        dep_search.bind("<KeyRelease>", lambda e: self.refresh_departments())

        dep_btns = ctk.CTkFrame(dep_toolbar)
        dep_btns.grid(row=0, column=1, sticky="e", padx=6, pady=6)
        ctk.CTkButton(dep_btns, text="➕ Додати", width=100, command=self.add_department).pack(side="left", padx=4)
        ctk.CTkButton(dep_btns, text="✏️ Перейменувати", width=140, command=self.rename_department).pack(side="left", padx=4)
        ctk.CTkButton(dep_btns, text="🗑 Видалити", width=110, command=self.delete_department).pack(side="left", padx=4)



        dep_table_frame = ctk.CTkFrame(body, corner_radius=6)
        dep_table_frame.grid(row=2, column=0, sticky="nsew", padx=(10,6), pady=(0,10))

        self.dep_tree = ttk.Treeview(dep_table_frame, columns=("name","emp_count"), show="headings", height=18)
        self.dep_tree.heading("name", text="Назва")
        self.dep_tree.heading("emp_count", text="К-сть працівників")
        self.dep_tree.column("name", width=320, anchor="w")
        self.dep_tree.column("emp_count", width=140, anchor="center")
        self.dep_tree.pack(fill="both", expand=True, padx=6, pady=6)

        self.dep_tree.bind("<<TreeviewSelect>>", lambda e: self.refresh_positions())

        # ===== Права панель: Посади =====
        ctk.CTkLabel(body, text="Посади", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=1, sticky="w", padx=10, pady=(10,0))

        pos_toolbar = ctk.CTkFrame(body, corner_radius=6)
        pos_toolbar.grid(row=1, column=1, sticky="new", padx=(6,10), pady=(6,6))
        pos_toolbar.grid_columnconfigure(0, weight=1)

        self.pos_search_var = ctk.StringVar()
        pos_search = ctk.CTkEntry(pos_toolbar, textvariable=self.pos_search_var, placeholder_text="Пошук посади")
        pos_search.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        pos_search.bind("<KeyRelease>", lambda e: self.refresh_positions())

        pos_btns = ctk.CTkFrame(pos_toolbar)
        pos_btns.grid(row=0, column=1, sticky="e", padx=6, pady=6)
        ctk.CTkButton(pos_btns, text="➕ Додати", width=100, command=self.add_position).pack(side="left", padx=4)
        ctk.CTkButton(pos_btns, text="✏️ Перейменувати", width=140, command=self.rename_position).pack(side="left", padx=4)
        ctk.CTkButton(pos_btns, text="🗑 Видалити", width=110, command=self.delete_position).pack(side="left", padx=4)
        ctk.CTkButton(pos_btns, text="👁 Показати всі", width=120, command=self.clear_department_selection).pack(side="left", padx=4)

        pos_table_frame = ctk.CTkFrame(body, corner_radius=6)
        pos_table_frame.grid(row=2, column=1, sticky="nsew", padx=(6,10), pady=(0,10))

        self.pos_tree = ttk.Treeview(pos_table_frame, columns=("name","emp_count"), show="headings", height=18)
        self.pos_tree.heading("name", text="Назва")
        self.pos_tree.heading("emp_count", text="К-сть працівників")
        self.pos_tree.column("name", width=320, anchor="w")
        self.pos_tree.column("emp_count", width=140, anchor="center")
        self.pos_tree.pack(fill="both", expand=True, padx=6, pady=6)

        # Початкове наповнення
        self.refresh_departments()
        self.refresh_positions()

    # ===== Оновлення таблиць =====
    def refresh_departments(self):
        q = (self.dep_search_var.get() or "").strip().lower()
        deps = db.get_departments()
        # додаємо лічильники
        data = []
        for d in deps:
            if q and q not in d["name"].lower():
                continue
            cnt = db.count_employees_in_department(d["id"])
            data.append({"id": d["id"], "name": d["name"], "emp_count": cnt})

        for iid in self.dep_tree.get_children():
            self.dep_tree.delete(iid)
        for d in data:
            self.dep_tree.insert("", "end", iid=str(d["id"]), values=(d["name"], d["emp_count"]))

        # після оновлення відділень — оновимо й посади (бо фільтр залежить)
        self.refresh_positions()

    def refresh_positions(self):
        q = (self.pos_search_var.get() or "").strip().lower()
        # якщо вибране відділення — показуємо тільки дозволені посади
        sel = self.dep_tree.selection()
        if sel:
            dep_id = int(sel[0])
            poss = db.get_positions_by_department(dep_id)
        else:
            poss = db.get_all_positions()

        data = []
        for p in poss:
            if q and q not in p["name"].lower():
                continue
            cnt = db.count_employees_in_position(p["id"])
            data.append({"id": p["id"], "name": p["name"], "emp_count": cnt})

        for iid in self.pos_tree.get_children():
            self.pos_tree.delete(iid)
        for p in data:
            self.pos_tree.insert("", "end", iid=str(p["id"]), values=(p["name"], p["emp_count"]))

    # ===== Дії: Відділення =====
    def add_department(self):
        name = self._prompt_text("Нове відділення", "Введіть назву відділення:")
        if not name: return
        try:
            db.add_department(name.strip())
            self.refresh_departments()
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося додати: {e}")

    def rename_department(self):
        sel = self.dep_tree.selection()
        if not sel:
            messagebox.showwarning("Перейменування", "Оберіть відділення.")
            return
        dep_id = int(sel[0])
        old = self.dep_tree.item(sel[0], "values")[0]
        new_name = self._prompt_text("Перейменувати відділення", "Нова назва:", initial=old)
        if not new_name: return
        try:
            db.rename_department(dep_id, new_name.strip())
            self.refresh_departments()
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося перейменувати: {e}")

    def delete_department(self):
        sel = self.dep_tree.selection()
        if not sel:
            messagebox.showwarning("Видалення", "Оберіть відділення.")
            return
        dep_id = int(sel[0])
        if db.count_employees_in_department(dep_id) > 0:
            messagebox.showwarning("Заборонено", "Неможливо видалити: у відділенні є працівники.")
            return
        if not messagebox.askyesno("Підтвердження", "Видалити відділення?"):
            return
        try:
            db.delete_department(dep_id)
            self.refresh_departments()
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося видалити: {e}")

    def clear_department_selection(self):
        sel = self.dep_tree.selection()
        if sel:
            self.dep_tree.selection_remove(sel[0])
        self.refresh_positions()



    # ===== Дії: Посади =====
    def add_position(self):
        name = self._prompt_text("Нова посада", "Введіть назву посади:")
        if not name:
            return
        try:
            new_id = db.add_position(name.strip())  # тепер повертає id
            # якщо вибране відділення — одразу прив'язуємо
            sel = self.dep_tree.selection()
            if sel:
                dep_id = int(sel[0])
                db.link_position_to_department(new_id, dep_id)
            self.refresh_positions()
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося додати: {e}")


    def rename_position(self):
        sel = self.pos_tree.selection()
        if not sel:
            messagebox.showwarning("Перейменування", "Оберіть посаду.")
            return
        pos_id = int(sel[0])
        old = self.pos_tree.item(sel[0], "values")[0]
        new_name = self._prompt_text("Перейменувати посаду", "Нова назва:", initial=old)
        if not new_name: return
        try:
            db.rename_position(pos_id, new_name.strip())
            self.refresh_positions()
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося перейменувати: {e}")

    def delete_position(self):
        sel = self.pos_tree.selection()
        if not sel:
            messagebox.showwarning("Видалення", "Оберіть посаду.")
            return
        pos_id = int(sel[0])
        if db.count_employees_in_position(pos_id) > 0:
            messagebox.showwarning("Заборонено", "Неможливо видалити: з цією посадою пов'язані працівники.")
            return
        if not messagebox.askyesno("Підтвердження", "Видалити посаду?"):
            return
        try:
            db.delete_position(pos_id)
            self.refresh_positions()
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося видалити: {e}")

    # ===== Допоміжне текстове діалогове вікно =====
    def _prompt_text(self, title: str, label: str, initial: str = "") -> str | None:
        # Простий модальний CTkToplevel з одним Entry
        dlg = ctk.CTkToplevel(self)
        dlg.title(title)
        dlg.geometry("480x160")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        wrap = ctk.CTkFrame(dlg, corner_radius=8)
        wrap.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(wrap, text=label).pack(anchor="w", pady=(0,6))
        var = ctk.StringVar(value=initial)
        entry = ctk.CTkEntry(wrap, textvariable=var)
        entry.pack(fill="x")
        entry.focus_set()

        btns = ctk.CTkFrame(wrap)
        btns.pack(fill="x", pady=(12,0))
        res = {"value": None}
        def ok():
            v = (var.get() or "").strip()
            res["value"] = v if v else None
            dlg.destroy()
        def cancel():
            res["value"] = None
            dlg.destroy()
        ctk.CTkButton(btns, text="OK", width=120, command=ok).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Скасувати", width=120, fg_color="gray", hover_color="darkgray", command=cancel).pack(side="right", padx=6)
        dlg.wait_window()
        return res["value"]




if __name__ == "__main__":
    app = HRMainWindow(current_user={"username": "olena.shevchenko", "role": "hr"})
    app.mainloop()
