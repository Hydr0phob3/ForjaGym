import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime


ORANGE = "#FF6600"
BACKGROUND = "#111315"
SIDEBAR = "#191C20"
CARD = "#202429"
TEXT = "#FFFFFF"
SECONDARY = "#A0A5AB"
GREEN = "#20A464"
RED = "#D94343"
YELLOW = "#D99B25"


class AsistenciasWindow(ctk.CTkToplevel):
    """Ventana de consulta del historial de fichajes de FORJAGYM."""

    def __init__(self, parent, db):
        super().__init__(parent)
        self.parent = parent
        self.db = db

        self.title("FORJAGYM | Historial de asistencias")
        self.geometry("1180x720")
        self.minsize(900, 580)
        self.configure(fg_color=BACKGROUND)
        self.transient(parent)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.create_layout()
        self.refresh_history()
        self.focus_force()

    def create_layout(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="HISTORIAL DE ASISTENCIAS",
            font=ctk.CTkFont(size=25, weight="bold"),
            text_color=TEXT
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Registro de ingresos e intentos de acceso",
            font=ctk.CTkFont(size=12),
            text_color=SECONDARY
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        self.summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_frame.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))
        for col in range(4):
            self.summary_frame.grid_columnconfigure(col, weight=1)

        self.summary_values = {}
        summary_items = [
            ("today", "FICHAJES DE HOY"),
            ("total", "INTENTOS REGISTRADOS"),
            ("allowed", "ACCESOS PERMITIDOS"),
            ("rejected", "ACCESOS RECHAZADOS"),
        ]
        for col, (key, label) in enumerate(summary_items):
            card = ctk.CTkFrame(self.summary_frame, fg_color=CARD, corner_radius=10, height=85)
            card.grid(row=0, column=col, sticky="ew", padx=6)
            card.grid_propagate(False)
            ctk.CTkLabel(
                card, text=label, text_color=SECONDARY,
                font=ctk.CTkFont(size=10, weight="bold")
            ).pack(anchor="w", padx=13, pady=(13, 2))
            value = ctk.CTkLabel(
                card, text="0", text_color=ORANGE,
                font=ctk.CTkFont(size=23, weight="bold")
            )
            value.pack(anchor="w", padx=13)
            self.summary_values[key] = value

        filters = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        filters.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        filters.grid_columnconfigure(0, weight=2)
        filters.grid_columnconfigure(1, weight=1)
        filters.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(filters, text="Buscar socio / DNI", text_color=SECONDARY).grid(
            row=0, column=0, sticky="w", padx=(14, 6), pady=(10, 2)
        )
        ctk.CTkLabel(filters, text="Desde (AAAA-MM-DD)", text_color=SECONDARY).grid(
            row=0, column=1, sticky="w", padx=6, pady=(10, 2)
        )
        ctk.CTkLabel(filters, text="Hasta (AAAA-MM-DD)", text_color=SECONDARY).grid(
            row=0, column=2, sticky="w", padx=6, pady=(10, 2)
        )

        self.search_var = tk.StringVar()
        self.date_from_var = tk.StringVar()
        self.date_to_var = tk.StringVar()
        self.result_var = tk.StringVar(value="Todos")

        self.search_entry = ctk.CTkEntry(
            filters, textvariable=self.search_var, placeholder_text="Nombre, apellido o DNI", height=34
        )
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=(14, 6), pady=(0, 10))
        self.date_from_entry = ctk.CTkEntry(
            filters, textvariable=self.date_from_var, placeholder_text="Ej. 2026-11-01", height=34
        )
        self.date_from_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=(0, 10))
        self.date_to_entry = ctk.CTkEntry(
            filters, textvariable=self.date_to_var, placeholder_text="Ej. 2026-11-30", height=34
        )
        self.date_to_entry.grid(row=1, column=2, sticky="ew", padx=6, pady=(0, 10))

        ctk.CTkLabel(filters, text="Resultado", text_color=SECONDARY).grid(
            row=2, column=0, sticky="w", padx=14, pady=(0, 2)
        )
        self.result_menu = ctk.CTkOptionMenu(
            filters,
            variable=self.result_var,
            values=["Todos", "allowed", "expired", "limit_reached", "inactive", "no_payment", "pending", "not_found"],
            height=32,
            fg_color="#343A40",
            button_color=ORANGE,
            button_hover_color="#D95700",
            dropdown_fg_color=CARD
        )
        self.result_menu.grid(row=3, column=0, sticky="w", padx=14, pady=(0, 12))

        buttons = ctk.CTkFrame(filters, fg_color="transparent")
        buttons.grid(row=3, column=1, columnspan=2, sticky="e", padx=12, pady=(0, 12))
        ctk.CTkButton(
            buttons, text="APLICAR FILTROS", width=145, height=34,
            fg_color=ORANGE, hover_color="#D95700", command=self.refresh_history
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            buttons, text="LIMPIAR", width=95, height=34,
            fg_color="#343A40", hover_color="#454C54", command=self.clear_filters
        ).pack(side="left")

        table_frame = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        table_frame.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 22))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure(
            "Forja.Treeview",
            background="#202429",
            foreground="#FFFFFF",
            fieldbackground="#202429",
            rowheight=31,
            borderwidth=0,
            font=("Arial", 10)
        )
        style.configure(
            "Forja.Treeview.Heading",
            background="#30363D",
            foreground="#FFFFFF",
            relief="flat",
            font=("Arial", 10, "bold")
        )
        style.map(
            "Forja.Treeview",
            background=[("selected", "#75401F")],
            foreground=[("selected", "#FFFFFF")]
        )

        columns = ("date", "time", "name", "dni", "result", "detail")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", style="Forja.Treeview"
        )
        self.tree.heading("date", text="FECHA")
        self.tree.heading("time", text="HORA")
        self.tree.heading("name", text="SOCIO")
        self.tree.heading("dni", text="DNI")
        self.tree.heading("result", text="RESULTADO")
        self.tree.heading("detail", text="DETALLE")
        self.tree.column("date", width=105, anchor="center", stretch=False)
        self.tree.column("time", width=85, anchor="center", stretch=False)
        self.tree.column("name", width=220, anchor="w")
        self.tree.column("dni", width=110, anchor="center", stretch=False)
        self.tree.column("result", width=150, anchor="center", stretch=False)
        self.tree.column("detail", width=340, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.tag_configure("allowed", foreground=GREEN)
        self.tree.tag_configure("rejected", foreground="#F07878")
        self.tree.bind("<Double-1>", self.show_selected_detail)

        self.footer_label = ctk.CTkLabel(
            self, text="", text_color=SECONDARY, font=ctk.CTkFont(size=11)
        )
        self.footer_label.grid(row=4, column=0, sticky="e", padx=28, pady=(0, 10))

    def clear_filters(self):
        self.search_var.set("")
        self.date_from_var.set("")
        self.date_to_var.set("")
        self.result_var.set("Todos")
        self.refresh_history()

    def refresh_history(self):
        date_from = self.date_from_var.get().strip()
        date_to = self.date_to_var.get().strip()
        try:
            if date_from:
                datetime.strptime(date_from, "%Y-%m-%d")
            if date_to:
                datetime.strptime(date_to, "%Y-%m-%d")
            if date_from and date_to and date_from > date_to:
                raise ValueError("La fecha 'Desde' no puede ser posterior a 'Hasta'.")
        except ValueError as error:
            messagebox.showwarning("Fechas inválidas", str(error), parent=self)
            return

        try:
            rows = self.db.get_attendance_history(
                search=self.search_var.get(),
                date_from=date_from,
                date_to=date_to,
                result_filter=self.result_var.get()
            )
            summary = self.db.get_attendance_history_summary()
        except Exception as error:
            messagebox.showerror(
                "Error al consultar asistencias",
                f"No se pudo cargar el historial.\n\n{error}",
                parent=self
            )
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        labels = {
            "allowed": "PERMITIDO",
            "expired": "CUOTA VENCIDA",
            "limit_reached": "CUPO AGOTADO",
            "inactive": "SOCIO INACTIVO",
            "no_payment": "SIN CUOTA",
            "pending": "NO VIGENTE",
            "not_found": "NO ENCONTRADO",
        }
        for row in rows:
            try:
                stamp = datetime.fromisoformat(row["checked_at"])
                time_text = stamp.strftime("%H:%M:%S")
            except (TypeError, ValueError):
                time_text = str(row["checked_at"])[11:19]
            date_text = row["attendance_date"]
            try:
                date_text = datetime.strptime(date_text, "%Y-%m-%d").strftime("%d/%m/%Y")
            except (TypeError, ValueError):
                pass

            result = row["result"]
            detail = row["message"] or ""
            if result == "allowed" and row.get("used") is not None and row.get("limit_count") is not None:
                detail = f"{detail} · {row['used']}/{row['limit_count']} asistencias semanales"
            name = row["member_name"] or ("—" if result != "not_found" else "No registrado")
            self.tree.insert(
                "", "end",
                values=(date_text, time_text, name, row["dni"], labels.get(result, result), detail),
                tags=("allowed" if result == "allowed" else "rejected",)
            )

        self.summary_values["today"].configure(text=str(summary["today_attempts"]))
        self.summary_values["total"].configure(text=str(summary["total_attempts"]))
        self.summary_values["allowed"].configure(text=str(summary["allowed"]))
        self.summary_values["rejected"].configure(text=str(summary["rejected"]))
        self.footer_label.configure(text=f"Se muestran {len(rows)} registros · Máximo de consulta: 2.000")

    def show_selected_detail(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        messagebox.showinfo(
            "Detalle del fichaje",
            f"Fecha: {values[0]}\nHora: {values[1]}\nSocio: {values[2]}\n"
            f"DNI: {values[3]}\nResultado: {values[4]}\nDetalle: {values[5]}",
            parent=self
        )
