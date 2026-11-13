import tkinter as tk
from pathlib import Path
import sys
from PIL import Image
from datetime import datetime

import customtkinter as ctk

from database import Database

try:
    import winsound
except ImportError:
    winsound = None


ORANGE = "#FF6600"
BACKGROUND = "#111315"
CARD = "#202429"
TEXT = "#FFFFFF"
SECONDARY = "#A0A5AB"
GREEN = "#20A464"
RED = "#D94343"
YELLOW = "#D99B25"


def resource_path(relative_path):
    """Resuelve recursos en desarrollo y en ejecutables PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative_path


class FichajeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.title("FORJAGYM | Fichaje")
        self.geometry("900x650")
        self.minsize(700, 550)
        self.configure(fg_color=BACKGROUND)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="#191C20", corner_radius=16,
                              border_width=1, border_color="#41474E")
        header.grid(row=0, column=0, sticky="ew", padx=36, pady=(22, 12))
        # Una sola columna garantiza el centrado geométrico real del bloque.
        # El reloj se posiciona de forma independiente para que no desplace el logo.
        header.grid_columnconfigure(0, weight=1)

        logo_path = resource_path("assets/logo_forjagym.png")
        logo_original = Image.open(logo_path).convert("RGBA")
        self.logo_image = ctk.CTkImage(
            light_image=logo_original,
            dark_image=logo_original,
            size=(170, 170)
        )
        ctk.CTkLabel(header, text="", image=self.logo_image).grid(
            row=0, column=0, padx=18, pady=(12, 2), sticky="n"
        )
        ctk.CTkLabel(
            header, text="CONTROL DE ACCESO",
            font=("Segoe UI Black", 24, "bold"), text_color=TEXT
        ).grid(row=1, column=0, pady=(2, 3))
        ctk.CTkLabel(
            header, text="GESTIÓN INTEGRAL PARA GIMNASIOS",
            font=("Segoe UI", 20, "bold"), text_color=ORANGE
        ).grid(row=2, column=0, pady=(0, 14))
        self.clock_label = ctk.CTkLabel(
            header, text="", font=("Segoe UI", 13, "bold"), text_color=SECONDARY
        )
        self.clock_label.place(relx=0.985, rely=0.06, anchor="ne")

        content = ctk.CTkFrame(self, fg_color=CARD, corner_radius=18,
                               border_width=1, border_color="#41474E")
        content.grid(row=1, column=0, sticky="nsew", padx=36, pady=(0, 24))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            content, text="INGRESÁ TU DNI", font=("Segoe UI Black", 25, "bold"),
            text_color=TEXT
        ).grid(row=0, column=0, pady=(34, 16))

        self.dni_var = tk.StringVar()
        self.dni_entry = ctk.CTkEntry(
            content, textvariable=self.dni_var, width=360, height=62,
            font=ctk.CTkFont(size=28, weight="bold"), justify="center",
            placeholder_text="DNI", border_color=ORANGE, border_width=2
        )
        self.dni_entry.grid(row=1, column=0, padx=20, pady=(0, 14))
        self.dni_entry.bind("<Return>", self.process_check_in)
        self.dni_entry.bind("<KP_Enter>", self.process_check_in)
        self.dni_entry.bind("<KeyRelease>", self.keep_numeric)

        self.submit_button = ctk.CTkButton(
            content, text="CONFIRMAR INGRESO", height=48, width=260,
            fg_color=ORANGE, hover_color="#D95700",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.process_check_in
        )
        self.submit_button.grid(row=2, column=0, pady=(0, 20))

        self.result_panel = ctk.CTkFrame(content, fg_color="#171A1E", corner_radius=14)
        self.result_panel.grid(row=3, column=0, sticky="ew", padx=28, pady=(0, 20))
        self.result_panel.grid_columnconfigure(0, weight=1)

        self.result_title = ctk.CTkLabel(
            self.result_panel, text="ESPERANDO DNI", text_color=SECONDARY,
            font=ctk.CTkFont(size=25, weight="bold")
        )
        self.result_title.pack(padx=20, pady=(24, 8))
        self.result_detail = ctk.CTkLabel(
            self.result_panel, text="Ingresá tu documento para validar el acceso.",
            text_color=TEXT, font=ctk.CTkFont(size=16), wraplength=650
        )
        self.result_detail.pack(padx=20, pady=(0, 24))

        ctk.CTkLabel(
            content, text="Cada ingreso consume una asistencia del cupo semanal. Semana: lunes a domingo.",
            text_color=SECONDARY, font=ctk.CTkFont(size=12)
        ).grid(row=4, column=0, sticky="s", pady=(0, 22))

        self.update_clock()
        self.after(250, self.dni_entry.focus_set)

    def keep_numeric(self, _event=None):
        value = self.dni_var.get()
        numeric = "".join(character for character in value if character.isdigit())
        if value != numeric:
            cursor = self.dni_entry.index(tk.INSERT)
            self.dni_var.set(numeric)
            self.dni_entry.icursor(min(cursor, len(numeric)))

    def update_clock(self):
        self.clock_label.configure(text=datetime.now().strftime("%d/%m/%Y  |  %H:%M:%S"))
        self.after(1000, self.update_clock)

    def play_feedback(self, allowed):
        if winsound:
            try:
                if allowed:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                else:
                    winsound.MessageBeep(winsound.MB_ICONHAND)
            except Exception:
                pass

    def process_check_in(self, _event=None):
        dni = self.dni_var.get().strip()
        if not dni:
            self.show_result("INGRESÁ UN DNI", "El campo no puede estar vacío.", YELLOW)
            self.dni_entry.focus_set()
            return "break"

        try:
            result = self.db.check_in_by_dni(dni)
            status = result["status"]
            member = result.get("member", {})
            full_name = " ".join(
                part for part in (member.get("first_name", ""), member.get("last_name", "")) if part
            ).strip()

            if status == "allowed":
                detail = (
                    f"{full_name}\n"
                    f"{result['payment']['plan_name']}\n"
                    f"Asistencias utilizadas: {result['used']} de {result['limit']}\n"
                    f"Disponibles esta semana: {result['remaining']}"
                )
                self.show_result("ACCESO PERMITIDO", detail, GREEN)
                self.play_feedback(True)
            else:
                messages = {
                    "not_found": "El DNI ingresado no está registrado.",
                    "inactive": f"{full_name}\nLa ficha está archivada. Consultá en recepción.",
                    "no_payment": f"{full_name}\nNo tiene una cuota registrada. Debe abonar para ingresar.",
                    "pending": f"{full_name}\nSu cuota todavía no comenzó.",
                    "expired": f"{full_name}\nSu cuota está vencida. Debe abonar para ingresar.",
                    "limit_reached": (
                        f"{full_name}\nYa utilizó {result['used']} de {result['limit']} asistencias "
                        "permitidas esta semana. El cupo se renueva el lunes."
                    ),
                }
                titles = {
                    "not_found": "SOCIO NO ENCONTRADO",
                    "inactive": "SOCIO INACTIVO",
                    "no_payment": "SIN CUOTA REGISTRADA",
                    "pending": "CUOTA NO VIGENTE",
                    "expired": "CUOTA VENCIDA",
                    "limit_reached": "SIN ASISTENCIAS DISPONIBLES",
                }
                color = YELLOW if status in ("pending", "limit_reached") else RED
                self.show_result(titles.get(status, "INGRESO RECHAZADO"), messages.get(status, result.get("message", "No se pudo validar el ingreso.")), color)
                self.play_feedback(False)
        except Exception as error:
            self.show_result("ERROR DE SISTEMA", f"No se pudo registrar el fichaje.\n{error}", RED)
            self.play_feedback(False)

        self.dni_var.set("")
        self.dni_entry.focus_set()
        return "break"

    def show_result(self, title, detail, color):
        self.result_title.configure(text=title, text_color=color)
        self.result_detail.configure(text=detail)


if __name__ == "__main__":
    app = FichajeApp()
    app.mainloop()
