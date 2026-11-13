
import customtkinter as ctk

from tkinter import ttk, messagebox

import sqlite3


# ==========================================
# CONFIGURACION VISUAL
# ==========================================

ORANGE = "#FF6600"
BACKGROUND = "#111315"
CARD = "#202429"
TEXT = "#FFFFFF"
SECONDARY = "#A0A5AB"


# ==========================================
# VENTANA DE SOCIOS
# ==========================================

class SociosWindow(ctk.CTkToplevel):

    def __init__(self, parent, database):

        super().__init__(parent)

        self.db = database
        self.parent = parent

        self.title("FORJAGYM | Gestión de socios")
        self.geometry("1150x680")
        self.minsize(900, 550)

        self.configure(fg_color=BACKGROUND)

        self.create_interface()
        self.load_members()

        self.transient(parent)


    # ======================================
    # INTERFAZ
    # ======================================

    def create_interface(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)


        ctk.CTkLabel(

            self,
            text="GESTIÓN DE SOCIOS",
            font=("Arial", 25, "bold"),
            text_color=TEXT

        ).grid(

            row=0,
            column=0,
            sticky="w",
            padx=25,
            pady=(25, 5)

        )


        ctk.CTkLabel(

            self,
            text="Administración y control de membresías",
            font=("Arial", 12),
            text_color=SECONDARY

        ).grid(

            row=1,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 15)

        )


        # BARRA DE HERRAMIENTAS

        toolbar = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        toolbar.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=25,
            pady=5
        )

        toolbar.grid_columnconfigure(0, weight=1)


        self.search_entry = ctk.CTkEntry(

            toolbar,
            placeholder_text="Buscar por DNI, nombre o apellido...",
            height=40

        )

        self.search_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 10)
        )

        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.load_members()
        )


        ctk.CTkButton(

            toolbar,
            text="+ NUEVO SOCIO",
            fg_color=ORANGE,
            hover_color="#CC5200",
            height=40,
            command=self.open_new_member

        ).grid(row=0, column=1, padx=4)


        ctk.CTkButton(

            toolbar,
            text="EDITAR",
            fg_color="#343A40",
            hover_color="#454C53",
            height=40,
            command=self.edit_selected

        ).grid(row=0, column=2, padx=4)


        ctk.CTkButton(

            toolbar,
            text="ARCHIVAR",
            fg_color="#8C3030",
            hover_color="#A63B3B",
            height=40,
            command=self.archive_selected

        ).grid(row=0, column=3, padx=4)


        ctk.CTkButton(

            toolbar,
            text="ELIMINAR DEFINITIVO",
            fg_color="#641E1E",
            hover_color="#A00000",
            height=40,
            font=("Arial", 11, "bold"),
            command=self.delete_selected

        ).grid(row=0, column=4, padx=4)


        # FILTRO DE ARCHIVADOS

        self.archived_checkbox = ctk.CTkCheckBox(

            self,
            text="Incluir socios archivados",
            text_color=SECONDARY,
            command=self.load_members,
            fg_color=ORANGE,
            hover_color="#CC5200"

        )

        self.archived_checkbox.grid(

            row=3,
            column=0,
            sticky="w",
            padx=30,
            pady=(8, 0)

        )


        # TABLA

        table_frame = ctk.CTkFrame(
            self,
            fg_color=CARD,
            corner_radius=10
        )

        table_frame.grid(
            row=4,
            column=0,
            sticky="nsew",
            padx=25,
            pady=15
        )

        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)


        style = ttk.Style()
        style.theme_use("clam")

        style.configure(

            "Treeview",
            background="#202429",
            foreground="white",
            fieldbackground="#202429",
            rowheight=34,
            font=("Arial", 10)

        )

        style.configure(

            "Treeview.Heading",
            background="#30363D",
            foreground="white",
            font=("Arial", 10, "bold"),
            padding=8

        )

        style.map(

            "Treeview",
            background=[("selected", "#A94710")],
            foreground=[("selected", "white")]

        )


        columns = (

            "dni",
            "nombre",
            "telefono",
            "plan",
            "vencimiento",
            "estado",
            "situacion"

        )


        self.tree = ttk.Treeview(

            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"

        )


        headings = {

            "dni": "DNI",
            "nombre": "NOMBRE Y APELLIDO",
            "telefono": "TELÉFONO",
            "plan": "PLAN",
            "vencimiento": "VENCIMIENTO",
            "estado": "ESTADO",
            "situacion": "REGISTRO"

        }


        widths = {

            "dni": 95,
            "nombre": 180,
            "telefono": 110,
            "plan": 145,
            "vencimiento": 105,
            "estado": 95,
            "situacion": 90

        }


        for column in columns:

            self.tree.heading(
                column,
                text=headings[column]
            )

            self.tree.column(
                column,
                width=widths[column],
                minwidth=65
            )


        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=10,
            pady=10
        )


        scrollbar = ttk.Scrollbar(

            table_frame,
            orient="vertical",
            command=self.tree.yview

        )

        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )


        self.tree.bind(
            "<Double-1>",
            lambda event: self.edit_selected()
        )


        self.counter_label = ctk.CTkLabel(

            self,
            text="Socios encontrados: 0",
            text_color=SECONDARY,
            font=("Arial", 11)

        )

        self.counter_label.grid(

            row=5,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 15)

        )


    # ======================================
    # CARGAR SOCIOS
    # ======================================

    def load_members(self):

        for item in self.tree.get_children():
            self.tree.delete(item)


        search = self.search_entry.get()

        include_archived = bool(
            self.archived_checkbox.get()
        )


        members = self.db.get_members(
            search,
            include_archived=include_archived
        )


        for member in members:

            situation = (
                "Activo"
                if member["active"] == 1
                else "Archivado"
            )

            self.tree.insert(

                "",
                "end",

                iid=str(member["id"]),

                values=(

                    member["dni"],

                    f"{member['first_name']} {member['last_name']}",

                    member["phone"] or "-",

                    member["plan_name"] or "-",

                    member["end_date"] or "-",

                    member["status"],

                    situation

                )

            )


        self.counter_label.configure(

            text=f"Socios encontrados: {len(members)}"

        )


    # ======================================
    # FORMULARIO DE SOCIO
    # ======================================

    def open_form(self, member=None):

        editing = member is not None

        form = ctk.CTkToplevel(self)

        form.title(
            "Editar socio" if editing else "Nuevo socio"
        )

        form.geometry("440x550")
        form.resizable(False, False)

        form.configure(fg_color=BACKGROUND)
        form.transient(self)
        form.grab_set()


        ctk.CTkLabel(

            form,
            text="EDITAR SOCIO" if editing else "REGISTRAR SOCIO",
            font=("Arial", 22, "bold"),
            text_color=ORANGE

        ).pack(pady=(25, 20))


        fields = [

            ("Nombre", "first_name"),
            ("Apellido", "last_name"),
            ("DNI", "dni"),
            ("Teléfono", "phone"),
            ("Contacto de emergencia", "emergency_contact")

        ]


        entries = {}


        for label, key in fields:

            ctk.CTkLabel(
                form,
                text=label,
                text_color=SECONDARY
            ).pack(anchor="w", padx=40)


            entry = ctk.CTkEntry(
                form,
                width=350,
                height=38
            )

            entry.pack(pady=(4, 12))


            if editing:

                entry.insert(
                    0,
                    member.get(key) or ""
                )


            entries[key] = entry


        def save():

            values = {

                key: entry.get().strip()

                for key, entry in entries.items()

            }


            if not values["first_name"]:

                messagebox.showwarning(
                    "Validación",
                    "Ingresá el nombre.",
                    parent=form
                )

                return


            if not values["last_name"]:

                messagebox.showwarning(
                    "Validación",
                    "Ingresá el apellido.",
                    parent=form
                )

                return


            dni = values["dni"]


            if not dni.isdigit() or not 7 <= len(dni) <= 10:

                messagebox.showwarning(
                    "Validación",
                    "El DNI debe contener entre 7 y 10 números.",
                    parent=form
                )

                return


            try:

                if editing:

                    self.db.update_member(
                        member["id"],
                        **values
                    )

                else:

                    self.db.add_member(
                        **values
                    )


                self.load_members()
                self.parent.refresh_dashboard()

                form.destroy()


                messagebox.showinfo(
                    "FORJAGYM",
                    "Socio guardado correctamente.",
                    parent=self
                )


            except sqlite3.IntegrityError:

                messagebox.showerror(
                    "DNI duplicado",
                    "Ya existe un socio con ese DNI.",
                    parent=form
                )


            except sqlite3.Error as error:

                messagebox.showerror(
                    "Error",
                    str(error),
                    parent=form
                )


        ctk.CTkButton(

            form,
            text="GUARDAR SOCIO",
            fg_color=ORANGE,
            hover_color="#CC5200",
            height=42,
            command=save

        ).pack(
            fill="x",
            padx=40,
            pady=15
        )


    # ======================================
    # NUEVO SOCIO
    # ======================================

    def open_new_member(self):

        self.open_form()


    # ======================================
    # EDITAR SOCIO
    # ======================================

    def edit_selected(self):

        selection = self.tree.selection()

        if not selection:

            messagebox.showwarning(
                "FORJAGYM",
                "Seleccioná un socio para editar.",
                parent=self
            )

            return


        member_id = int(selection[0])

        member = self.db.get_member_by_id(member_id)


        if member:

            self.open_form(member)

        else:

            messagebox.showwarning(
                "FORJAGYM",
                "Solo se pueden editar socios activos.",
                parent=self
            )


    # ======================================
    # ARCHIVAR SOCIO
    # ======================================

    def archive_selected(self):

        selection = self.tree.selection()

        if not selection:

            messagebox.showwarning(
                "FORJAGYM",
                "Seleccioná un socio.",
                parent=self
            )

            return


        member_id = int(selection[0])

        member = self.db.get_member_by_id(member_id)


        if not member:

            messagebox.showwarning(
                "FORJAGYM",
                "El socio ya está archivado.",
                parent=self
            )

            return


        confirm = messagebox.askyesno(

            "Confirmar archivo",

            "¿Querés archivar este socio?\n\n"

            "Se conservarán sus pagos y asistencias.",

            parent=self

        )


        if confirm:

            self.db.archive_member(member_id)

            self.load_members()
            self.parent.refresh_dashboard()

            messagebox.showinfo(
                "FORJAGYM",
                "Socio archivado correctamente.",
                parent=self
            )


    # ======================================
    # ELIMINAR DEFINITIVAMENTE
    # ======================================

    def delete_selected(self):

        selection = self.tree.selection()

        if not selection:

            messagebox.showwarning(
                "FORJAGYM",
                "Seleccioná un socio para eliminar.",
                parent=self
            )

            return


        member_id = int(selection[0])

        member = self.db.get_member_by_id(member_id)

        if not member:

            member = next(

                (
                    item for item in self.db.get_members(
                        include_archived=True
                    )

                    if item["id"] == member_id

                ),

                None

            )


        if not member:

            messagebox.showerror(
                "FORJAGYM",
                "No se encontró el socio seleccionado.",
                parent=self
            )

            return


        full_name = (

            f"{member['first_name']} "

            f"{member['last_name']}"

        )


        confirm = messagebox.askyesno(

            "ELIMINACIÓN DEFINITIVA",

            f"¿Estás seguro de eliminar definitivamente a:\n\n"

            f"{full_name}\n"

            f"DNI: {member['dni']}\n\n"

            "SE ELIMINARÁN:\n"

            "• El registro del socio.\n"

            "• Todos sus pagos.\n"

            "• Todas sus asistencias.\n\n"

            "Esta operación NO SE PUEDE DESHACER.\n\n"

            "¿Deseás continuar?",

            icon="warning",

            parent=self

        )


        if not confirm:
            return


        try:

            self.db.delete_member_permanently(member_id)

            self.load_members()
            self.parent.refresh_dashboard()

            messagebox.showinfo(

                "FORJAGYM",

                "El socio y todos sus registros "

                "fueron eliminados definitivamente.",

                parent=self

            )


        except Exception as error:

            messagebox.showerror(
                "Error al eliminar",
                str(error),
                parent=self
            )

