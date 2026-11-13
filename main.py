
import customtkinter as ctk
from pathlib import Path
import sys
from PIL import Image

from tkinter import messagebox

from database import Database

from socios import SociosWindow

from pagos import PagosWindow

from planes import PlanesWindow

from asistencias import AsistenciasWindow
from estadisticas import EstadisticasWindow
from entrenamientos import EntrenamientosWindow
from rutinas_socios import RutinasSociosWindow


# ==========================================
# CONFIGURACION VISUAL
# ==========================================

ctk.set_appearance_mode("dark")

ctk.set_default_color_theme("dark-blue")


ORANGE = "#FF6600"

BACKGROUND = "#111315"

SIDEBAR = "#191C20"

CARD = "#202429"

TEXT = "#FFFFFF"

SECONDARY = "#A0A5AB"
IRON = "#343A40"
FIRE = "#FF6600"


def resource_path(relative_path):
    """Resuelve recursos tanto en Python como dentro de un bundle PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative_path



# ==========================================
# APLICACION PRINCIPAL
# ==========================================

class ForjaGymApp(ctk.CTk):

    def __init__(self):

        super().__init__()

        self.db = Database()

        self.title("FORJAGYM | Administración")

        self.geometry("1200x750")

        self.minsize(1000, 650)

        self.configure(fg_color=BACKGROUND)

        self.socios_window = None

        self.pagos_window = None

        self.planes_window = None

        self.asistencias_window = None
        self.estadisticas_window = None
        self.entrenamientos_window = None
        self.rutinas_socios_window = None

        # PRIVACIDAD FINANCIERA

        self.show_money = True

        self.monthly_income = 0

        self.create_layout()

        # Atajo global y silencioso de privacidad financiera.
        self.bind_all("<F3>", self._on_f3_toggle_money, add="+")

        self.refresh_dashboard()


    # ======================================
    # ESTRUCTURA PRINCIPAL
    # ======================================

    def create_layout(self):

        self.grid_columnconfigure(1, weight=1)

        self.grid_rowconfigure(0, weight=1)


        # MENU LATERAL

        self.sidebar = ctk.CTkFrame(

            self,
            width=230,
            corner_radius=0,
            fg_color=SIDEBAR

        )

        self.sidebar.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        self.sidebar.grid_propagate(False)


        # IDENTIDAD OLD SCHOOL + LOGO OFICIAL
        logo_path = resource_path("assets/logo_forjagym.png")
        self.logo_image = ctk.CTkImage(
            light_image=Image.open(logo_path),
            dark_image=Image.open(logo_path),
            size=(158, 158)
        )
        ctk.CTkLabel(
            self.sidebar,
            text="",
            image=self.logo_image
        ).pack(pady=(22, 8))

        ctk.CTkLabel(
            self.sidebar,
            text="GESTIÓN INTEGRAL PARA GIMNASIOS",
            font=("Segoe UI", 8, "bold"),
            text_color=ORANGE
        ).pack(pady=(0, 22))

        # OPCIONES DEL MENU

        menu_items = [

            ("⌂", "Panel principal"),
            ("♟", "Socios"),
            ("$", "Pagos"),
            ("▤", "Planes"),
            ("🏋", "Entrenamientos"),
            ("📋", "Rutinas de socios"),
            ("▣", "Asistencias"),
            ("▥", "Estadísticas"),

        ]


        for icon, name in menu_items:

            ctk.CTkButton(

                self.sidebar,
                text=f"{icon}    {name}",
                height=45,
                anchor="w",
                fg_color="transparent",
                hover_color="#30343A",
                text_color=TEXT,
                font=("Arial", 13, "bold"),
                command=lambda n=name: self.show_section(n)

            ).pack(
                fill="x",
                padx=15,
                pady=4
            )


        # PIE

        ctk.CTkLabel(

            self.sidebar,
            text="SISTEMA LOCAL OFFLINE",
            font=("Arial", 10, "bold"),
            text_color=SECONDARY

        ).pack(
            side="bottom",
            pady=25
        )


        # AREA PRINCIPAL

        self.main_area = ctk.CTkFrame(

            self,
            corner_radius=0,
            fg_color=BACKGROUND

        )

        self.main_area.grid(

            row=0,
            column=1,
            sticky="nsew",
            padx=25,
            pady=20

        )

        self.main_area.grid_columnconfigure(
            0,
            weight=1
        )


        # TITULO

        ctk.CTkLabel(

            self.main_area,
            text="PANEL DE CONTROL",
            font=("Segoe UI Black", 27, "bold"),
            text_color=TEXT

        ).grid(

            row=0,
            column=0,
            sticky="w",
            pady=(10, 5)

        )


        ctk.CTkLabel(

            self.main_area,
            text="HIERRO · DISCIPLINA · TRABAJO DURO",
            font=("Arial", 13),
            text_color=SECONDARY

        ).grid(

            row=1,
            column=0,
            sticky="w",
            pady=(0, 25)

        )


        # ==================================
        # TARJETAS
        # ==================================

        self.cards_frame = ctk.CTkFrame(

            self.main_area,
            fg_color="transparent"

        )

        self.cards_frame.grid(

            row=2,
            column=0,
            sticky="ew"

        )

        self.cards_frame.grid_columnconfigure(
            (0, 1, 2),
            weight=1
        )


        self.total_card = self.create_card(

            self.cards_frame,
            "SOCIOS REGISTRADOS",
            "0",
            0

        )


        self.active_card = self.create_card(

            self.cards_frame,
            "CUOTAS VIGENTES",
            "0",
            1

        )


        self.income_card = self.create_card(

            self.cards_frame,
            "INGRESOS DEL MES",
            "$0",
            2,
            privacy=True

        )


        # INFORMACION INFERIOR

        self.info_frame = ctk.CTkFrame(

            self.main_area,
            fg_color="#1B1F23",
            corner_radius=12,
            border_width=1,
            border_color="#41474E"

        )

        self.info_frame.grid(

            row=3,
            column=0,
            sticky="ew",
            pady=30

        )


        ctk.CTkLabel(

            self.info_frame,
            text="FORJAGYM",
            font=("Segoe UI Black", 23, "bold"),
            text_color=ORANGE

        ).pack(

            anchor="w",
            padx=25,
            pady=(20, 5)

        )


        ctk.CTkLabel(

            self.info_frame,
            text="GESTIÓN INTEGRAL PARA GIMNASIOS\nEntrená con método. Gestioná con claridad.",
            font=("Arial", 13),
            text_color=TEXT

        ).pack(

            anchor="w",
            padx=25,
            pady=(0, 20)

        )


    # ======================================
    # CREAR TARJETAS
    # ======================================

    def create_card(

        self,
        parent,
        title,
        value,
        column,
        privacy=False

    ):

        card = ctk.CTkFrame(

            parent,
            fg_color=CARD,
            corner_radius=12,
            height=125

        )

        card.grid(

            row=0,
            column=column,
            sticky="ew",
            padx=6,
            pady=5

        )

        card.grid_propagate(False)


        ctk.CTkLabel(

            card,
            text=title,
            font=("Arial", 11, "bold"),
            text_color=SECONDARY

        ).pack(

            anchor="w",
            padx=15,
            pady=(20, 5)

        )


        value_label = ctk.CTkLabel(

            card,
            text=value,
            font=("Arial", 25, "bold"),
            text_color=ORANGE

        )

        value_label.pack(

            anchor="w",
            padx=15

        )


        return value_label


    # ======================================
    # PRIVACIDAD FINANCIERA (ATAJO F3)
    # ======================================

    def _on_f3_toggle_money(self, event=None):
        self.show_money = not self.show_money
        self.update_income_display()

        # Actualizar las ventanas secundarias que estén abiertas.
        for window_name in (
            "pagos_window",
            "planes_window",
            "estadisticas_window",
        ):
            window = getattr(self, window_name, None)
            if window is not None:
                try:
                    if window.winfo_exists() and hasattr(window, "refresh_money_visibility"):
                        window.refresh_money_visibility()
                except Exception:
                    pass

        return "break"

    def update_income_display(self):
        if self.show_money:
            amount = f"${self.monthly_income:,}".replace(",", ".")
        else:
            amount = "••••••"
        self.income_card.configure(text=amount)


    # ======================================
    # ACTUALIZAR DASHBOARD
    # ======================================

    def refresh_dashboard(self):

        data = self.db.get_dashboard_summary()


        self.total_card.configure(

            text=str(data["total_members"])

        )


        self.active_card.configure(

            text=str(data["active_members"])

        )


        self.monthly_income = data["monthly_income"]

        self.update_income_display()


    # ======================================
    # NAVEGACION
    # ======================================

    def show_section(self, section):

        if section == "Panel principal":

            self.refresh_dashboard()

            return


        # SOCIOS

        if section == "Socios":

            if (

                self.socios_window is not None

                and self.socios_window.winfo_exists()

            ):

                self.socios_window.lift()

                self.socios_window.focus_force()

            else:

                self.socios_window = SociosWindow(

                    self,
                    self.db

                )

            return


        # PAGOS

        if section == "Pagos":

            if (

                self.pagos_window is not None

                and self.pagos_window.winfo_exists()

            ):

                self.pagos_window.lift()

                self.pagos_window.focus_force()

            else:

                self.pagos_window = PagosWindow(

                    self,
                    self.db

                )

            return


        # PLANES

        if section == "Planes":

            if (
                self.planes_window is not None
                and self.planes_window.winfo_exists()
            ):
                self.planes_window.lift()
                self.planes_window.focus_force()
            else:
                self.planes_window = PlanesWindow(self, self.db)

            return


        # ENTRENAMIENTOS / RUTINAS MAESTRAS
        if section == "Entrenamientos":
            if (self.entrenamientos_window is not None and self.entrenamientos_window.winfo_exists()):
                self.entrenamientos_window.lift()
                self.entrenamientos_window.focus_force()
            else:
                self.entrenamientos_window = EntrenamientosWindow(self, self.db)
            return


        # ASIGNACIÓN DE RUTINAS A SOCIOS Y EXPORTACIÓN PDF
        if section == "Rutinas de socios":
            if (self.rutinas_socios_window is not None and self.rutinas_socios_window.winfo_exists()):
                self.rutinas_socios_window.lift()
                self.rutinas_socios_window.focus_force()
            else:
                self.rutinas_socios_window = RutinasSociosWindow(self, self.db)
            return


        # ASISTENCIAS / HISTORIAL DE FICHAJES

        if section == "Asistencias":

            if (
                self.asistencias_window is not None
                and self.asistencias_window.winfo_exists()
            ):
                self.asistencias_window.lift()
                self.asistencias_window.focus_force()
            else:
                self.asistencias_window = AsistenciasWindow(self, self.db)

            return


        # ESTADISTICAS Y REPORTES

        if section == "Estadísticas":

            if (
                self.estadisticas_window is not None
                and self.estadisticas_window.winfo_exists()
            ):
                self.estadisticas_window.lift()
                self.estadisticas_window.focus_force()
            else:
                self.estadisticas_window = EstadisticasWindow(self, self.db)

            return


        # SECCIONES PENDIENTES

        messagebox.showinfo(

            "FORJAGYM",

            f"Sección seleccionada: {section}\n\n"

            "Esta funcionalidad será desarrollada "

            "en las próximas etapas."

        )


# ==========================================
# INICIAR PROGRAMA
# ==========================================

if __name__ == "__main__":

    app = ForjaGymApp()

    app.mainloop()
