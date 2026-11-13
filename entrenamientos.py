
import customtkinter as ctk
from tkinter import messagebox

ORANGE = "#FF6600"
BACKGROUND = "#111315"
CARD = "#202429"
TEXT = "#FFFFFF"
SECONDARY = "#A0A5AB"
FIELD = "#171A1E"
BORDER = "#383D43"

DAYS = [
    "Lunes", "Martes", "Miércoles", "Jueves",
    "Viernes", "Sábado", "Domingo"
]

MINIMUM_ROWS = 5


class EntrenamientosWindow(ctk.CTkToplevel):
    """Gestión de rutinas maestras de FORJAGYM."""

    def __init__(self, parent, db):
        super().__init__(parent)

        self.parent = parent
        self.db = db
        self.selected_template_id = None
        self.detail = None
        self.exercise_rows = []

        self.title("FORJAGYM | Entrenamientos")
        self.geometry("1350x850")
        self.minsize(1100, 700)
        self.configure(fg_color=BACKGROUND)

        self.transient(parent)
        self.grab_set()

        self._build()
        self.refresh_templates()
        self._create_empty_rows(MINIMUM_ROWS)

    # ==========================================
    # INTERFAZ PRINCIPAL
    # ==========================================

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(
            row=0, column=0,
            sticky="ew", padx=24, pady=(20, 12)
        )

        ctk.CTkLabel(
            header,
            text="ENTRENAMIENTOS",
            font=("Arial", 26, "bold"),
            text_color=ORANGE
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Creá y organizá rutinas maestras por días de la semana.",
            font=("Arial", 12),
            text_color=SECONDARY
        ).pack(anchor="w", pady=(3, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(
            row=1, column=0,
            sticky="nsew", padx=20, pady=(0, 20)
        )

        body.grid_columnconfigure(0, weight=1, minsize=250)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)

        self._build_template_panel(body)
        self._build_editor_panel(body)

    # ==========================================
    # PANEL DE RUTINAS
    # ==========================================

    def _build_template_panel(self, parent):
        left = ctk.CTkFrame(
            parent,
            fg_color=CARD,
            corner_radius=12
        )

        left.grid(
            row=0, column=0,
            sticky="nsew", padx=(0, 10)
        )

        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left,
            text="RUTINAS MAESTRAS",
            font=("Arial", 14, "bold"),
            text_color=TEXT
        ).grid(
            row=0, column=0,
            sticky="w", padx=15, pady=(15, 8)
        )

        ctk.CTkButton(
            left,
            text="+ NUEVA RUTINA",
            height=38,
            fg_color=ORANGE,
            hover_color="#D95700",
            command=self.new_template
        ).grid(
            row=1, column=0,
            sticky="ew", padx=12, pady=(0, 10)
        )

        self.template_list = ctk.CTkScrollableFrame(
            left,
            fg_color="transparent"
        )

        self.template_list.grid(
            row=2, column=0,
            sticky="nsew", padx=8, pady=5
        )

    # ==========================================
    # PANEL EDITOR
    # ==========================================

    def _build_editor_panel(self, parent):
        right = ctk.CTkFrame(
            parent,
            fg_color=CARD,
            corner_radius=12
        )

        right.grid(row=0, column=1, sticky="nsew")

        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(
            right,
            text="DATOS DE LA RUTINA",
            font=("Arial", 14, "bold"),
            text_color=TEXT
        ).grid(
            row=0, column=0,
            sticky="w", padx=18, pady=(15, 8)
        )

        self.name_entry = ctk.CTkEntry(
            right,
            placeholder_text="Nombre de la rutina (ej. Hipertrofia 4 días)",
            height=36
        )

        self.name_entry.grid(
            row=1, column=0,
            sticky="ew", padx=18, pady=5
        )

        self.description_entry = ctk.CTkEntry(
            right,
            placeholder_text="Descripción general (opcional)",
            height=36
        )

        self.description_entry.grid(
            row=2, column=0,
            sticky="ew", padx=18, pady=5
        )

        actions = ctk.CTkFrame(
            right,
            fg_color="transparent"
        )

        actions.grid(
            row=3, column=0,
            sticky="ew", padx=18, pady=8
        )

        ctk.CTkButton(
            actions,
            text="GUARDAR RUTINA",
            fg_color=ORANGE,
            hover_color="#D95700",
            command=self.save_template
        ).pack(side="left")

        ctk.CTkButton(
            actions,
            text="ELIMINAR",
            fg_color="#8E3030",
            hover_color="#6F2424",
            command=self.delete_template
        ).pack(side="left", padx=8)

        ctk.CTkLabel(
            right,
            text="PLANIFICACIÓN SEMANAL",
            font=("Arial", 14, "bold"),
            text_color=TEXT
        ).grid(
            row=4, column=0,
            sticky="w", padx=18, pady=(8, 5)
        )

        day_area = ctk.CTkFrame(
            right,
            fg_color="transparent"
        )

        day_area.grid(
            row=5, column=0,
            sticky="nsew", padx=18, pady=(0, 8)
        )

        day_area.grid_columnconfigure(1, weight=1)
        day_area.grid_rowconfigure(5, weight=1)

        self.day_var = ctk.StringVar(value=DAYS[0])

        ctk.CTkLabel(
            day_area,
            text="Día",
            text_color=SECONDARY
        ).grid(
            row=0, column=0,
            sticky="w", padx=(0, 8), pady=4
        )

        self.day_menu = ctk.CTkOptionMenu(
            day_area,
            values=DAYS,
            variable=self.day_var,
            command=self.load_day
        )

        self.day_menu.grid(
            row=0, column=1,
            sticky="w", pady=4
        )

        ctk.CTkLabel(
            day_area,
            text="Grupos musculares",
            text_color=SECONDARY
        ).grid(
            row=1, column=0,
            sticky="w", padx=(0, 8), pady=4
        )

        self.groups_entry = ctk.CTkEntry(
            day_area,
            placeholder_text="Ej. Espalda + Bíceps"
        )

        self.groups_entry.grid(
            row=1, column=1,
            sticky="ew", pady=4
        )

        ctk.CTkLabel(
            day_area,
            text="Notas del día",
            text_color=SECONDARY
        ).grid(
            row=2, column=0,
            sticky="w", padx=(0, 8), pady=4
        )

        self.day_notes_entry = ctk.CTkEntry(
            day_area,
            placeholder_text="Ej. Calentamiento previo, intensidad, indicaciones..."
        )

        self.day_notes_entry.grid(
            row=2, column=1,
            sticky="ew", pady=4
        )

        # ENCABEZADO DE LA PLANILLA

        table_title = ctk.CTkFrame(
            day_area,
            fg_color="transparent"
        )

        table_title.grid(
            row=3, column=0,
            columnspan=2, sticky="ew",
            pady=(15, 5)
        )

        ctk.CTkLabel(
            table_title,
            text="EJERCICIOS DEL DÍA",
            font=("Arial", 13, "bold"),
            text_color=TEXT
        ).pack(side="left")

        ctk.CTkLabel(
            table_title,
            text="Una fila por ejercicio",
            font=("Arial", 10),
            text_color=SECONDARY
        ).pack(side="right")

        # COLUMNAS DE LA TABLA

        table_header = ctk.CTkFrame(
            day_area,
            fg_color="#30363D",
            corner_radius=6
        )

        table_header.grid(
            row=4, column=0,
            columnspan=2, sticky="ew",
            pady=(0, 3)
        )

        column_weights = [5, 1, 2, 2, 5, 1]

        for column, weight in enumerate(column_weights):
            table_header.grid_columnconfigure(
                column, weight=weight
            )

        headers = [
            "EJERCICIO",
            "SERIES",
            "REPETICIONES",
            "PESO REF.",
            "NOTAS / TIPS",
            ""
        ]

        for column, title in enumerate(headers):
            ctk.CTkLabel(
                table_header,
                text=title,
                font=("Arial", 10, "bold"),
                text_color=TEXT,
                anchor="w"
            ).grid(
                row=0, column=column,
                sticky="ew", padx=5, pady=9
            )

        # CONTENEDOR CON SCROLL

        self.table_frame = ctk.CTkScrollableFrame(
            day_area,
            fg_color="#171A1E",
            corner_radius=6
        )

        self.table_frame.grid(
            row=5, column=0,
            columnspan=2, sticky="nsew"
        )

        for column, weight in enumerate(column_weights):
            self.table_frame.grid_columnconfigure(
                column, weight=weight
            )

        # BOTONES DE LA PLANILLA

        table_actions = ctk.CTkFrame(
            day_area,
            fg_color="transparent"
        )

        table_actions.grid(
            row=6, column=0,
            columnspan=2, sticky="ew",
            pady=(8, 5)
        )

        ctk.CTkButton(
            table_actions,
            text="+ AGREGAR EJERCICIO",
            height=32,
            fg_color="#30363D",
            hover_color="#454D56",
            command=self.add_exercise_row
        ).pack(side="left")

        ctk.CTkLabel(
            table_actions,
            text="Podés dejar filas vacías.",
            font=("Arial", 10),
            text_color=SECONDARY
        ).pack(side="right")

        # PIE

        footer = ctk.CTkFrame(
            right,
            fg_color="transparent"
        )

        footer.grid(
            row=6, column=0,
            sticky="ew", padx=18, pady=(0, 15)
        )

        ctk.CTkButton(
            footer,
            text="GUARDAR DÍA",
            fg_color=ORANGE,
            hover_color="#D95700",
            command=self.save_day
        ).pack(side="left")

        ctk.CTkButton(
            footer,
            text="QUITAR DÍA",
            fg_color="#555B63",
            hover_color="#41464D",
            command=self.remove_day
        ).pack(side="left", padx=8)

        ctk.CTkLabel(
            footer,
            text="Los cambios se guardan en la base local.",
            text_color=SECONDARY,
            font=("Arial", 10)
        ).pack(side="right")

    # ==========================================
    # FILAS DE EJERCICIOS
    # ==========================================

    def add_exercise_row(self, values=None):
        if values is None:
            values = ["", "", "", "", ""]

        row_number = len(self.exercise_rows)

        fields = []

        widths = [180, 55, 85, 85, 190]

        for index, value in enumerate(values):
            entry = ctk.CTkEntry(
                self.table_frame,
                height=34,
                width=widths[index],
                fg_color=FIELD,
                border_color=BORDER,
                text_color=TEXT,
                placeholder_text=(
                    "Nombre del ejercicio" if index == 0 else
                    "N°" if index == 1 else
                    "Ej. 8-10" if index == 2 else
                    "Opcional" if index == 3 else
                    "Indicaciones técnicas"
                )
            )

            entry.grid(
                row=row_number,
                column=index,
                sticky="ew",
                padx=3,
                pady=3
            )

            if value is not None and str(value) != "":
                entry.insert(0, str(value))

            fields.append(entry)

        remove_button = ctk.CTkButton(
            self.table_frame,
            text="✕",
            width=30,
            height=30,
            fg_color="#6F3030",
            hover_color="#923A3A",
            command=lambda f=fields: self.remove_exercise_row(f)
        )

        remove_button.grid(
            row=row_number,
            column=5,
            padx=3,
            pady=3
        )

        self.exercise_rows.append({
            "fields": fields,
            "button": remove_button
        })

        return fields

    def _create_empty_rows(self, amount):
        for _ in range(amount):
            self.add_exercise_row()

    def remove_exercise_row(self, fields):
        for index, row in enumerate(self.exercise_rows):
            if row["fields"] == fields:
                for widget in row["fields"]:
                    widget.destroy()

                row["button"].destroy()
                self.exercise_rows.pop(index)
                break

        self._reindex_rows()

        if not self.exercise_rows:
            self.add_exercise_row()

    def _reindex_rows(self):
        for row_number, row in enumerate(self.exercise_rows):
            for column, entry in enumerate(row["fields"]):
                entry.grid_configure(
                    row=row_number,
                    column=column
                )

            row["button"].grid_configure(
                row=row_number,
                column=5
            )

    def clear_exercise_rows(self):
        for row in self.exercise_rows:
            for widget in row["fields"]:
                widget.destroy()

            row["button"].destroy()

        self.exercise_rows.clear()

    def get_exercise_data(self):
        exercises = []

        for number, row in enumerate(self.exercise_rows, start=1):
            values = [
                field.get().strip()
                for field in row["fields"]
            ]

            if not any(values):
                continue

            if not values[0]:
                messagebox.showwarning(
                    "Ejercicio incompleto",
                    f"Falta el nombre del ejercicio en la fila {number}.",
                    parent=self
                )
                return None

            exercises.append({
                "name": values[0],
                "sets": values[1],
                "reps": values[2],
                "weight": values[3],
                "notes": values[4]
            })

        return exercises

    # ==========================================
    # RUTINAS MAESTRAS
    # ==========================================

    def refresh_templates(self):
        for widget in self.template_list.winfo_children():
            widget.destroy()

        rows = self.db.get_workout_templates()

        if not rows:
            ctk.CTkLabel(
                self.template_list,
                text="Todavía no hay rutinas.\nCreá la primera.",
                text_color=SECONDARY
            ).pack(pady=20)

        for row in rows:
            ctk.CTkButton(
                self.template_list,
                text=row["name"],
                anchor="w",
                fg_color="#30363D",
                hover_color=ORANGE,
                command=lambda r=row: self.select_template(r["id"])
            ).pack(fill="x", padx=4, pady=4)

    def new_template(self):
        self.selected_template_id = None
        self.detail = None

        self.name_entry.delete(0, "end")
        self.description_entry.delete(0, "end")

        self.day_var.set(DAYS[0])
        self.clear_day_fields()

    def select_template(self, template_id):
        self.selected_template_id = template_id

        self.detail = self.db.get_workout_template_detail(
            template_id
        )

        self.name_entry.delete(0, "end")
        self.name_entry.insert(
            0, self.detail["template"]["name"]
        )

        self.description_entry.delete(0, "end")
        self.description_entry.insert(
            0,
            self.detail["template"]["description"] or ""
        )

        self.load_day(self.day_var.get())

    def save_template(self):
        try:
            self.selected_template_id = (
                self.db.save_workout_template(
                    self.selected_template_id,
                    self.name_entry.get(),
                    self.description_entry.get()
                )
            )

            self.refresh_templates()
            self.select_template(self.selected_template_id)

            messagebox.showinfo(
                "Entrenamientos",
                "Rutina guardada correctamente.",
                parent=self
            )

        except Exception as exc:
            messagebox.showerror(
                "No se pudo guardar",
                str(exc),
                parent=self
            )

    def delete_template(self):
        if not self.selected_template_id:
            messagebox.showwarning(
                "Entrenamientos",
                "Seleccioná una rutina primero.",
                parent=self
            )
            return

        if messagebox.askyesno(
            "Eliminar rutina",
            "¿Eliminar definitivamente esta plantilla y todos sus días y ejercicios?",
            parent=self
        ):
            self.db.delete_workout_template(
                self.selected_template_id
            )

            self.new_template()
            self.refresh_templates()

    # ==========================================
    # DÍAS DE LA SEMANA
    # ==========================================

    def clear_day_fields(self):
        self.groups_entry.delete(0, "end")
        self.day_notes_entry.delete(0, "end")

        self.clear_exercise_rows()
        self._create_empty_rows(MINIMUM_ROWS)

    def load_day(self, day_name):
        self.clear_day_fields()

        if not self.selected_template_id:
            return

        detail = self.db.get_workout_template_detail(
            self.selected_template_id
        )

        weekday = DAYS.index(day_name)

        for item in detail["days"]:
            day = item["day"]

            if day["weekday"] == weekday:
                self.groups_entry.insert(
                    0, day["muscle_groups"] or ""
                )

                self.day_notes_entry.insert(
                    0, day["notes"] or ""
                )

                self.clear_exercise_rows()

                for ex in item["exercises"]:
                    values = [
                        ex["name"],
                        ex["sets"],
                        ex["reps"],
                        ex["reference_weight"],
                        ex["notes"]
                    ]

                    self.add_exercise_row(values)

                if len(self.exercise_rows) < MINIMUM_ROWS:
                    self._create_empty_rows(
                        MINIMUM_ROWS - len(self.exercise_rows)
                    )

                break

    def save_day(self):
        if not self.selected_template_id:
            messagebox.showwarning(
                "Entrenamientos",
                "Primero guardá la rutina.",
                parent=self
            )
            return

        exercises = self.get_exercise_data()

        if exercises is None:
            return

        try:
            self.db.save_workout_day(
                self.selected_template_id,
                DAYS.index(self.day_var.get()),
                self.groups_entry.get(),
                self.day_notes_entry.get(),
                exercises
            )

            messagebox.showinfo(
                "Entrenamientos",
                f"{self.day_var.get()} guardado correctamente.",
                parent=self
            )

        except Exception as exc:
            messagebox.showerror(
                "No se pudo guardar el día",
                str(exc),
                parent=self
            )

    def remove_day(self):
        if not self.selected_template_id:
            return

        if messagebox.askyesno(
            "Quitar día",
            f"¿Quitar {self.day_var.get()} de esta rutina?",
            parent=self
        ):
            self.db.delete_workout_day(
                self.selected_template_id,
                DAYS.index(self.day_var.get())
            )

            self.clear_day_fields()