import customtkinter as ctk

from tkinter import ttk, messagebox

import sqlite3


# ==========================================
# CONFIGURACION VISUAL
# ==========================================

ORANGE = "#FF6600"
BACKGROUND = "#111315"
CARD = "#202429"
TEXT = "#FFFFFF"
SECONDARY = "#A0A5AB"


# ==========================================
# VENTANA DE SOCIOS
# ==========================================

class SociosWindow(ctk.CTkToplevel):

    def __init__(self, parent, database):

        super().__init__(parent)

        self.db = database
        self.parent = parent

        self.title("FORJAGYM | Gestión de socios")
        self.geometry("1150x680")
        self.minsize(900, 550)

        self.configure(fg_color=BACKGROUND)

        self.create_interface()
        self.load_members()

        self.transient(parent)


    # ======================================
    # INTERFAZ
    # ======================================

    def create_interface(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)


        ctk.CTkLabel(

            self,
            text="GESTIÓN DE SOCIOS",
            font=("Arial", 25, "bold"),
            text_color=TEXT

        ).grid(

            row=0,
            column=0,
            sticky="w",
            padx=25,
            pady=(25, 5)

        )


        ctk.CTkLabel(

            self,
            text="Administración y control de membresías",
            font=("Arial", 12),
            text_color=SECONDARY

        ).grid(

            row=1,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 15)

        )


        # BARRA DE HERRAMIENTAS

        toolbar = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        toolbar.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=25,
            pady=5
        )

        toolbar.grid_columnconfigure(0, weight=1)


        self.search_entry = ctk.CTkEntry(

            toolbar,
            placeholder_text="Buscar por DNI, nombre o apellido...",
            height=40

        )

        self.search_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 10)
        )

        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.load_members()
        )


        ctk.CTkButton(

            toolbar,
            text="+ NUEVO SOCIO",
            fg_color=ORANGE,
            hover_color="#CC5200",
            height=40,
            command=self.open_new_member

        ).grid(row=0, column=1, padx=4)


        ctk.CTkButton(

            toolbar,
            text="EDITAR",
            fg_color="#343A40",
            hover_color="#454C53",
            height=40,
            command=self.edit_selected

        ).grid(row=0, column=2, padx=4)


        ctk.CTkButton(

            toolbar,
            text="ARCHIVAR",
            fg_color="#8C3030",
            hover_color="#A63B3B",
            height=40,
            command=self.archive_selected

        ).grid(row=0, column=3, padx=4)


        ctk.CTkButton(

            toolbar,
            text="ELIMINAR DEFINITIVO",
            fg_color="#641E1E",
            hover_color="#A00000",
            height=40,
            font=("Arial", 11, "bold"),
            command=self.delete_selected

        ).grid(row=0, column=4, padx=4)


        # FILTRO DE ARCHIVADOS

        self.archived_checkbox = ctk.CTkCheckBox(

            self,
            text="Incluir socios archivados",
            text_color=SECONDARY,
            command=self.load_members,
            fg_color=ORANGE,
            hover_color="#CC5200"

        )

        self.archived_checkbox.grid(

            row=3,
            column=0,
            sticky="w",
            padx=30,
            pady=(8, 0)

        )


        # TABLA

        table_frame = ctk.CTkFrame(
            self,
            fg_color=CARD,
            corner_radius=10
        )

        table_frame.grid(
            row=4,
            column=0,
            sticky="nsew",
            padx=25,
            pady=15
        )

        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)


        style = ttk.Style()
        style.theme_use("clam")

        style.configure(

            "Treeview",
            background="#202429",
            foreground="white",
            fieldbackground="#202429",
            rowheight=34,
            font=("Arial", 10)

        )

        style.configure(

            "Treeview.Heading",
            background="#30363D",
            foreground="white",
            font=("Arial", 10, "bold"),
            padding=8

        )

        style.map(

            "Treeview",
            background=[("selected", "#A94710")],
            foreground=[("selected", "white")]

        )


        columns = (

            "dni",
            "nombre",
            "telefono",
            "plan",
            "vencimiento",
            "estado",
            "situacion"

        )


        self.tree = ttk.Treeview(

            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"

        )


        headings = {

            "dni": "DNI",
            "nombre": "NOMBRE Y APELLIDO",
            "telefono": "TELÉFONO",
            "plan": "PLAN",
            "vencimiento": "VENCIMIENTO",
            "estado": "ESTADO",
            "situacion": "REGISTRO"

        }


        widths = {

            "dni": 95,
            "nombre": 180,
            "telefono": 110,
            "plan": 145,
            "vencimiento": 105,
            "estado": 95,
            "situacion": 90

        }


        for column in columns:

            self.tree.heading(
                column,
                text=headings[column]
            )

            self.tree.column(
                column,
                width=widths[column],
                minwidth=65
            )


        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=10,
            pady=10
        )


        scrollbar = ttk.Scrollbar(

            table_frame,
            orient="vertical",
            command=self.tree.yview

        )

        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )


        self.tree.bind(
            "<Double-1>",
            lambda event: self.edit_selected()
        )


        self.counter_label = ctk.CTkLabel(

            self,
            text="Socios encontrados: 0",
            text_color=SECONDARY,
            font=("Arial", 11)

        )

        self.counter_label.grid(

            row=5,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 15)

        )


    # ======================================
    # CARGAR SOCIOS
    # ======================================

    def load_members(self):

        for item in self.tree.get_children():
            self.tree.delete(item)


        search = self.search_entry.get()

        include_archived = bool(
            self.archived_checkbox.get()
        )


        members = self.db.get_members(
            search,
            include_archived=include_archived
        )


        for member in members:

            situation = (
                "Activo"
                if member["active"] == 1
                else "Archivado"
            )

            self.tree.insert(

                "",
                "end",

                iid=str(member["id"]),

                values=(

                    member["dni"],

                    f"{member['first_name']} {member['last_name']}",

                    member["phone"] or "-",

                    member["plan_name"] or "-",

                    member["end_date"] or "-",

                    member["status"],

                    situation

                )

            )


        self.counter_label.configure(

            text=f"Socios encontrados: {len(members)}"

        )


    # ======================================
    # FORMULARIO DE SOCIO
    # ======================================

    def open_form(self, member=None):

        editing = member is not None

        form = ctk.CTkToplevel(self)

        form.title(
            "Editar socio" if editing else "Nuevo socio"
        )

        form.geometry("440x550")
        form.resizable(False, False)

        form.configure(fg_color=BACKGROUND)
        form.transient(self)
        form.grab_set()


        ctk.CTkLabel(

            form,
            text="EDITAR SOCIO" if editing else "REGISTRAR SOCIO",
            font=("Arial", 22, "bold"),
            text_color=ORANGE

        ).pack(pady=(25, 20))


        fields = [

            ("Nombre", "first_name"),
            ("Apellido", "last_name"),
            ("DNI", "dni"),
            ("Teléfono", "phone"),
            ("Contacto de emergencia", "emergency_contact")

        ]


        entries = {}


        for label, key in fields:

            ctk.CTkLabel(
                form,
                text=label,
                text_color=SECONDARY
            ).pack(anchor="w", padx=40)


            entry = ctk.CTkEntry(
                form,
                width=350,
                height=38
            )

            entry.pack(pady=(4, 12))


            if editing:

                entry.insert(
                    0,
                    member.get(key) or ""
                )


            entries[key] = entry


        def save():

            values = {

                key: entry.get().strip()

                for key, entry in entries.items()

            }


            if not values["first_name"]:

                messagebox.showwarning(
                    "Validación",
                    "Ingresá el nombre.",
                    parent=form
                )

                return


            if not values["last_name"]:

                messagebox.showwarning(
                    "Validación",
                    "Ingresá el apellido.",
                    parent=form
                )

                return


            dni = values["dni"]


            if not dni.isdigit() or not 7 <= len(dni) <= 10:

                messagebox.showwarning(
                    "Validación",
                    "El DNI debe contener entre 7 y 10 números.",
                    parent=form
                )

                return


            try:

                if editing:

                    self.db.update_member(
                        member["id"],
                        **values
                    )

                else:

                    self.db.add_member(
                        **values
                    )


                self.load_members()
                self.parent.refresh_dashboard()

                form.destroy()


                messagebox.showinfo(
                    "FORJAGYM",
                    "Socio guardado correctamente.",
                    parent=self
                )


            except sqlite3.IntegrityError:

                messagebox.showerror(
                    "DNI duplicado",
                    "Ya existe un socio con ese DNI.",
                    parent=form
                )


            except sqlite3.Error as error:

                messagebox.showerror(
                    "Error",
                    str(error),
                    parent=form
                )


        ctk.CTkButton(

            form,
            text="GUARDAR SOCIO",
            fg_color=ORANGE,
            hover_color="#CC5200",
            height=42,
            command=save

        ).pack(
            fill="x",
            padx=40,
            pady=15
        )


    # ======================================
    # NUEVO SOCIO
    # ======================================

    def open_new_member(self):

        self.open_form()


    # ======================================
    # EDITAR SOCIO
    # ======================================

    def edit_selected(self):

        selection = self.tree.selection()

        if not selection:

            messagebox.showwarning(
                "FORJAGYM",
                "Seleccioná un socio para editar.",
                parent=self
            )

            return


        member_id = int(selection[0])

        member = self.db.get_member_by_id(member_id)


        if member:

            self.open_form(member)

        else:

            messagebox.showwarning(
                "FORJAGYM",
                "Solo se pueden editar socios activos.",
                parent=self
            )


    # ======================================
    # ARCHIVAR SOCIO
    # ======================================

    def archive_selected(self):

        selection = self.tree.selection()

        if not selection:

            messagebox.showwarning(
                "FORJAGYM",
                "Seleccioná un socio.",
                parent=self
            )

            return


        member_id = int(selection[0])

        member = self.db.get_member_by_id(member_id)


        if not member:

            messagebox.showwarning(
                "FORJAGYM",
                "El socio ya está archivado.",
                parent=self
            )

            return


        confirm = messagebox.askyesno(

            "Confirmar archivo",

            "¿Querés archivar este socio?\n\n"

            "Se conservarán sus pagos y asistencias.",

            parent=self

        )


        if confirm:

            self.db.archive_member(member_id)

            self.load_members()
            self.parent.refresh_dashboard()

            messagebox.showinfo(
                "FORJAGYM",
                "Socio archivado correctamente.",
                parent=self
            )


    # ======================================
    # ELIMINAR DEFINITIVAMENTE
    # ======================================

    def delete_selected(self):

        selection = self.tree.selection()

        if not selection:

            messagebox.showwarning(
                "FORJAGYM",
                "Seleccioná un socio para eliminar.",
                parent=self
            )

            return


        member_id = int(selection[0])

        member = self.db.get_member_by_id(member_id)

        if not member:

            member = next(

                (
                    item for item in self.db.get_members(
                        include_archived=True
                    )

                    if item["id"] == member_id

                ),

                None

            )


        if not member:

            messagebox.showerror(
                "FORJAGYM",
                "No se encontró el socio seleccionado.",
                parent=self
            )

            return


        full_name = (

            f"{member['first_name']} "

            f"{member['last_name']}"

        )


        confirm = messagebox.askyesno(

            "ELIMINACIÓN DEFINITIVA",

            f"¿Estás seguro de eliminar definitivamente a:\n\n"

            f"{full_name}\n"

            f"DNI: {member['dni']}\n\n"

            "SE ELIMINARÁN:\n"

            "• El registro del socio.\n"

            "• Todos sus pagos.\n"

            "• Todas sus asistencias.\n\n"

            "Esta operación NO SE PUEDE DESHACER.\n\n"

            "¿Deseás continuar?",

            icon="warning",

            parent=self

        )


        if not confirm:
            return


        try:

            self.db.delete_member_permanently(member_id)

            self.load_members()
            self.parent.refresh_dashboard()

            messagebox.showinfo(

                "FORJAGYM",

                "El socio y todos sus registros "

                "fueron eliminados definitivamente.",

                parent=self

            )


        except Exception as error:

            messagebox.showerror(
                "Error al eliminar",
                str(error),
                parent=self
            )
