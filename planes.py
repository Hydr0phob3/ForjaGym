import customtkinter as ctk
from tkinter import messagebox


ORANGE = "#FF6600"
BACKGROUND = "#111315"
CARD = "#202429"
SIDEBAR = "#191C20"
TEXT = "#FFFFFF"
SECONDARY = "#A0A5AB"
GREEN = "#2E8B57"
RED = "#A93226"


class PlanesWindow(ctk.CTkToplevel):

    def __init__(self, parent, db):

        super().__init__(parent)

        self.parent = parent
        self.db = db
        self.selected_plan_id = None
        self.plan_rows = {}
        self.money_entries = []

        self.title("FORJAGYM | Gestión de planes")
        self.geometry("950x650")
        self.minsize(800, 550)
        self.configure(fg_color=BACKGROUND)

        self.transient(parent)
        self.grab_set()

        self.create_layout()
        self.refresh_plans()


    def create_layout(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=25, pady=(22, 8))

        ctk.CTkLabel(
            header,
            text="GESTIÓN DE PLANES",
            font=("Arial", 25, "bold"),
            text_color=TEXT
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Creá planes, configurá frecuencias y mantené actualizados los precios.",
            font=("Arial", 12),
            text_color=SECONDARY
        ).pack(anchor="w", pady=(4, 0))

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", padx=25, pady=12)

        ctk.CTkButton(
            toolbar,
            text="+  NUEVO PLAN",
            width=150,
            height=38,
            fg_color=ORANGE,
            hover_color="#D95700",
            text_color="#FFFFFF",
            font=("Arial", 12, "bold"),
            command=self.new_plan
        ).pack(side="left")

        ctk.CTkButton(
            toolbar,
            text="ACTUALIZAR",
            width=115,
            height=38,
            fg_color="#343A40",
            hover_color="#454C53",
            text_color=TEXT,
            command=self.refresh_plans
        ).pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=CARD,
            corner_radius=12
        )
        self.list_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=25,
            pady=(0, 18)
        )
        self.list_frame.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkLabel(
            self,
            text="Los planes desactivados se conservan y no estarán disponibles para nuevos pagos.",
            font=("Arial", 11),
            text_color=SECONDARY
        )
        footer.grid(row=3, column=0, sticky="w", padx=28, pady=(0, 15))


    def refresh_money_visibility(self):
        self.refresh_plans()
        show_char = "" if self.parent.show_money else "•"
        valid_entries = []
        for entry in self.money_entries:
            try:
                if entry.winfo_exists():
                    entry.configure(show=show_char)
                    valid_entries.append(entry)
            except Exception:
                pass
        self.money_entries = valid_entries

    def refresh_plans(self):

        for widget in self.list_frame.winfo_children():
            widget.destroy()

        plans = self.db.get_plans(active_only=False)

        if not plans:
            ctk.CTkLabel(
                self.list_frame,
                text="Todavía no hay planes cargados.",
                text_color=SECONDARY,
                font=("Arial", 13)
            ).pack(pady=30)
            return

        for plan in plans:
            self.create_plan_row(plan)


    def create_plan_row(self, plan):

        row = ctk.CTkFrame(
            self.list_frame,
            fg_color="#292E34",
            corner_radius=10
        )
        row.pack(fill="x", padx=8, pady=6)
        row.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.grid(row=0, column=0, sticky="ew", padx=15, pady=12)

        name_color = TEXT if plan["active"] else SECONDARY
        status_text = "ACTIVO" if plan["active"] else "INACTIVO"
        status_color = GREEN if plan["active"] else RED

        ctk.CTkLabel(
            info,
            text=plan["name"],
            font=("Arial", 15, "bold"),
            text_color=name_color
        ).pack(anchor="w")

        details = (
            f'{plan["days_per_week"]} días/semana  •  '
            f'{plan["duration_days"]} días de duración  •  '
            + (f'${plan["price"]:,}'.replace(",", ".") if self.parent.show_money else "••••••")
        )

        ctk.CTkLabel(
            info,
            text=details,
            font=("Arial", 12),
            text_color=SECONDARY
        ).pack(anchor="w", pady=(3, 0))

        ctk.CTkLabel(
            row,
            text=status_text,
            text_color=status_color,
            font=("Arial", 10, "bold"),
            width=75
        ).grid(row=0, column=1, padx=8)

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.grid(row=0, column=2, padx=10, pady=8)

        ctk.CTkButton(
            actions,
            text="EDITAR",
            width=75,
            height=30,
            fg_color="#3B4650",
            hover_color="#4A5864",
            command=lambda p=plan: self.edit_plan(p)
        ).pack(side="left", padx=3)

        if plan["active"]:
            ctk.CTkButton(
                actions,
                text="DESACTIVAR",
                width=100,
                height=30,
                fg_color="#71352A",
                hover_color="#8E4031",
                command=lambda p=plan: self.toggle_plan(p, False)
            ).pack(side="left", padx=3)
        else:
            ctk.CTkButton(
                actions,
                text="ACTIVAR",
                width=85,
                height=30,
                fg_color="#246B45",
                hover_color="#2D8555",
                command=lambda p=plan: self.toggle_plan(p, True)
            ).pack(side="left", padx=3)

    def new_plan(self):

        self.open_plan_form()


    def edit_plan(self, plan):

        self.open_plan_form(plan)


    def open_plan_form(self, plan=None):

        is_edit = plan is not None

        dialog = ctk.CTkToplevel(self)
        dialog.title("Editar plan" if is_edit else "Nuevo plan")
        dialog.geometry("450x520")
        dialog.resizable(False, False)
        dialog.configure(fg_color=BACKGROUND)
        dialog.transient(self)
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog, fg_color=CARD, corner_radius=12)
        frame.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            frame,
            text="EDITAR PLAN" if is_edit else "CREAR PLAN",
            font=("Arial", 20, "bold"),
            text_color=ORANGE
        ).pack(anchor="w", padx=22, pady=(20, 15))

        ctk.CTkLabel(
            frame,
            text="Nombre del plan",
            text_color=TEXT,
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=22)

        name_entry = ctk.CTkEntry(
            frame,
            height=36,
            placeholder_text="Ej.: Pase semanal, Quincenal..."
        )
        name_entry.pack(fill="x", padx=22, pady=(5, 10))

        ctk.CTkLabel(
            frame,
            text="Frecuencia semanal (1 a 7 días)",
            text_color=TEXT,
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=22)

        days_entry = ctk.CTkEntry(
            frame,
            height=36,
            placeholder_text="Ej.: 5"
        )
        days_entry.pack(fill="x", padx=22, pady=(5, 10))

        ctk.CTkLabel(
            frame,
            text="Duración de la cuota (en días)",
            text_color=TEXT,
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=22)

        duration_entry = ctk.CTkEntry(
            frame,
            height=36,
            placeholder_text="Ej.: 7, 15 o 30"
        )
        duration_entry.pack(fill="x", padx=22, pady=(5, 10))

        ctk.CTkLabel(
            frame,
            text="Precio ($)",
            text_color=TEXT,
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=22)

        price_entry = ctk.CTkEntry(
            frame,
            height=36,
            placeholder_text="Ej.: 35000",
            show="" if self.parent.show_money else "•"
        )
        price_entry.pack(fill="x", padx=22, pady=(5, 15))
        self.money_entries.append(price_entry)

        if is_edit:
            name_entry.insert(0, plan["name"])
            days_entry.insert(0, str(plan["days_per_week"]))
            duration_entry.insert(0, str(plan["duration_days"]))
            price_entry.insert(0, str(plan["price"]))
        else:
            duration_entry.insert(0, "30")

        def save_plan():

            name = name_entry.get().strip()

            try:
                days = int(days_entry.get().strip())
                duration = int(duration_entry.get().strip())
                price = int(price_entry.get().strip())
            except ValueError:
                messagebox.showwarning(
                    "Datos inválidos",
                    "Frecuencia, duración y precio deben ser números enteros.",
                    parent=dialog
                )
                return

            try:
                if is_edit:
                    self.db.update_plan(
                        plan["id"],
                        name,
                        days,
                        duration,
                        price
                    )
                else:
                    self.db.add_plan(
                        name,
                        days,
                        duration,
                        price
                    )

            except ValueError as error:
                messagebox.showerror(
                    "No se pudo guardar",
                    str(error),
                    parent=dialog
                )
                return
            except Exception as error:
                messagebox.showerror(
                    "Error",
                    f"No se pudo guardar el plan.\n\nDetalle: {error}",
                    parent=dialog
                )
                return

            dialog.destroy()
            self.refresh_plans()

            messagebox.showinfo(
                "FORJAGYM",
                "El plan se guardó correctamente.",
                parent=self
            )

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(fill="x", padx=22, pady=(0, 16))

        ctk.CTkButton(
            buttons,
            text="CANCELAR",
            width=110,
            height=38,
            fg_color="#343A40",
            hover_color="#454C53",
            command=dialog.destroy
        ).pack(side="left")

        ctk.CTkButton(
            buttons,
            text="GUARDAR PLAN",
            width=145,
            height=38,
            fg_color=ORANGE,
            hover_color="#D95700",
            font=("Arial", 11, "bold"),
            command=save_plan
        ).pack(side="right")

        name_entry.focus()

    def toggle_plan(self, plan, activate):

        action = "activar" if activate else "desactivar"

        confirmation = messagebox.askyesno(
            "Confirmar acción",
            f'¿Seguro que querés {action} el plan "{plan["name"]}"?',
            parent=self
        )

        if not confirmation:
            return

        try:
            self.db.set_plan_active(plan["id"], activate)
        except Exception as error:
            messagebox.showerror(
                "Error",
                f"No se pudo actualizar el plan.\n\nDetalle: {error}",
                parent=self
            )
            return

        self.refresh_plans()
