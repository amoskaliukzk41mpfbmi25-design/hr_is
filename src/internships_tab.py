# src/internships_tab.py
from tkinter import ttk, simpledialog
import customtkinter as ctk
import db_manager as db
from tkinter import messagebox

class InternshipsTab(ctk.CTkFrame):
    """Вкладка 'Стажування': список + фільтри + дії (Продовжити, Завершити, Неуспішно)."""
    def __init__(self, master):
        super().__init__(master)
        self.pack_propagate(False)

        # ---- Верхня панель ----
        bar = ctk.CTkFrame(self)
        bar.pack(fill="x", padx=10, pady=(10,6))

        ctk.CTkLabel(bar, text="Статус:").pack(side="left", padx=(6,6))
        self.status_var = ctk.StringVar(value="active")
        self.status_filter = ctk.CTkComboBox(
            bar, values=["усі","active","completed","failed"],
            variable=self.status_var, width=150, command=lambda _=None: self.refresh()
        )
        self.status_filter.pack(side="left")

        ctk.CTkLabel(bar, text="   Пошук:").pack(side="left", padx=(12,6))
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(bar, textvariable=self.search_var, width=240, placeholder_text="ПІБ / Відділення / Посада")
        self.search_entry.pack(side="left")
        ctk.CTkButton(bar, text="Знайти", width=90, command=self.refresh).pack(side="left", padx=6)

        ctk.CTkButton(bar, text="Оновити", width=110, command=self.refresh).pack(side="right", padx=6)

        # ---- Група дій ----
        actions = ctk.CTkFrame(self)
        actions.pack(fill="x", padx=10, pady=(0,6))
        ctk.CTkButton(actions, text="Продовжити…", width=140, command=self.action_extend).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Завершити зараз", width=160, command=self.action_complete).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Позначити як неуспішно", width=200, command=self.action_fail).pack(side="left", padx=4)

        # ---- Таблиця ----
        wrap = ctk.CTkFrame(self, corner_radius=8)
        wrap.pack(fill="both", expand=True, padx=10, pady=(0,10))

        self.tree = ttk.Treeview(wrap, columns=("full_name","deptpos","start","planned","days_left","status"), show="headings", height=18, selectmode="extended")
        self.tree.heading("full_name", text="ПІБ")
        self.tree.heading("deptpos",   text="Відділення / Посада")
        self.tree.heading("start",     text="Початок")
        self.tree.heading("planned",   text="План. завершення")
        self.tree.heading("days_left", text="Залишилось днів")
        self.tree.heading("status",    text="Статус")

        self.tree.column("full_name", width=260, anchor="w")
        self.tree.column("deptpos",   width=320, anchor="w")
        self.tree.column("start",     width=120, anchor="center")
        self.tree.column("planned",   width=150, anchor="center")
        self.tree.column("days_left", width=140, anchor="center")
        self.tree.column("status",    width=120, anchor="center")

        self.tree.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        yscroll = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side="right", fill="y")

        # стилі підсвітки (єдине місце де конфігуруємо кольори)
        self.tree.tag_configure("overdue",   background="#FF8A80")  # прострочено
        self.tree.tag_configure("critical",  background="#FFB3B3")  # 0–1 день
        self.tree.tag_configure("very_soon", background="#FFE0B2")  # 2–6 днів
        self.tree.tag_configure("due_soon",  background="#FFF4CC")  # 7–14 днів



        # Контекст-меню (ПКМ)
        self.menu = tk_menu = ctk.CTkMenu(self) if hasattr(ctk, "CTkMenu") else None
        # Якщо у твоїй версії customtkinter немає CTkMenu — просто опустимо контекст-меню.

        self.tree.bind("<Button-3>", self._open_context_menu)  # ПКМ
        self.refresh()

    # ---- Helpers ----
    def _selected_ids(self):
        ids = []
        for iid in self.tree.selection():
            try:
                ids.append(int(iid))
            except Exception:
                pass
        return ids

    def _open_context_menu(self, event):
        if not self.menu:
            return
        sel = self._selected_ids()
        if not sel:
            return
        try:
            self.menu = m = ctk.CTkMenu(self)  # recreate each time (workaround)
            m.add_command(label="Продовжити…", command=self.action_extend)
            m.add_command(label="Завершити зараз", command=self.action_complete)
            m.add_command(label="Позначити як неуспішно", command=self.action_fail)
            m.tk_popup(event.x_root, event.y_root)  # type: ignore
        except Exception:
            pass

    def _colorize_row(self, iid, days_left, status):
        if status != "active":
            return
        try:
            d = int(days_left)
        except Exception:
            return

        if d < 0:
            self.tree.item(iid, tags=("overdue",))
        elif d <= 1:
            self.tree.item(iid, tags=("critical",))
        elif d <= 6:
            self.tree.item(iid, tags=("very_soon",))
        elif d <= 14:
            self.tree.item(iid, tags=("due_soon",))



    # ---- Data ----
    def refresh(self):
        try:
            db.auto_complete_overdue()
        except Exception:
            pass

        for iid in self.tree.get_children():
            self.tree.delete(iid)

        rows = db.list_internships(status=self.status_var.get(), search=(self.search_var.get() or "").strip())

        from datetime import date
        today = date.today()

        for r in rows:
            # days_left
            left = ""
            try:
                y, m, d = map(int, (r["planned_end_date"] or "").split("-"))
                from datetime import date as _d
                dd = (_d(y, m, d) - today).days
                left = str(dd)
            except Exception:
                pass

            dep = r.get("department_name") or "—"
            pos = r.get("position_name") or "—"
            iid = str(r["id"])
            self.tree.insert(
                "", "end", iid=iid, values=(
                    r.get("full_name",""),
                    f"{dep} / {pos}",
                    r.get("start_date",""),
                    r.get("planned_end_date",""),
                    left,
                    r.get("status","")
                )
            )
            self._colorize_row(iid, left, r.get("status",""))

    # ---- Actions ----
    def action_extend(self):
        sel = self._selected_ids()
        if not sel:
            messagebox.showwarning("Продовжити", "Оберіть 1 або більше стажувань у статусі 'active'.")
            return
        try:
            add = simpledialog.askinteger("Продовжити", "На скільки місяців продовжити?", minvalue=1, maxvalue=12, parent=self)
            if not add:
                return
            note = simpledialog.askstring("Коментар (опціонально)", "Додати коментар?", parent=self) or ""
            for iid in sel:
                db.extend_internship(iid, add, note)
            self.refresh()
            messagebox.showinfo("Готово", f"Продовжено на +{add} міс.")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося продовжити: {e}")

    def action_complete(self):
        sel = self._selected_ids()
        if not sel:
            messagebox.showwarning("Завершити", "Оберіть 1 або більше стажувань у статусі 'active'.")
            return
        if not messagebox.askyesno("Підтвердження", "Завершити вибрані стажування сьогодні?"):
            return
        try:
            for iid in sel:
                db.complete_internship_now(iid, note="")
            self.refresh()
            messagebox.showinfo("Готово", "Стажування завершено.")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося завершити: {e}")

    def action_fail(self):
        sel = self._selected_ids()
        if not sel:
            messagebox.showwarning("Неуспішно", "Оберіть 1 або більше стажувань у статусі 'active'.")
            return
        note = simpledialog.askstring("Причина", "Вкажіть причину/коментар:", parent=self) or ""
        if not messagebox.askyesno("Підтвердження", "Позначити вибрані стажування як неуспішні?"):
            return
        try:
            for iid in sel:
                db.fail_internship(iid, note=note)
            self.refresh()
            messagebox.showinfo("Готово", "Позначено як неуспішно.")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося змінити статус: {e}")
