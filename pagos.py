
import customtkinter as ctk

from tkinter import ttk, messagebox

from datetime import date, timedelta


# ==========================================
# CONFIGURACION VISUAL
# ==========================================

ORANGE = "#FF6600"
BACKGROUND = "#111315"
CARD = "#202429"
TEXT = "#FFFFFF"
SECONDARY = "#A0A5AB"


# ==========================================
# VENTANA DE PAGOS
# ==========================================

class PagosWindow(ctk.CTkToplevel):

    def __init__(self, parent, database):

        super().__init__(parent)

        self.db = database
        self.parent = parent

        self.title("FORJAGYM | Gestión de pagos")

        self.geometry("1200x680")
        self.minsize(950, 550)

        self.configure(fg_color=BACKGROUND)
        self.money_entries = []

        self.create_interface()
        self.load_payments()

        self.transient(parent)


    # ======================================
    # INTERFAZ
    # ======================================

    def create_interface(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)


        ctk.CTkLabel(

            self,
            text="GESTIÓN DE PAGOS",
            font=("Arial", 26, "bold"),
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
            text="Registro de cuotas e historial financiero",
            font=("Arial", 12),
            text_color=SECONDARY

        ).grid(

            row=1,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 20)

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
            lambda event: self.load_payments()
        )


        ctk.CTkButton(

            toolbar,
            text="+ REGISTRAR PAGO",
            fg_color=ORANGE,
            hover_color="#CC5200",
            height=40,
            font=("Arial", 11, "bold"),
            command=self.open_payment_form

        ).grid(row=0, column=1, padx=4)


        ctk.CTkButton(

            toolbar,
            text="ELIMINAR PAGO",
            fg_color="#8C3030",
            hover_color="#A00000",
            height=40,
            font=("Arial", 11, "bold"),
            command=self.delete_selected_payment

        ).grid(row=0, column=2, padx=4)


        ctk.CTkButton(

            toolbar,
            text="ACTUALIZAR",
            fg_color="#343A40",
            hover_color="#454C53",
            height=40,
            command=self.load_payments

        ).grid(row=0, column=3, padx=4)


        # TABLA

        table_frame = ctk.CTkFrame(
            self,
            fg_color=CARD,
            corner_radius=10
        )

        table_frame.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=25,
            pady=20
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
            rowheight=35,
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

            "fecha",
            "socio",
            "dni",
            "plan",
            "duracion",
            "importe",
            "inicio",
            "vencimiento"

        )


        self.tree = ttk.Treeview(

            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"

        )


        headings = {

            "fecha": "FECHA DE PAGO",
            "socio": "SOCIO",
            "dni": "DNI",
            "plan": "PLAN",
            "duracion": "DURACIÓN",
            "importe": "IMPORTE",
            "inicio": "INICIO",
            "vencimiento": "VENCIMIENTO"

        }


        widths = {

            "fecha": 115,
            "socio": 190,
            "dni": 100,
            "plan": 150,
            "duracion": 90,
            "importe": 115,
            "inicio": 105,
            "vencimiento": 115

        }


        for column in columns:

            self.tree.heading(
                column,
                text=headings[column]
            )

            self.tree.column(
                column,
                width=widths[column],
                minwidth=75
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


        # CONTADOR

        self.counter_label = ctk.CTkLabel(

            self,
            text="Pagos registrados: 0",
            text_color=SECONDARY,
            font=("Arial", 11)

        )

        self.counter_label.grid(

            row=4,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 15)

        )


    # ======================================
    # PRIVACIDAD FINANCIERA
    # ======================================

    def refresh_money_visibility(self):
        self.load_payments()
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

    # ======================================
    # CARGAR HISTORIAL
    # ======================================

    def load_payments(self):

        for item in self.tree.get_children():
            self.tree.delete(item)


        search = self.search_entry.get()

        payments = self.db.get_payments(search)


        for payment in payments:

            amount = (
                f"${payment['amount']:,}".replace(",", ".")
                if self.parent.show_money else "••••••"
            )


            self.tree.insert(

                "",
                "end",

                iid=str(payment["id"]),

                values=(

                    payment["payment_date"],

                    f"{payment['first_name']} {payment['last_name']}",

                    payment["dni"],

                    payment["plan_name"],

                    f'{payment["duration_days"]} días',

                    amount,

                    payment["start_date"],

                    payment["end_date"]

                )

            )


        self.counter_label.configure(

            text=f"Pagos registrados: {len(payments)}"

        )


    # ======================================
    # ELIMINAR PAGO SELECCIONADO
    # ======================================

    def delete_selected_payment(self):

        selection = self.tree.selection()


        if not selection:

            messagebox.showwarning(

                "FORJAGYM",

                "Seleccioná un pago para eliminar.",

                parent=self

            )

            return


        payment_id = int(selection[0])


        payments = self.db.get_payments()

        payment = next(

            (

                item for item in payments

                if item["id"] == payment_id

            ),

            None

        )


        if not payment:

            messagebox.showerror(

                "FORJAGYM",

                "No se encontró el pago seleccionado.",

                parent=self

            )

            return


        amount = (
            f"${payment['amount']:,}".replace(",", ".")
            if self.parent.show_money else "••••••"
        )

        full_name = (

            f"{payment['first_name']} "

            f"{payment['last_name']}"

        )


        confirm = messagebox.askyesno(

            "ELIMINAR PAGO",

            f"¿Querés eliminar este movimiento?\n\n"

            f"Socio: {full_name}\n"

            f"DNI: {payment['dni']}\n"

            f"Importe: {amount}\n"

            f"Fecha: {payment['payment_date']}\n\n"

            "El movimiento desaparecerá del historial "

            "y se recalcularán los ingresos del mes.\n\n"

            "Esta operación no se puede deshacer.",

            icon="warning",

            parent=self

        )


        if not confirm:
            return


        try:

            self.db.delete_payment(payment_id)

            self.load_payments()

            self.parent.refresh_dashboard()


            messagebox.showinfo(

                "FORJAGYM",

                "El pago fue eliminado correctamente.",

                parent=self

            )


        except Exception as error:

            messagebox.showerror(

                "Error al eliminar",

                str(error),

                parent=self

            )


    # ======================================
    # FORMULARIO DE PAGO
    # ======================================

    def open_payment_form(self):

        members = self.db.get_members()
        plans = self.db.get_plans()

        if not members:
            messagebox.showwarning(
                "FORJAGYM",
                "No hay socios activos registrados.",
                parent=self
            )
            return

        if not plans:
            messagebox.showwarning(
                "FORJAGYM",
                "No hay planes activos disponibles.",
                parent=self
            )
            return

        form = ctk.CTkToplevel(self)
        form.title("Registrar pago")
        form.geometry("550x790")
        form.resizable(False, False)
        form.configure(fg_color=BACKGROUND)
        form.transient(self)
        form.grab_set()

        ctk.CTkLabel(
            form,
            text="REGISTRAR NUEVO PAGO",
            font=("Arial", 23, "bold"),
            text_color=ORANGE
        ).pack(pady=(22, 5))

        ctk.CTkLabel(
            form,
            text="Completá los datos de la cuota",
            font=("Arial", 12),
            text_color=SECONDARY
        ).pack(pady=(0, 15))

        content = ctk.CTkScrollableFrame(
            form,
            fg_color="transparent"
        )
        content.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=5
        )

        def create_label(text):
            ctk.CTkLabel(
                content,
                text=text,
                text_color=SECONDARY,
                font=("Arial", 11, "bold")
            ).pack(anchor="w", pady=(9, 3))

        # SOCIO
        create_label("SOCIO")

        member_options = {}
        for member in members:
            label = (
                f'{member["dni"]} - '
                f'{member["first_name"]} {member["last_name"]}'
            )
            member_options[label] = member["id"]

        # Buscador predictivo de socios: filtra por DNI, nombre y apellido.
        all_member_labels = list(member_options.keys())
        filtered_member_labels = all_member_labels.copy()

        member_combo = ctk.CTkComboBox(
            content,
            values=filtered_member_labels,
            width=450,
            height=38,
            state="normal"
        )
        member_combo.pack(anchor="w")
        member_combo.set(all_member_labels[0])

        def filter_members(event=None):
            # No interferir con teclas de navegación/selección.
            if event is not None and event.keysym in (
                "Up", "Down", "Left", "Right", "Return", "Escape", "Tab"
            ):
                return

            query = member_combo.get().strip().casefold()
            current_text = member_combo.get()

            if not query:
                matches = all_member_labels.copy()
            else:
                matches = [
                    label for label in all_member_labels
                    if query in label.casefold()
                ]

            filtered_member_labels[:] = matches
            member_combo.configure(values=matches)

            # Mantener lo escrito para permitir seguir buscando.
            member_combo.delete(0, "end")
            member_combo.insert(0, current_text)

        def on_member_selected(choice=None):
            # Al elegir un resultado, el texto completo identifica al socio.
            return

        member_combo.configure(command=on_member_selected)
        member_combo.bind("<KeyRelease>", filter_members)

        # PLAN
        create_label("PLAN")

        plan_options = {}
        for plan in plans:
            label = (
                f'{plan["name"]} - {plan["days_per_week"]} días/semana '
                f'- {plan["duration_days"]} días'
            )
            plan_options[label] = plan

        plan_combo = ctk.CTkComboBox(
            content,
            values=list(plan_options.keys()),
            width=450,
            height=38,
            state="readonly"
        )
        plan_combo.pack(anchor="w")
        plan_combo.set(list(plan_options.keys())[0])

        # IMPORTE
        create_label("IMPORTE ABONADO ($)")

        amount_entry = ctk.CTkEntry(
            content,
            width=450,
            height=38,
            placeholder_text="Ejemplo: 65000",
            show="" if self.parent.show_money else "•"
        )
        amount_entry.pack(anchor="w")
        self.money_entries.append(amount_entry)

        # DURACIÓN CONTRATADA (INFORMATIVA, VIENE DEL PLAN)
        create_label("DURACIÓN DE LA CUOTA")

        duration_label = ctk.CTkLabel(
            content,
            text="",
            width=450,
            anchor="w",
            text_color=TEXT,
            font=("Arial", 12, "bold")
        )
        duration_label.pack(anchor="w", pady=(0, 4))

        # FECHAS
        today = date.today()
        today_string = today.isoformat()

        create_label("FECHA DE PAGO (AAAA-MM-DD)")
        payment_date_entry = ctk.CTkEntry(
            content,
            width=450,
            height=38
        )
        payment_date_entry.pack(anchor="w")
        payment_date_entry.insert(0, today_string)

        create_label("INICIO DE VIGENCIA (AAAA-MM-DD)")
        start_date_entry = ctk.CTkEntry(
            content,
            width=450,
            height=38
        )
        start_date_entry.pack(anchor="w")
        start_date_entry.insert(0, today_string)

        create_label("VENCIMIENTO (AAAA-MM-DD)")
        end_date_entry = ctk.CTkEntry(
            content,
            width=450,
            height=38
        )
        end_date_entry.pack(anchor="w")

        # Al modificar manualmente el vencimiento, no lo pisamos al cambiar plan.
        end_manually_edited = False
        start_manually_edited = False

        def selected_plan():
            return plan_options.get(plan_combo.get())

        def calculate_end_date():
            plan = selected_plan()
            if not plan:
                return

            try:
                start_day = date.fromisoformat(start_date_entry.get().strip())
            except ValueError:
                return

            new_end = start_day + timedelta(days=int(plan["duration_days"]))
            end_date_entry.delete(0, "end")
            end_date_entry.insert(0, new_end.isoformat())

        def update_plan_fields(choice=None):
            nonlocal end_manually_edited

            plan = selected_plan()
            if not plan:
                return

            amount_entry.delete(0, "end")
            amount_entry.insert(0, str(plan["price"]))

            duration_label.configure(
                text=f'{plan["duration_days"]} días'
            )

            if not end_manually_edited:
                calculate_end_date()

        def on_start_changed(event=None):
            nonlocal start_manually_edited
            start_manually_edited = True
            if not end_manually_edited:
                calculate_end_date()

        def on_payment_date_changed(event=None):
            if start_manually_edited:
                return

            try:
                payment_day = date.fromisoformat(
                    payment_date_entry.get().strip()
                )
            except ValueError:
                return

            start_date_entry.delete(0, "end")
            start_date_entry.insert(0, payment_day.isoformat())

            if not end_manually_edited:
                calculate_end_date()

        def on_end_changed(event=None):
            nonlocal end_manually_edited
            end_manually_edited = True

        plan_combo.configure(command=update_plan_fields)
        start_date_entry.bind("<KeyRelease>", on_start_changed)
        end_date_entry.bind("<KeyRelease>", on_end_changed)
        payment_date_entry.bind("<FocusOut>", on_payment_date_changed)

        update_plan_fields()

        ctk.CTkLabel(
            content,
            text=(
                "El vencimiento se calcula automáticamente sumando la "
                "duración del plan a la fecha de inicio. Podés modificar "
                "manualmente las fechas si lo necesitás."
            ),
            text_color=SECONDARY,
            font=("Arial", 10),
            wraplength=440,
            justify="left"
        ).pack(anchor="w", pady=15)

        # GUARDAR
        def save_payment():

            selected_member = member_options.get(member_combo.get().strip())
            plan = selected_plan()

            if not selected_member or not plan:
                messagebox.showwarning(
                    "Validación",
                    "Seleccioná un socio y un plan.",
                    parent=form
                )
                return

            amount_text = (
                amount_entry.get()
                .strip()
                .replace("$", "")
                .replace(".", "")
                .replace(",", "")
                .replace(" ", "")
            )

            if not amount_text.isdigit():
                messagebox.showwarning(
                    "Validación",
                    "Ingresá un importe válido sin decimales.",
                    parent=form
                )
                return

            amount = int(amount_text)

            payment_date = payment_date_entry.get().strip()
            start_date = start_date_entry.get().strip()
            end_date = end_date_entry.get().strip()

            try:
                payment_day = date.fromisoformat(payment_date)
                start_day = date.fromisoformat(start_date)
                end_day = date.fromisoformat(end_date)
            except ValueError:
                messagebox.showwarning(
                    "Fechas incorrectas",
                    "Utilizá el formato AAAA-MM-DD.",
                    parent=form
                )
                return

            if end_day < start_day:
                messagebox.showwarning(
                    "Fechas incorrectas",
                    "El vencimiento no puede ser anterior al inicio.",
                    parent=form
                )
                return

            if payment_day > date.today():
                messagebox.showwarning(
                    "Fecha incorrecta",
                    "La fecha de pago no puede ser futura.",
                    parent=form
                )
                return

            try:
                self.db.register_payment(
                    member_id=selected_member,
                    plan_id=plan["id"],
                    amount=amount,
                    payment_date=payment_date,
                    start_date=start_date,
                    end_date=end_date,
                    duration_days=plan["duration_days"]
                )

                self.load_payments()
                self.parent.refresh_dashboard()
                form.destroy()

                messagebox.showinfo(
                    "FORJAGYM",
                    "¡Pago registrado correctamente!",
                    parent=self
                )

            except Exception as error:
                messagebox.showerror(
                    "Error al registrar el pago",
                    str(error),
                    parent=form
                )

        ctk.CTkButton(
            content,
            text="CONFIRMAR Y REGISTRAR PAGO",
            fg_color=ORANGE,
            hover_color="#CC5200",
            height=45,
            font=("Arial", 13, "bold"),
            command=save_payment
        ).pack(fill="x", pady=(10, 25))

