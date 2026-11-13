import customtkinter as ctk
from tkinter import messagebox, filedialog
from datetime import date
from pathlib import Path
import sys
import xml.sax.saxutils as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether

ORANGE = "#FF6600"
BACKGROUND = "#111315"
CARD = "#202429"
TEXT = "#FFFFFF"
SECONDARY = "#A0A5AB"
DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def resource_path(relative_path):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative_path


def safe(value):
    return xml_escape.escape(str(value or "")).replace("\n", "<br/>")


class RutinasSociosWindow(ctk.CTkToplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.parent = parent
        self.selected_member = None
        self.selected_assignment = None
        self.title("FORJAGYM | Rutinas de socios")
        self.geometry("1080x720")
        self.minsize(900, 620)
        self.configure(fg_color=BACKGROUND)
        self.transient(parent)
        self.grab_set()
        self._build()
        self.refresh_members()
        self.refresh_templates()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 10))
        ctk.CTkLabel(header, text="RUTINAS DE SOCIOS", font=("Arial", 25, "bold"), text_color=ORANGE).pack(anchor="w")
        ctk.CTkLabel(header, text="Asigná una copia individual de una rutina maestra y exportá el plan en PDF.", text_color=SECONDARY).pack(anchor="w", pady=(3, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        body.grid_columnconfigure(0, weight=1, minsize=330)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color=CARD, corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(left, text="1. SELECCIONAR SOCIO", font=("Arial", 14, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))
        self.search_entry = ctk.CTkEntry(left, placeholder_text="Buscar por nombre, apellido o DNI")
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda _e: self.refresh_members())
        self.member_list = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.member_list.grid(row=2, column=0, sticky="nsew", padx=8, pady=5)
        self.member_label = ctk.CTkLabel(left, text="Ningún socio seleccionado", text_color=SECONDARY, wraplength=290)
        self.member_label.grid(row=3, column=0, sticky="ew", padx=12, pady=10)

        right = ctk.CTkFrame(body, fg_color=CARD, corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(5, weight=1)
        ctk.CTkLabel(right, text="2. ASIGNAR RUTINA MAESTRA", font=("Arial", 14, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        self.template_menu = ctk.CTkOptionMenu(right, values=["Sin rutinas maestras"], fg_color="#343A40", button_color=ORANGE, button_hover_color="#D95700")
        self.template_menu.grid(row=1, column=0, sticky="ew", padx=16, pady=5)
        self.template_by_name = {}
        date_row = ctk.CTkFrame(right, fg_color="transparent")
        date_row.grid(row=2, column=0, sticky="ew", padx=16, pady=5)
        ctk.CTkLabel(date_row, text="Fecha de inicio (AAAA-MM-DD):", text_color=SECONDARY).pack(side="left")
        self.start_date = ctk.CTkEntry(date_row, width=140)
        self.start_date.pack(side="right")
        self.start_date.insert(0, date.today().isoformat())
        actions = ctk.CTkFrame(right, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=16, pady=9)
        ctk.CTkButton(actions, text="ASIGNAR AL SOCIO", fg_color=ORANGE, hover_color="#D95700", command=self.assign).pack(side="left")
        ctk.CTkButton(actions, text="EXPORTAR PDF", fg_color="#343A40", hover_color="#4A5159", command=self.export_pdf).pack(side="left", padx=8)
        ctk.CTkButton(actions, text="VER RUTINA", fg_color=ORANGE, hover_color="#D95700", command=self.view_routine).pack(side="left", padx=8)
        ctk.CTkLabel(right, text="ASIGNACIÓN ACTUAL / HISTORIAL", font=("Arial", 13, "bold")).grid(row=4, column=0, sticky="w", padx=16, pady=(8, 4))
        self.history = ctk.CTkScrollableFrame(right, fg_color="#171A1E")
        self.history.grid(row=5, column=0, sticky="nsew", padx=16, pady=(0, 14))

    def refresh_members(self):
        for w in self.member_list.winfo_children():
            w.destroy()
        query = self.search_entry.get().strip() if hasattr(self, "search_entry") else ""
        for member in self.db.get_members(query):
            label = f'{member["last_name"]}, {member["first_name"]}  |  DNI {member["dni"]}'
            ctk.CTkButton(self.member_list, text=label, anchor="w", fg_color="#30363D", hover_color=ORANGE,
                          command=lambda m=member: self.select_member(m)).pack(fill="x", padx=3, pady=3)

    def refresh_templates(self):
        rows = self.db.get_workout_templates()
        self.template_by_name = {r["name"]: r["id"] for r in rows}
        names = list(self.template_by_name) or ["Sin rutinas maestras"]
        self.template_menu.configure(values=names)
        self.template_menu.set(names[0])

    def select_member(self, member):
        self.selected_member = member
        self.selected_assignment = None
        self.member_label.configure(text=f'Socio seleccionado:\n{member["first_name"]} {member["last_name"]}\nDNI: {member["dni"]}', text_color=TEXT)
        self.refresh_history()

    def refresh_history(self):
        for w in self.history.winfo_children():
            w.destroy()
        if not self.selected_member:
            ctk.CTkLabel(self.history, text="Seleccioná un socio para consultar sus rutinas.", text_color=SECONDARY).pack(pady=12)
            return
        rows = self.db.get_member_workout_history(self.selected_member["id"])
        if not rows:
            ctk.CTkLabel(self.history, text="Este socio todavía no tiene rutinas asignadas.", text_color=SECONDARY).pack(pady=12)
            return
        for row in rows:
            status = "ACTUAL" if row["active"] else "ANTERIOR"
            ctk.CTkButton(self.history, text=f'{status}  |  {row["routine_name"]}  |  Desde {row["start_date"]}',
                          anchor="w", fg_color=ORANGE if row["active"] else "#30363D", hover_color="#D95700",
                          command=lambda rid=row["id"]: self.select_assignment(rid)).pack(fill="x", padx=3, pady=3)

    def select_assignment(self, assignment_id):
        self.selected_assignment = assignment_id
        self.export_pdf()

    def assign(self):
        if not self.selected_member:
            messagebox.showwarning("Rutinas", "Primero seleccioná un socio.", parent=self)
            return
        name = self.template_menu.get()
        template_id = self.template_by_name.get(name)
        if not template_id:
            messagebox.showwarning("Rutinas", "No hay una rutina maestra disponible.", parent=self)
            return
        try:
            assignment_id = self.db.assign_workout_to_member(self.selected_member["id"], template_id, self.start_date.get())
            self.selected_assignment = assignment_id
            self.refresh_history()
            messagebox.showinfo("Rutinas", "Rutina asignada correctamente. Se guardó una copia independiente para este socio.", parent=self)
        except Exception as exc:
            messagebox.showerror("No se pudo asignar", str(exc), parent=self)

    def view_routine(self):
        """Abre la rutina individual del socio dentro de ADMIN, sin generar archivos."""
        if not self.selected_member:
            messagebox.showwarning("Rutina", "Primero seleccioná un socio.", parent=self)
            return

        detail = self.db.get_member_workout_assignment(
            self.selected_member["id"], self.selected_assignment
        )
        if not detail:
            messagebox.showinfo(
                "Rutina", "Este socio todavía no tiene una rutina asignada.", parent=self
            )
            return

        RoutineViewerWindow(self, self.selected_member, detail)

    def export_pdf(self):
        if not self.selected_member:
            messagebox.showwarning("PDF", "Primero seleccioná un socio.", parent=self)
            return
        detail = self.db.get_member_workout_assignment(self.selected_member["id"], self.selected_assignment)
        if not detail:
            messagebox.showwarning("PDF", "El socio no tiene una rutina asignada para exportar.", parent=self)
            return
        member = self.selected_member
        default = f'Rutina_{member["last_name"]}_{member["first_name"]}.pdf'.replace(" ", "_")
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".pdf", initialfile=default, filetypes=[("Documento PDF", "*.pdf")])
        if not path:
            return
        try:
            self._create_pdf(path, member, detail)
            messagebox.showinfo("PDF generado", f"El PDF se exportó correctamente:\n{path}", parent=self)
        except Exception as exc:
            messagebox.showerror("Error al exportar PDF", str(exc), parent=self)

    def _create_pdf(self, path, member, detail):
        styles = getSampleStyleSheet()
        title = ParagraphStyle("ForjaTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=19, leading=22, textColor=colors.HexColor("#FF6600"), alignment=TA_CENTER, spaceAfter=4)
        sub = ParagraphStyle("ForjaSub", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.HexColor("#333333"), alignment=TA_CENTER)
        heading = ParagraphStyle("DayHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#FF6600"), spaceBefore=10, spaceAfter=4)
        normal = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8, leading=10)
        story = []
        logo = resource_path("assets/logo_forjagym.png")
        if logo.exists():
            img = RLImage(str(logo), width=27*mm, height=27*mm, kind="proportional")
            img.hAlign = "CENTER"
            story.extend([img, Spacer(1, 3*mm)])
        story += [Paragraph("FORJAGYM", title), Paragraph("GESTIÓN INTEGRAL PARA GIMNASIOS", sub),
                  Paragraph("Entrená con método. Gestioná con claridad.", sub), Spacer(1, 7*mm)]
        assignment = detail["assignment"]
        story.append(Paragraph(f'<b>Socio:</b> {safe(member["first_name"])} {safe(member["last_name"])}', normal))
        story.append(Paragraph(f'<b>DNI:</b> {safe(member["dni"])}', normal))
        story.append(Paragraph(f'<b>Rutina:</b> {safe(assignment["routine_name"])}', normal))
        story.append(Paragraph(f'<b>Fecha de inicio:</b> {safe(assignment["start_date"])}', normal))
        if assignment.get("routine_description"):
            story.append(Paragraph(f'<b>Descripción:</b> {safe(assignment["routine_description"])}', normal))
        story.append(Spacer(1, 5*mm))
        for item in detail["days"]:
            day = item["day"]
            label = DAYS[day["weekday"]]
            group = safe(day["muscle_groups"] or "Sin grupos especificados")
            parts = [Paragraph(f'{label} — {group}', heading)]
            if day["notes"]:
                parts.append(Paragraph(f'<b>Notas del día:</b> {safe(day["notes"])}', normal))
            data = [["Ejercicio", "Series", "Repeticiones", "Peso ref.", "Notas"]]
            for ex in item["exercises"]:
                data.append([Paragraph(safe(ex["name"]), normal), Paragraph(safe(ex["sets"]), normal),
                             Paragraph(safe(ex["reps"]), normal), Paragraph(safe(ex["reference_weight"]), normal),
                             Paragraph(safe(ex["notes"]), normal)])
            if len(data) == 1:
                data.append([Paragraph("Sin ejercicios cargados", normal), "", "", "", ""])
            table = Table(data, colWidths=[48*mm, 17*mm, 25*mm, 22*mm, 53*mm], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#252A30")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE", (0,0), (-1,-1), 8),
                ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#B8B8B8")),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F2F2F2")]),
                ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
                ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ]))
            parts.append(table)
            story.append(KeepTogether(parts))
        doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=13*mm, leftMargin=13*mm, topMargin=12*mm, bottomMargin=14*mm, title=f'Rutina {member["first_name"]} {member["last_name"]}')
        doc.build(story)

# -----------------------------------------------------------------------------
# REDISEÑO PDF MOBILE FIRST — reemplaza el generador anterior sin alterar la UI.
# -----------------------------------------------------------------------------
def _create_pdf_mobile(self, path, member, detail):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image as RLImage, PageBreak
    )

    FIRE = colors.HexColor("#FF6600")
    GRAPHITE = colors.HexColor("#202429")
    DEEP = colors.HexColor("#111315")
    MID = colors.HexColor("#3A4148")
    LIGHT = colors.HexColor("#F1F3F5")
    MUTED = colors.HexColor("#626A73")
    WHITE = colors.white

    # Página vertical angosta/alta: se adapta mejor al desplazamiento en teléfono.
    page_size = (160 * mm, 240 * mm)
    margin_x, margin_top, margin_bottom = 8 * mm, 8 * mm, 12 * mm
    usable = page_size[0] - 2 * margin_x

    base = getSampleStyleSheet()
    brand = ParagraphStyle("BGBrand", parent=base["Title"], fontName="Helvetica-Bold",
        fontSize=19, leading=21, textColor=FIRE, alignment=TA_CENTER, spaceAfter=1 * mm)
    slogan = ParagraphStyle("BGSlogan", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=7.8, leading=10, textColor=GRAPHITE, alignment=TA_CENTER)
    motto = ParagraphStyle("BGMotto", parent=base["Normal"], fontName="Helvetica-Oblique",
        fontSize=8, leading=10, textColor=MUTED, alignment=TA_CENTER)
    section = ParagraphStyle("BGSection", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=10, leading=12, textColor=WHITE)
    day_style = ParagraphStyle("BGDay", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=9.5, leading=12, textColor=WHITE)
    label = ParagraphStyle("BGLabel", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=6.8, leading=8, textColor=MUTED)
    value = ParagraphStyle("BGValue", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=8.5, leading=10, textColor=DEEP)
    cell = ParagraphStyle("BGCell", parent=base["BodyText"], fontName="Helvetica",
        fontSize=7.4, leading=9, textColor=GRAPHITE, splitLongWords=1)
    cell_bold = ParagraphStyle("BGCellBold", parent=cell, fontName="Helvetica-Bold")
    th = ParagraphStyle("BGTH", parent=base["Normal"], fontName="Helvetica-Bold",
        fontSize=6.8, leading=8, textColor=WHITE)
    day_note = ParagraphStyle("BGDayNote", parent=base["BodyText"], fontSize=7.8,
        leading=10, textColor=GRAPHITE, spaceAfter=1.5 * mm)
    advice_head = ParagraphStyle("BGAdviceHead", parent=base["Heading2"],
        fontName="Helvetica-Bold", fontSize=9.5, leading=11, textColor=FIRE,
        spaceBefore=3 * mm, spaceAfter=1.5 * mm)
    advice = ParagraphStyle("BGAdvice", parent=base["BodyText"], fontName="Helvetica",
        fontSize=8.2, leading=11.5, textColor=GRAPHITE, leftIndent=2 * mm, spaceAfter=2 * mm)

    def para(text, style=cell):
        return Paragraph(safe(text if text not in (None, "") else "—"), style)

    def page_decor(canvas, doc):
        canvas.saveState()
        w, h = page_size
        canvas.setFillColor(DEEP)
        canvas.rect(0, h - 3 * mm, w, 3 * mm, stroke=0, fill=1)
        canvas.setStrokeColor(FIRE)
        canvas.setLineWidth(1)
        canvas.line(margin_x, 8 * mm, w - margin_x, 8 * mm)
        canvas.setFont("Helvetica-Bold", 6.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(margin_x, 4.5 * mm, "FORJAGYM  •  FUERZA · DISCIPLINA · RESULTADOS")
        canvas.drawRightString(w - margin_x, 4.5 * mm, f"PÁG. {doc.page}")
        canvas.restoreState()

    story = []
    assignment = detail["assignment"]
    logo = resource_path("assets/logo_forjagym.png")
    if logo.exists():
        try:
            logo_img = RLImage(str(logo), width=22 * mm, height=22 * mm, kind="proportional")
            logo_img.hAlign = "CENTER"
            story.extend([logo_img, Spacer(1, 1 * mm)])
        except Exception:
            pass

    story.extend([
        Paragraph("FORJAGYM", brand),
        Paragraph("GESTIÓN INTEGRAL PARA GIMNASIOS", slogan),
        Paragraph("“Entrená con método. Gestioná con claridad.”", motto),
        Spacer(1, 3.5 * mm),
    ])

    # Ficha del alumno en dos columnas y dos filas para aprovechar el ancho móvil.
    meta = [
        [para("ALUMNO", label), para("DNI", label)],
        [para(f'{member.get("first_name", "")} {member.get("last_name", "")}', value),
         para(member.get("dni", ""), value)],
        [para("RUTINA ASIGNADA", label), para("FECHA DE INICIO", label)],
        [para(assignment.get("routine_name", ""), value),
         para(assignment.get("start_date", ""), value)],
    ]
    meta_table = Table(meta, colWidths=[usable * .60, usable * .40])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BACKGROUND", (0, 0), (-1, 0), GRAPHITE),
        ("BOX", (0, 0), (-1, -1), .6, colors.HexColor("#D2D7DC")),
        ("INNERGRID", (0, 0), (-1, -1), .35, colors.HexColor("#D2D7DC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([meta_table, Spacer(1, 3.5 * mm)])

    if assignment.get("routine_description"):
        story.extend([Paragraph("SOBRE ESTA RUTINA", advice_head),
                      Paragraph(safe(assignment["routine_description"]), advice)])

    def banner(text):
        t = Table([[Paragraph(text, section)]], colWidths=[usable])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GRAPHITE),
            ("LINEBEFORE", (0, 0), (0, 0), 3, FIRE),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return t

    story.extend([banner("PLANIFICACIÓN SEMANAL"), Spacer(1, 2 * mm)])
    widths = [usable * .34, usable * .10, usable * .15, usable * .13, usable * .28]
    for item in detail.get("days", []):
        day = item["day"]
        idx = int(day["weekday"])
        day_name = DAYS[idx] if 0 <= idx < len(DAYS) else f"Día {idx + 1}"
        muscle_groups = safe(day.get("muscle_groups") or "Grupos no especificados")
        day_band = Table([[Paragraph(f"{day_name.upper()}  |  {muscle_groups}", day_style)]],
                         colWidths=[usable])
        day_band.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GRAPHITE),
            ("LINEBEFORE", (0, 0), (0, 0), 3, FIRE),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.extend([day_band, Spacer(1, 1 * mm)])
        if day.get("notes"):
            story.append(Paragraph(f"<b>ENFOQUE DEL DÍA:</b> {safe(day['notes'])}", day_note))
        rows = [[Paragraph("EJERCICIO", th), Paragraph("SER.", th),
                 Paragraph("REPS.", th), Paragraph("PESO", th), Paragraph("NOTAS / TIPS", th)]]
        for ex in item.get("exercises", []):
            rows.append([para(ex.get("name"), cell_bold), para(ex.get("sets")),
                         para(ex.get("reps")), para(ex.get("reference_weight")),
                         para(ex.get("notes"))])
        if len(rows) == 1:
            rows.append([para("Sin ejercicios cargados"), "", "", "", ""])
        table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), MID),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
            ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#D2D7DC")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([table, Spacer(1, 2.5 * mm)])

    # Consejos en página separada para que no compitan visualmente con la rutina.
    story.extend([
        PageBreak(), banner("GUÍA PARA ENTRENAR Y PROGRESAR"), Spacer(1, 2 * mm),
        Paragraph("La rutina es una guía de trabajo. La prioridad es ejecutar cada repetición con control y sostener el progreso semana a semana.", advice),
        Paragraph("01  ·  INTENSIDAD Y REPETICIONES EN RECÁMARA", advice_head),
        Paragraph("<b>Ejercicios compuestos:</b> terminá normalmente con 1 a 3 repeticiones en reserva. No hace falta llegar al fallo en todas las series.", advice),
        Paragraph("<b>Ejercicios de aislamiento:</b> podés acercarte a 0–2 repeticiones en reserva si mantenés la técnica y no aparece dolor.", advice),
        Paragraph("02  ·  CÓMO PROGRESAR", advice_head),
        Paragraph("Cuando completes el máximo del rango de repeticiones en todas las series con buena técnica, aumentá un poco la carga en la próxima sesión.", advice),
        Paragraph("Si no llegás al mínimo del rango o la técnica se deteriora, mantené el peso o reducí la carga. No sacrifiques ejecución para levantar más.", advice),
        Paragraph("03  ·  TÉCNICA Y CONTROL", advice_head),
        Paragraph("Realizá cada repetición con recorrido controlado. Evitá impulsos innecesarios y respetá la postura indicada para cada ejercicio.", advice),
        Paragraph("Si aparece dolor agudo, mareo o una molestia fuera de lo habitual, detené el ejercicio y consultá al profesional a cargo.", advice),
        Paragraph("04  ·  REGISTRO Y CONSTANCIA", advice_head),
        Paragraph("Anotá las cargas y repeticiones realizadas. Comparar esos datos te permite comprobar si estás progresando y ajustar el entrenamiento con criterio.", advice),
        Paragraph("La recuperación, el descanso y la constancia también forman parte del entrenamiento. No busques terminar destruido: buscá acumular buenas sesiones.", advice),
    ])
    closing_style = ParagraphStyle("BGClosing", parent=slogan, fontSize=9, leading=12, textColor=WHITE)
    closing = Table([[Paragraph("<b>COMUNIDAD FORJAGYM</b><br/>Entrená con método. Gestioná con claridad.", closing_style)]],
                    colWidths=[usable])
    closing.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DEEP),
        ("LINEABOVE", (0, 0), (-1, 0), 2, FIRE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([Spacer(1, 3 * mm), closing])

    doc = SimpleDocTemplate(
        path, pagesize=page_size, leftMargin=margin_x, rightMargin=margin_x,
        topMargin=margin_top, bottomMargin=margin_bottom,
        title=f'Rutina {member.get("first_name", "")} {member.get("last_name", "")} - ForjaGym',
        author="FORJAGYM", subject="Plan personalizado de entrenamiento"
    )
    doc.build(story, onFirstPage=page_decor, onLaterPages=page_decor)


# La ventana existente conserva todas sus funciones; solo cambia el diseño del PDF.
RutinasSociosWindow._create_pdf = _create_pdf_mobile


def _create_pdf_card_design(self, path, member, detail):
    """Genera un PDF de dos páginas, mobile-first, con tarjetas FORJAGYM."""
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfbase.pdfmetrics import stringWidth

    W, H = 160 * mm, 240 * mm
    M = 7 * mm
    CONTENT_W = W - 2 * M

    ORANGE = colors.HexColor("#FF6600")
    GRAPHITE = colors.HexColor("#202429")
    DARK = colors.HexColor("#111315")
    MID = colors.HexColor("#3A4148")
    LIGHT = colors.HexColor("#EEF0F2")
    LIGHT2 = colors.HexColor("#E2E5E8")
    WHITE = colors.white
    TEXT = colors.HexColor("#24282D")
    MUTED = colors.HexColor("#68717A")

    c = canvas.Canvas(path, pagesize=(W, H), pageCompression=1)
    c.setTitle(f'Rutina {member.get("first_name", "")} {member.get("last_name", "")} | FORJAGYM')
    c.setAuthor("FORJAGYM")
    c.setSubject("Plan personalizado de entrenamiento")

    def txt(value):
        return str(value if value not in (None, "") else "—").replace("\r", " ").replace("\n", " ").strip()

    def wrapped(value, font, size, width):
        return simpleSplit(txt(value), font, size, width) or ["—"]

    def draw_lines(lines, x, y, font, size, leading, color=TEXT):
        c.setFillColor(color)
        c.setFont(font, size)
        for line in lines:
            c.drawString(x, y, line)
            y -= leading
        return y

    def footer(page):
        c.setStrokeColor(ORANGE)
        c.setLineWidth(1.2)
        c.line(M, 8.5*mm, W-M, 8.5*mm)
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Bold", 5.8)
        c.drawString(M, 4.8*mm, "FORJAGYM  •  GESTIÓN INTEGRAL PARA GIMNASIOS")
        c.drawRightString(W-M, 4.8*mm, f"{page} / 2")

    # ── PAGE 1: encabezado + ficha + planificación completa ───────────────
    y = H - 8*mm
    c.setFillColor(DARK)
    c.rect(0, H-3.2*mm, W, 3.2*mm, stroke=0, fill=1)

    logo = resource_path("assets/logo_forjagym.png")
    if logo.exists():
        try:
            c.drawImage(str(logo), W/2-10*mm, y-20*mm, width=20*mm, height=20*mm,
                        preserveAspectRatio=True, anchor="c", mask="auto")
            y -= 22*mm
        except Exception:
            y -= 2*mm
    else:
        y -= 2*mm

    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 17)
    c.drawCentredString(W/2, y, "FORJAGYM")
    y -= 4.5*mm
    c.setFillColor(GRAPHITE)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawCentredString(W/2, y, "GESTIÓN INTEGRAL PARA GIMNASIOS")
    y -= 3.5*mm
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Oblique", 6.7)
    c.drawCentredString(W/2, y, "Entrená con método. Gestioná con claridad.")
    y -= 5*mm

    # Student information as a dark header + two compact grey info rows.
    info_h = 20*mm
    c.setFillColor(LIGHT)
    c.roundRect(M, y-info_h, CONTENT_W, info_h, 2.2*mm, stroke=0, fill=1)
    c.setFillColor(GRAPHITE)
    c.roundRect(M, y-5.4*mm, CONTENT_W, 5.4*mm, 2.2*mm, stroke=0, fill=1)
    c.rect(M, y-5.4*mm, CONTENT_W, 2.2*mm, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 6.2)
    c.drawString(M+3*mm, y-3.6*mm, "FICHA DEL ALUMNO")
    y -= 8.5*mm

    half = CONTENT_W/2
    fields = [
        ("ALUMNO", f'{member.get("first_name", "")} {member.get("last_name", "")}'),
        ("DNI", member.get("dni", "")),
        ("RUTINA", detail["assignment"].get("routine_name", "")),
        ("INICIO", detail["assignment"].get("start_date", "")),
    ]
    positions = [(M+3*mm, y), (M+half+2*mm, y),
                 (M+3*mm, y-7.5*mm), (M+half+2*mm, y-7.5*mm)]
    for (label, value), (x, yy) in zip(fields, positions):
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(x, yy, label)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 7.2)
        val_lines = wrapped(value, "Helvetica-Bold", 7.2, half-8*mm)
        c.drawString(x, yy-3.2*mm, val_lines[0][:70])
    y -= 14.5*mm

    # Weekly section label
    c.setFillColor(GRAPHITE)
    c.roundRect(M, y-6*mm, CONTENT_W, 6*mm, 1.2*mm, stroke=0, fill=1)
    c.setFillColor(ORANGE)
    c.rect(M, y-6*mm, 2*mm, 6*mm, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(M+5*mm, y-4.1*mm, "PLANIFICACIÓN SEMANAL")
    y -= 8*mm

    days = detail.get("days", [])
    # Fit the complete training plan on page one by selecting a compact type scale.
    # The design stays readable; long notes wrap within their own cell.
    def measure_plan(font_size):
        leading = font_size * 1.16
        total = 0
        for item in days:
            day = item["day"]
            groups = txt(day.get("muscle_groups") or "Grupos no especificados")
            title_lines = wrapped(f'{DAYS[int(day["weekday"])] if 0 <= int(day["weekday"]) < 7 else "Día"}  |  {groups}',
                                  "Helvetica-Bold", font_size+1.0, CONTENT_W-12*mm)
            total += max(5.2*mm, len(title_lines)*leading+2.4*mm)
            if day.get("notes"):
                total += len(wrapped(day["notes"], "Helvetica", font_size, CONTENT_W-7*mm))*leading + 1.2*mm
            # header
            total += leading + 2.2*mm
            for ex in item.get("exercises", []):
                # five visual columns: exercise / sets / reps / weight / tips
                col_w = [CONTENT_W*.25, CONTENT_W*.085, CONTENT_W*.13, CONTENT_W*.12, CONTENT_W*.415]
                vals = [ex.get("name"), ex.get("sets"), ex.get("reps"),
                        ex.get("reference_weight"), ex.get("notes")]
                n = max(len(wrapped(v, "Helvetica-Bold" if i == 0 else "Helvetica",
                                    font_size, col_w[i]-2.2*mm)) for i, v in enumerate(vals))
                total += max(4.6*mm, n*leading+2.0*mm)
            if not item.get("exercises"):
                total += 5*mm
            total += 2.2*mm
        return total

    available = y - (15*mm)
    fs = 6.4
    while fs > 4.8 and measure_plan(fs) > available:
        fs -= 0.2
    if measure_plan(fs) > available:
        raise ValueError("La rutina tiene demasiados ejercicios o notas para entrar en una sola página móvil. Reducí el texto de las notas o dividí la rutina en más de un plan.")

    leading = fs*1.16
    col_w = [CONTENT_W*.25, CONTENT_W*.085, CONTENT_W*.13, CONTENT_W*.12, CONTENT_W*.415]
    for item in days:
        day = item["day"]
        weekday = int(day["weekday"])
        day_name = DAYS[weekday].upper() if 0 <= weekday < 7 else f"DÍA {weekday+1}"
        groups = txt(day.get("muscle_groups") or "Grupos no especificados")
        title = f"{day_name}  |  {groups}"
        title_lines = wrapped(title, "Helvetica-Bold", fs+1, CONTENT_W-12*mm)
        band_h = max(5.2*mm, len(title_lines)*(fs+1)*1.15+2.2*mm)
        c.setFillColor(GRAPHITE)
        c.roundRect(M, y-band_h, CONTENT_W, band_h, 1.4*mm, stroke=0, fill=1)
        c.setFillColor(ORANGE)
        c.roundRect(M, y-band_h, 2*mm, band_h, .7*mm, stroke=0, fill=1)
        draw_lines(title_lines, M+5*mm, y-3.5*mm, "Helvetica-Bold", fs+1, (fs+1)*1.15, WHITE)
        y -= band_h + 1.1*mm

        if day.get("notes"):
            note_lines = wrapped(day["notes"], "Helvetica", fs, CONTENT_W-8*mm)
            c.setFillColor(MID)
            c.setFont("Helvetica-Bold", fs)
            c.drawString(M+2*mm, y, "ENFOQUE")
            draw_lines(note_lines, M+17*mm, y, "Helvetica", fs, leading, TEXT)
            y -= max(len(note_lines)*leading, leading) + 1.1*mm

        # table header row
        headers = ["EJERCICIO", "SER.", "REPS.", "PESO", "NOTAS / TIPS"]
        header_h = leading+2.2*mm
        c.setFillColor(MID)
        c.roundRect(M, y-header_h, CONTENT_W, header_h, 0.8*mm, stroke=0, fill=1)
        x = M
        for label, cw in zip(headers, col_w):
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", fs-0.3)
            c.drawString(x+1.1*mm, y-3.3*mm, label)
            x += cw
        y -= header_h

        exercises = item.get("exercises", [])
        if not exercises:
            exercises = [{"name":"Sin ejercicios cargados"}]
        for ri, ex in enumerate(exercises):
            vals = [ex.get("name"), ex.get("sets"), ex.get("reps"),
                    ex.get("reference_weight"), ex.get("notes")]
            fonts = ["Helvetica-Bold", "Helvetica", "Helvetica", "Helvetica", "Helvetica"]
            line_sets = [wrapped(v, fonts[i], fs, col_w[i]-2.2*mm) for i, v in enumerate(vals)]
            row_lines = max(len(lines) for lines in line_sets)
            row_h = max(4.6*mm, row_lines*leading+2.0*mm)
            c.setFillColor(LIGHT if ri % 2 == 0 else LIGHT2)
            c.roundRect(M, y-row_h, CONTENT_W, row_h, .6*mm, stroke=0, fill=1)
            x = M
            for i, (lines, cw) in enumerate(zip(line_sets, col_w)):
                draw_lines(lines, x+1.1*mm, y-2.8*mm, fonts[i], fs, leading, TEXT)
                x += cw
            y -= row_h
        y -= 2.1*mm

    footer(1)
    c.showPage()

    # ── PAGE 2: guidance in branded, soft-grey cards ──────────────────────
    y = H - 10*mm
    c.setFillColor(DARK)
    c.rect(0, H-3.2*mm, W, 3.2*mm, stroke=0, fill=1)
    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(M, y-5*mm, "GUÍA PARA ENTRENAR")
    c.setFillColor(GRAPHITE)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(M, y-12*mm, "Y PROGRESAR")
    y -= 19*mm
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.2)
    intro = "La rutina es una guía de trabajo. La prioridad es ejecutar cada repetición con control y sostener el progreso semana a semana."
    for line in wrapped(intro, "Helvetica", 7.2, CONTENT_W):
        c.drawString(M, y, line)
        y -= 3.2*mm
    y -= 3*mm

    cards = [
        ("01", "INTENSIDAD Y REPETICIONES EN RECÁMARA", [
            ("EJERCICIOS COMPUESTOS", "Terminá normalmente con 1 a 3 repeticiones en reserva. No hace falta llegar al fallo en todas las series."),
            ("EJERCICIOS DE AISLAMIENTO", "Podés acercarte a 0–2 repeticiones en reserva si mantenés la técnica y no aparece dolor."),
        ]),
        ("02", "CÓMO PROGRESAR", [
            ("PROGRESIÓN DE CARGA", "Cuando completes el máximo del rango de repeticiones en todas las series con buena técnica, aumentá un poco la carga en la próxima sesión."),
            ("SI LA TÉCNICA SE DETERIORA", "Si no llegás al mínimo del rango o la técnica se deteriora, mantené el peso o reducí la carga. No sacrifiques ejecución para levantar más."),
        ]),
        ("03", "TÉCNICA Y CONTROL", [
            ("EJECUCIÓN", "Realizá cada repetición con recorrido controlado. Evitá impulsos innecesarios y respetá la postura indicada para cada ejercicio."),
            ("SEÑALES DE ALERTA", "Si aparece dolor agudo, mareo o una molestia fuera de lo habitual, detené el ejercicio y consultá al profesional a cargo."),
        ]),
        ("04", "REGISTRO Y CONSTANCIA", [
            ("REGISTRÁ TUS RESULTADOS", "Anotá las cargas y repeticiones realizadas. Comparar esos datos te permite comprobar si estás progresando y ajustar el entrenamiento con criterio."),
            ("RECUPERACIÓN", "La recuperación, el descanso y la constancia también forman parte del entrenamiento. No busques terminar destruido: buscá acumular buenas sesiones."),
        ]),
    ]

    # Use card heights based on wrapped copy; the second page is kept visually balanced.
    for number, title, entries in cards:
        body_lines = []
        for label, copy in entries:
            body_lines.append((label, wrapped(copy, "Helvetica", 7.2, CONTENT_W-15*mm)))
        card_h = 10*mm
        for label, lines in body_lines:
            card_h += 3.2*mm + len(lines)*3.3*mm + 1.4*mm
        c.setFillColor(LIGHT)
        c.roundRect(M, y-card_h, CONTENT_W, card_h, 2*mm, stroke=0, fill=1)
        c.setFillColor(GRAPHITE)
        c.roundRect(M, y-7*mm, CONTENT_W, 7*mm, 1.8*mm, stroke=0, fill=1)
        c.rect(M, y-7*mm, CONTENT_W, 2*mm, stroke=0, fill=1)
        c.setFillColor(ORANGE)
        c.roundRect(M, y-7*mm, 8*mm, 7*mm, 1.5*mm, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(M+4*mm, y-4.8*mm, number)
        c.setFont("Helvetica-Bold", 7.1)
        c.drawString(M+11*mm, y-4.8*mm, title)
        yy = y-11*mm
        for label, lines in body_lines:
            c.setFillColor(ORANGE)
            c.setFont("Helvetica-Bold", 6.3)
            c.drawString(M+4*mm, yy, label)
            yy -= 3.2*mm
            yy = draw_lines(lines, M+4*mm, yy, "Helvetica", 7.2, 3.3*mm, TEXT)
            yy -= 1.4*mm
        y -= card_h + 3*mm

    # Brand close-out panel
    close_h = 13*mm
    c.setFillColor(DARK)
    c.roundRect(M, y-close_h, CONTENT_W, close_h, 2*mm, stroke=0, fill=1)
    c.setFillColor(ORANGE)
    c.rect(M, y-close_h, CONTENT_W, 1.5*mm, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(W/2, y-6*mm, "COMUNIDAD FORJAGYM")
    c.setFont("Helvetica", 7.2)
    c.drawCentredString(W/2, y-9.5*mm, "Entrená con método. Gestioná con claridad.")

    footer(2)
    c.save()


RutinasSociosWindow._create_pdf = _create_pdf_card_design


def _create_pdf_mobile_legible(self, path, member, detail):
    """PDF mobile-first legible: tipografía mayor, cabecera despejada y tarjetas sin solaparse."""
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.utils import simpleSplit

    # A5 vertical, más ancho que la versión anterior para ganar tamaño real en el móvil.
    W, H = 148 * mm, 240 * mm
    M = 8 * mm
    CW = W - 2 * M
    TOP = H - 8 * mm
    FOOT = 14 * mm

    ORANGE = colors.HexColor("#FF6500")
    GRAPHITE = colors.HexColor("#202429")
    DARK = colors.HexColor("#111315")
    MID = colors.HexColor("#3B4249")
    PALE = colors.HexColor("#F0F2F4")
    PALE_ALT = colors.HexColor("#E4E7EA")
    INK = colors.HexColor("#24282D")
    MUTED = colors.HexColor("#69727B")
    WHITE = colors.white

    c = canvas.Canvas(path, pagesize=(W, H), pageCompression=1)
    c.setTitle(f'Rutina {member.get("first_name", "")} {member.get("last_name", "")} | FORJAGYM')
    c.setAuthor("FORJAGYM")

    def clean(v):
        return str(v if v not in (None, "") else "—").replace("\r", " ").replace("\n", " ").strip()

    def lines(v, font, size, width):
        return simpleSplit(clean(v), font, size, width) or ["—"]

    def text_lines(values, x, y, font, size, leading, color=INK):
        c.setFillColor(color)
        c.setFont(font, size)
        for line in values:
            c.drawString(x, y, line)
            y -= leading
        return y

    page_no = 1

    def footer():
        c.setStrokeColor(ORANGE)
        c.setLineWidth(1.1)
        c.line(M, 9*mm, W-M, 9*mm)
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Bold", 6.2)
        c.drawString(M, 5*mm, "FORJAGYM  •  GESTIÓN INTEGRAL PARA GIMNASIOS")
        c.drawRightString(W-M, 5*mm, f"{page_no}")

    def top_brand(continuation=False):
        c.setFillColor(DARK)
        c.rect(0, H-3*mm, W, 3*mm, stroke=0, fill=1)
        if continuation:
            c.setFillColor(ORANGE)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(M, H-13*mm, "PLANIFICACIÓN SEMANAL")
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 7)
            c.drawRightString(W-M, H-13*mm, "CONTINUACIÓN")
            return H-20*mm
        return TOP

    def new_plan_page():
        nonlocal page_no
        footer()
        c.showPage()
        page_no += 1
        return top_brand(True)

    def day_header(y, title, fs=9.2):
        title_lines = lines(title, "Helvetica-Bold", fs, CW-13*mm)
        h = max(8*mm, len(title_lines)*fs*1.22 + 3.5*mm)
        c.setFillColor(GRAPHITE)
        c.roundRect(M, y-h, CW, h, 1.8*mm, stroke=0, fill=1)
        c.setFillColor(ORANGE)
        c.roundRect(M, y-h, 2.4*mm, h, .8*mm, stroke=0, fill=1)
        text_lines(title_lines, M+6*mm, y-4.7*mm, "Helvetica-Bold", fs, fs*1.22, WHITE)
        return y-h-2*mm

    def draw_day(item, y):
        day = item["day"]
        idx = int(day.get("weekday", 0))
        name = DAYS[idx].upper() if 0 <= idx < len(DAYS) else f"DÍA {idx+1}"
        groups = clean(day.get("muscle_groups") or "Grupos musculares")
        y = day_header(y, f"{name}  |  {groups}")

        if day.get("notes"):
            note_lines = lines(day["notes"], "Helvetica", 8.2, CW-29*mm)
            block_h = max(6*mm, len(note_lines)*9.4 + 2.4*mm)
            c.setFillColor(PALE)
            c.roundRect(M, y-block_h, CW, block_h, 1.2*mm, stroke=0, fill=1)
            c.setFillColor(ORANGE)
            c.setFont("Helvetica-Bold", 7.2)
            c.drawString(M+3*mm, y-4.1*mm, "ENFOQUE")
            text_lines(note_lines, M+22*mm, y-4.1*mm, "Helvetica", 8.2, 9.4, INK)
            y -= block_h+2*mm

        # Column proportions are intentionally generous for exercise names and tips.
        widths = [CW*.30, CW*.09, CW*.12, CW*.12, CW*.37]
        headers = ["EJERCICIO", "SER.", "REPS.", "PESO", "NOTAS / TIPS"]
        fs_head, fs_cell, lead = 7.0, 8.0, 9.5

        def draw_table_head(y):
            hh = 7.2*mm
            c.setFillColor(MID)
            c.roundRect(M, y-hh, CW, hh, 1*mm, stroke=0, fill=1)
            x = M
            for label, width in zip(headers, widths):
                c.setFillColor(WHITE)
                c.setFont("Helvetica-Bold", fs_head)
                c.drawString(x+1.5*mm, y-4.6*mm, label)
                x += width
            return y-hh

        y = draw_table_head(y)
        exercises = item.get("exercises", [])
        if not exercises:
            exercises = [{"name": "Sin ejercicios cargados"}]

        for ri, ex in enumerate(exercises):
            values = [ex.get("name"), ex.get("sets"), ex.get("reps"),
                      ex.get("reference_weight"), ex.get("notes")]
            fonts = ["Helvetica-Bold", "Helvetica", "Helvetica", "Helvetica", "Helvetica"]
            wrapped = [lines(v, fonts[i], fs_cell, widths[i]-3.2*mm) for i, v in enumerate(values)]
            max_lines = max(len(v) for v in wrapped)
            rh = max(8.5*mm, max_lines*lead+3.4*mm)

            # A row never crosses the footer. If needed, continue on a fresh page
            # and repeat both the day label and column headings.
            if y-rh < FOOT+2*mm:
                y = new_plan_page()
                y = day_header(y, f"{name}  |  {groups} (CONT.)", fs=8.7)
                y = draw_table_head(y)

            c.setFillColor(PALE if ri % 2 == 0 else PALE_ALT)
            c.roundRect(M, y-rh, CW, rh, 1*mm, stroke=0, fill=1)
            x = M
            for col, (value_lines, width) in enumerate(zip(wrapped, widths)):
                font = fonts[col]
                text_lines(value_lines, x+1.5*mm, y-4.8*mm, font, fs_cell, lead, INK)
                x += width
            y -= rh+1.2*mm

        return y-3.5*mm

    # PAGE 1: brand header and student card. Logo is given its own reserved vertical area.
    y = top_brand(False)
    logo = resource_path("assets/logo_forjagym.png")
    if logo.exists():
        try:
            logo_w, logo_h = 24*mm, 24*mm
            logo_y = y-logo_h
            c.drawImage(str(logo), W/2-logo_w/2, logo_y, width=logo_w, height=logo_h,
                        preserveAspectRatio=True, anchor="c", mask="auto")
            y = logo_y-3.5*mm
        except Exception:
            y -= 2*mm
    else:
        y -= 2*mm

    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(W/2, y, "FORJAGYM")
    y -= 5*mm
    c.setFillColor(GRAPHITE)
    c.setFont("Helvetica-Bold", 7.4)
    c.drawCentredString(W/2, y, "GESTIÓN INTEGRAL PARA GIMNASIOS")
    y -= 4*mm
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Oblique", 7.2)
    c.drawCentredString(W/2, y, "Entrená con método. Gestioná con claridad.")
    y -= 6*mm

    # Student data card with deliberate vertical padding and no text collisions.
    card_h = 27*mm
    c.setFillColor(PALE)
    c.roundRect(M, y-card_h, CW, card_h, 2*mm, stroke=0, fill=1)
    c.setFillColor(GRAPHITE)
    c.roundRect(M, y-7*mm, CW, 7*mm, 1.7*mm, stroke=0, fill=1)
    c.rect(M, y-7*mm, CW, 2*mm, stroke=0, fill=1)
    c.setFillColor(ORANGE)
    c.rect(M, y-7*mm, 2.4*mm, 7*mm, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(M+6*mm, y-4.8*mm, "FICHA DEL ALUMNO")

    info = [
        ("ALUMNO", f'{member.get("first_name", "")} {member.get("last_name", "")}'),
        ("DNI", member.get("dni", "")),
        ("RUTINA", detail["assignment"].get("routine_name", "")),
        ("FECHA DE INICIO", detail["assignment"].get("start_date", "")),
    ]
    colx = [M+4*mm, M+CW/2+2*mm]
    rowy = [y-12*mm, y-20.5*mm]
    for (label, val), x, yy in zip(info, [colx[0],colx[1],colx[0],colx[1]], [rowy[0],rowy[0],rowy[1],rowy[1]]):
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(x, yy, label)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 8.3)
        value_lines = lines(val, "Helvetica-Bold", 8.3, CW/2-8*mm)
        text_lines(value_lines[:1], x, yy-3.8*mm, "Helvetica-Bold", 8.3, 9.5, DARK)
    y -= card_h+5*mm

    # Routine description remains present but compact and separated from the plan.
    description = detail["assignment"].get("routine_description")
    if description:
        c.setFillColor(ORANGE)
        c.setFont("Helvetica-Bold", 8.2)
        c.drawString(M, y, "SOBRE ESTA RUTINA")
        y -= 4.2*mm
        desc_lines = lines(description, "Helvetica", 7.8, CW)
        desc_h = len(desc_lines)*9.3+3*mm
        c.setFillColor(PALE)
        c.roundRect(M, y-desc_h, CW, desc_h, 1.5*mm, stroke=0, fill=1)
        text_lines(desc_lines, M+3*mm, y-4.5*mm, "Helvetica", 7.8, 9.3, INK)
        y -= desc_h+4*mm

    # Plan title
    c.setFillColor(GRAPHITE)
    c.roundRect(M, y-8*mm, CW, 8*mm, 1.5*mm, stroke=0, fill=1)
    c.setFillColor(ORANGE)
    c.rect(M, y-8*mm, 2.4*mm, 8*mm, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(M+6*mm, y-5.3*mm, "PLANIFICACIÓN SEMANAL")
    y -= 11*mm

    for item in detail.get("days", []):
        # Keep a day together whenever it fits on a fresh page; individual rows
        # still have their own overflow protection for unusually large sessions.
        y = draw_day(item, y)

    footer()
    c.showPage()

    # FINAL PAGE: larger typography and four visually separated advice cards.
    page_no += 1
    c.setFillColor(DARK)
    c.rect(0, H-3*mm, W, 3*mm, stroke=0, fill=1)
    y = TOP
    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(M, y-5*mm, "GUÍA PARA ENTRENAR")
    c.setFillColor(GRAPHITE)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(M, y-13*mm, "Y PROGRESAR")
    y -= 21*mm

    intro = "La rutina es una guía de trabajo. La prioridad es ejecutar cada repetición con control y sostener el progreso semana a semana."
    intro_lines = lines(intro, "Helvetica", 8.8, CW)
    y = text_lines(intro_lines, M, y, "Helvetica", 8.8, 11, MUTED)-5*mm

    advice_cards = [
        ("01", "INTENSIDAD Y REPETICIONES EN RECÁMARA", [
            ("EJERCICIOS COMPUESTOS", "Terminá normalmente con 1 a 3 repeticiones en reserva. No hace falta llegar al fallo en todas las series."),
            ("EJERCICIOS DE AISLAMIENTO", "Podés acercarte a 0–2 repeticiones en reserva si mantenés la técnica y no aparece dolor."),
        ]),
        ("02", "CÓMO PROGRESAR", [
            ("PROGRESIÓN DE CARGA", "Cuando completes el máximo del rango de repeticiones en todas las series con buena técnica, aumentá un poco la carga en la próxima sesión."),
            ("SI LA TÉCNICA SE DETERIORA", "Si no llegás al mínimo del rango o la técnica se deteriora, mantené el peso o reducí la carga. No sacrifiques ejecución para levantar más."),
        ]),
        ("03", "TÉCNICA Y CONTROL", [
            ("EJECUCIÓN", "Realizá cada repetición con recorrido controlado. Evitá impulsos innecesarios y respetá la postura indicada para cada ejercicio."),
            ("SEÑALES DE ALERTA", "Si aparece dolor agudo, mareo o una molestia fuera de lo habitual, detené el ejercicio y consultá al profesional a cargo."),
        ]),
        ("04", "REGISTRO Y CONSTANCIA", [
            ("REGISTRÁ TUS RESULTADOS", "Anotá las cargas y repeticiones realizadas. Comparar esos datos te permite comprobar si estás progresando y ajustar el entrenamiento con criterio."),
            ("RECUPERACIÓN", "La recuperación, el descanso y la constancia también forman parte del entrenamiento. No busques terminar destruido: buscá acumular buenas sesiones."),
        ]),
    ]

    for num, title, entries in advice_cards:
        card_top = y
        # Measure the card first, using 8.4pt copy and a generous line height.
        measured = 9*mm
        prepared = []
        for label, copy in entries:
            label_lines = lines(label, "Helvetica-Bold", 7.2, CW-12*mm)
            copy_lines = lines(copy, "Helvetica", 8.4, CW-12*mm)
            prepared.append((label_lines, copy_lines))
            measured += len(label_lines)*8.5 + len(copy_lines)*10.8 + 3.2*mm
        measured += 2*mm

        if card_top-measured < FOOT+3*mm:
            footer()
            c.showPage()
            page_no += 1
            y = top_brand(True)
            card_top = y

        c.setFillColor(PALE)
        c.roundRect(M, card_top-measured, CW, measured, 2*mm, stroke=0, fill=1)
        c.setFillColor(GRAPHITE)
        c.roundRect(M, card_top-8*mm, CW, 8*mm, 1.8*mm, stroke=0, fill=1)
        c.setFillColor(ORANGE)
        c.roundRect(M, card_top-8*mm, 9*mm, 8*mm, 1.5*mm, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawCentredString(M+4.5*mm, card_top-5.5*mm, num)
        c.setFont("Helvetica-Bold", 7.4)
        c.drawString(M+12*mm, card_top-5.5*mm, title)

        yy = card_top-12*mm
        for label_lines, copy_lines in prepared:
            yy = text_lines(label_lines, M+4*mm, yy, "Helvetica-Bold", 7.2, 8.5, ORANGE)
            yy = text_lines(copy_lines, M+4*mm, yy-0.7*mm, "Helvetica", 8.4, 10.8, INK)-2.5*mm
        y = card_top-measured-3*mm

    # Brand closing panel
    close_h = 9*mm
    # Cierre compacto para que la guía permanezca en una sola página.
    if y-close_h < FOOT+1*mm:
        # Si la rutina de consejos ocupa excepcionalmente más espacio,
        # se integra el lema en el pie institucional en vez de crear una página casi vacía.
        close_h = 0
    if close_h:
        c.setFillColor(DARK)
    if close_h:
        c.roundRect(M, y-close_h, CW, close_h, 2*mm, stroke=0, fill=1)
        c.setFillColor(ORANGE)
        c.rect(M, y-close_h, CW, 1.2*mm, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(W/2, y-3.8*mm, "COMUNIDAD FORJAGYM  •  Entrená con método. Gestioná con claridad.")

    footer()
    c.save()


RutinasSociosWindow._create_pdf = _create_pdf_mobile_legible


def _create_pdf_mobile_final(self, path, member, detail):
    """Genera planificación mobile-first y páginas finales con guía y datos de la rutina."""
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.utils import simpleSplit
    import re

    W, H = 148*mm, 240*mm
    M = 7*mm
    CW = W-2*M
    FOOT = 13*mm
    TOP = H-8*mm

    ORANGE = colors.HexColor("#FF6500")
    GRAPHITE = colors.HexColor("#202429")
    DARK = colors.HexColor("#111315")
    MID = colors.HexColor("#3B4249")
    PALE = colors.HexColor("#F0F2F4")
    ALT = colors.HexColor("#E4E7EA")
    INK = colors.HexColor("#22272C")
    MUTED = colors.HexColor("#68717A")
    WHITE = colors.white

    c = canvas.Canvas(path, pagesize=(W,H), pageCompression=1)
    c.setTitle(f'Rutina {member.get("first_name","")} {member.get("last_name","")} | FORJAGYM')
    c.setAuthor("FORJAGYM")

    def clean(v):
        return str(v if v not in (None,"") else "—").replace("\r"," ").strip()

    def wrap(v, font, size, width):
        return simpleSplit(clean(v), font, size, width) or ["—"]

    def draw_lines(lines, x, y, font, size, leading, color=INK):
        c.setFillColor(color); c.setFont(font,size)
        for line in lines:
            c.drawString(x,y,line)
            y -= leading
        return y

    page_no = 1
    def footer():
        c.setStrokeColor(ORANGE); c.setLineWidth(1.1)
        c.line(M,9*mm,W-M,9*mm)
        c.setFillColor(MUTED); c.setFont("Helvetica-Bold",6.2)
        c.drawString(M,5*mm,"FORJAGYM  •  GESTIÓN INTEGRAL PARA GIMNASIOS")
        c.drawRightString(W-M,5*mm,str(page_no))

    def finish_page():
        nonlocal page_no
        footer()
        c.showPage()
        page_no += 1

    def continuation_header(label="PLANIFICACIÓN SEMANAL"):
        c.setFillColor(DARK); c.rect(0,H-3*mm,W,3*mm,stroke=0,fill=1)
        c.setFillColor(ORANGE); c.setFont("Helvetica-Bold",10)
        c.drawString(M,H-13*mm,label)
        c.setFillColor(MUTED); c.setFont("Helvetica",7)
        c.drawRightString(W-M,H-13*mm,"FORJAGYM")
        return H-20*mm

    # ── PORTADA + FICHA ─────────────────────────────────────────────────
    c.setFillColor(DARK); c.rect(0,H-3*mm,W,3*mm,stroke=0,fill=1)
    y = TOP
    logo = resource_path("assets/logo_forjagym.png")
    if logo.exists():
        try:
            lw, lh = 19*mm, 19*mm
            c.drawImage(str(logo),W/2-lw/2,y-lh,width=lw,height=lh,
                        preserveAspectRatio=True,anchor="c",mask="auto")
            y -= lh+4.5*mm
        except Exception:
            y -= 3*mm
    else:
        y -= 3*mm

    c.setFillColor(ORANGE); c.setFont("Helvetica-Bold",18)
    c.drawCentredString(W/2,y,"FORJAGYM"); y -= 5*mm
    c.setFillColor(GRAPHITE); c.setFont("Helvetica-Bold",7.8)
    c.drawCentredString(W/2,y,"GESTIÓN INTEGRAL PARA GIMNASIOS"); y -= 4.2*mm
    c.setFillColor(MUTED); c.setFont("Helvetica-Oblique",7.5)
    c.drawCentredString(W/2,y,"Entrená con método. Gestioná con claridad.")
    y -= 6*mm

    card_h = 26*mm
    c.setFillColor(PALE); c.roundRect(M,y-card_h,CW,card_h,2*mm,stroke=0,fill=1)
    c.setFillColor(GRAPHITE); c.roundRect(M,y-7*mm,CW,7*mm,1.6*mm,stroke=0,fill=1)
    c.rect(M,y-7*mm,CW,2*mm,stroke=0,fill=1)
    c.setFillColor(ORANGE); c.rect(M,y-7*mm,2.4*mm,7*mm,stroke=0,fill=1)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8.3)
    c.drawString(M+6*mm,y-4.8*mm,"FICHA DEL ALUMNO")

    fields = [
        ("ALUMNO",f'{member.get("first_name","")} {member.get("last_name","")}'),
        ("DNI",member.get("dni","")),
        ("RUTINA",detail["assignment"].get("routine_name","")),
        ("FECHA DE INICIO",detail["assignment"].get("start_date","")),
    ]
    xs=[M+4*mm,M+CW/2+2*mm,M+4*mm,M+CW/2+2*mm]
    ys=[y-12*mm,y-12*mm,y-20*mm,y-20*mm]
    for (lab,val),x,yy in zip(fields,xs,ys):
        c.setFillColor(MUTED); c.setFont("Helvetica-Bold",6.8)
        c.drawString(x,yy,lab)
        value_lines=wrap(val,"Helvetica-Bold",8.5,CW/2-8*mm)
        draw_lines(value_lines[:1],x,yy-4*mm,"Helvetica-Bold",8.5,10,INK)
    y -= card_h+5*mm

    # Immediately start the weekly plan; "Sobre esta rutina" is intentionally moved later.
    def plan_title(y):
        h=8*mm
        c.setFillColor(GRAPHITE); c.roundRect(M,y-h,CW,h,1.5*mm,stroke=0,fill=1)
        c.setFillColor(ORANGE); c.rect(M,y-h,2.4*mm,h,stroke=0,fill=1)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",9.5)
        c.drawString(M+6*mm,y-5.3*mm,"PLANIFICACIÓN SEMANAL")
        return y-h-3*mm
    y=plan_title(y)

    # ── DAY CARDS: larger text, wider SERIES column, safe pagination ────
    widths=[CW*.285,CW*.145,CW*.12,CW*.115,CW*.335]
    headers=["EJERCICIO","SERIES","REPS.","PESO","NOTAS / TIPS"]
    fs_cell=9.0
    lead=11.0
    fs_head=7.1

    def day_data(item):
        day=item["day"]
        idx=int(day.get("weekday",0))
        dayname=DAYS[idx].upper() if 0<=idx<len(DAYS) else f"DÍA {idx+1}"
        groups=clean(day.get("muscle_groups") or "Grupos musculares")
        title=f"{dayname}  |  {groups}"
        focus=clean(day.get("notes")) if day.get("notes") else ""
        exercises=item.get("exercises",[]) or [{"name":"Sin ejercicios cargados"}]
        return dayname,groups,title,focus,exercises

    def measure_day(item):
        dayname,groups,title,focus,exercises=day_data(item)
        title_lines=wrap(title,"Helvetica-Bold",9.5,CW-13*mm)
        h=max(8.5*mm,len(title_lines)*12+9)
        total=h+3*mm
        if focus:
            focus_lines=wrap(focus,"Helvetica",9.0,CW-29*mm)
            focus_h=max(23, len(focus_lines)*11.5+12)
            total += focus_h+3*mm
        total += 8*mm+2*mm # table header and gap
        for ex in exercises:
            vals=[ex.get("name"),ex.get("sets"),ex.get("reps"),ex.get("reference_weight"),ex.get("notes")]
            fnts=["Helvetica-Bold","Helvetica","Helvetica","Helvetica","Helvetica"]
            wrapped=[wrap(v,fnts[i],fs_cell,widths[i]-3.5*mm) for i,v in enumerate(vals)]
            n=max(map(len,wrapped))
            total += max(10*mm,n*lead+8)+2
        return total+3*mm

    def draw_day(item,y):
        dayname,groups,title,focus,exercises=day_data(item)
        title_lines=wrap(title,"Helvetica-Bold",9.5,CW-13*mm)
        hh=max(8.5*mm,len(title_lines)*12+9)
        c.setFillColor(GRAPHITE); c.roundRect(M,y-hh,CW,hh,1.8*mm,stroke=0,fill=1)
        c.setFillColor(ORANGE); c.roundRect(M,y-hh,2.5*mm,hh,.8*mm,stroke=0,fill=1)
        draw_lines(title_lines,M+6*mm,y-5*mm,"Helvetica-Bold",9.5,12,WHITE)
        y -= hh+2.5*mm

        if focus:
            f_lines=wrap(focus,"Helvetica",9.0,CW-29*mm)
            fh=max(23,len(f_lines)*11.5+12)
            c.setFillColor(PALE); c.roundRect(M,y-fh,CW,fh,1.4*mm,stroke=0,fill=1)
            c.setFillColor(ORANGE); c.setFont("Helvetica-Bold",7.2)
            c.drawString(M+3*mm,y-9.5,"ENFOQUE")
            draw_lines(f_lines,M+22*mm,y-9.5,"Helvetica-Bold",9.0,11.5,INK)
            y -= fh+3*mm

        def table_head(y):
            th=8*mm
            c.setFillColor(MID); c.roundRect(M,y-th,CW,th,1*mm,stroke=0,fill=1)
            x=M
            for lab,w in zip(headers,widths):
                c.setFillColor(WHITE); c.setFont("Helvetica-Bold",fs_head)
                c.drawString(x+1.4*mm,y-5.1*mm,lab)
                x += w
            return y-th
        y=table_head(y)
        for ri,ex in enumerate(exercises):
            vals=[ex.get("name"),ex.get("sets"),ex.get("reps"),ex.get("reference_weight"),ex.get("notes")]
            fonts=["Helvetica-Bold","Helvetica-Bold","Helvetica","Helvetica","Helvetica"]
            wlines=[wrap(v,fonts[i],fs_cell,widths[i]-3.5*mm) for i,v in enumerate(vals)]
            n=max(map(len,wlines))
            rh=max(10*mm,n*lead+8)
            if y-rh < FOOT+2*mm:
                # Close the page cleanly and continue the same day on a fresh page.
                finish_page()
                y=continuation_header()
                y=draw_day_continuation(dayname,groups,y)
                y=table_head(y)
            c.setFillColor(PALE if ri%2==0 else ALT)
            c.roundRect(M,y-rh,CW,rh,1*mm,stroke=0,fill=1)
            x=M
            for col,(ls,w) in enumerate(zip(wlines,widths)):
                draw_lines(ls,x+1.5*mm,y-5.2*mm,fonts[col],fs_cell,lead,INK)
                x += w
            y -= rh+2*mm
        return y-4*mm

    def draw_day_continuation(dayname,groups,y):
        title=f"{dayname}  |  {groups} (CONTINUACIÓN)"
        ls=wrap(title,"Helvetica-Bold",9.0,CW-13*mm)
        hh=max(8*mm,len(ls)*11+8)
        c.setFillColor(GRAPHITE); c.roundRect(M,y-hh,CW,hh,1.6*mm,stroke=0,fill=1)
        c.setFillColor(ORANGE); c.roundRect(M,y-hh,2.5*mm,hh,.8*mm,stroke=0,fill=1)
        draw_lines(ls,M+6*mm,y-4.8*mm,"Helvetica-Bold",9.0,11,WHITE)
        return y-hh-2*mm

    for item in detail.get("days",[]):
        needed=measure_day(item)
        if y-needed < FOOT+2*mm:
            finish_page()
            y=continuation_header()
        y=draw_day(item,y)

    finish_page()

    # ── FINAL INFORMATION PAGES: routine-specific notes + progression guide ──
    y=continuation_header("SOBRE ESTA RUTINA")

    def section_heading(y,title):
        h=8*mm
        c.setFillColor(GRAPHITE); c.roundRect(M,y-h,CW,h,1.5*mm,stroke=0,fill=1)
        c.setFillColor(ORANGE); c.rect(M,y-h,2.4*mm,h,stroke=0,fill=1)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",9)
        c.drawString(M+6*mm,y-5.2*mm,title)
        return y-h-3*mm

    def info_card(y,label,body,accent=True):
        lab_lines=wrap(label,"Helvetica-Bold",8.0,CW-10*mm)
        body_lines=wrap(body,"Helvetica",9.0,CW-10*mm)
        h=5*mm+len(lab_lines)*10+len(body_lines)*11.5+5*mm
        c.setFillColor(PALE); c.roundRect(M,y-h,CW,h,1.8*mm,stroke=0,fill=1)
        c.setFillColor(ORANGE if accent else MID)
        c.roundRect(M,y-h,2*mm,h,.7*mm,stroke=0,fill=1)
        yy=y-5*mm
        yy=draw_lines(lab_lines,M+5*mm,yy,"Helvetica-Bold",8.0,10,ORANGE if accent else GRAPHITE)
        draw_lines(body_lines,M+5*mm,yy-1.5*mm,"Helvetica",9.0,11.5,INK)
        return y-h-3*mm

    # Parse routine description into real, readable cards.
    # Bullet symbols and line breaks are separators; empty sections are discarded.
    raw = str(detail["assignment"].get("routine_description") or "")
    raw = raw.replace("\r", "\n").replace("\u2022", "\n").replace("\u25AA", "\n").replace("\u25CF", "\n")
    raw = re.sub(r"(?i)(?<!\w)(CÓMO\s+PROGRESAR|PRIORIDADES\s+DEL\s+BLOQUE|DURACIÓN\s+INICIAL|LA\s+CLAVE)\b", r"\n\1", raw)
    raw_lines = []
    for part in raw.splitlines():
        part = re.sub(r"\s+", " ", part).strip(" \t-▪●•*")
        if part:
            raw_lines.append(part)

    desc_sections = []
    general_items = []
    progress_items = []
    priority_items = []
    duration_items = []
    mode = "general"

    def flush_general():
        if general_items:
            desc_sections.append(("INDICACIONES GENERALES", list(general_items)))
            general_items.clear()

    def flush_progress():
        if progress_items:
            desc_sections.append(("CÓMO PROGRESAR", list(progress_items)))
            progress_items.clear()

    def flush_priorities():
        if priority_items:
            desc_sections.append(("PRIORIDADES DEL BLOQUE", list(priority_items)))
            priority_items.clear()

    def flush_duration():
        if duration_items:
            desc_sections.append(("DURACIÓN Y CONSTANCIA", list(duration_items)))
            duration_items.clear()

    def add_priority_text(value):
        chunks = re.split(r"(?=(?:^|\s)\d+\.\s*)", value.strip())
        for chunk in chunks:
            chunk = re.sub(r"^\s*\d+\.\s*", "", chunk).strip()
            if chunk:
                priority_items.append(chunk)

    for line in raw_lines:
        upper = line.upper().strip(": ")
        if upper.startswith("CÓMO PROGRESAR"):
            flush_general()
            flush_progress()
            mode = "progress"
            remainder = re.sub(r"(?i)^CÓMO\s+PROGRESAR\s*[:\-]?\s*", "", line).strip()
            if remainder:
                progress_items.append(remainder)
        elif upper.startswith("PRIORIDADES DEL BLOQUE"):
            flush_general()
            flush_progress()
            flush_priorities()
            mode = "priorities"
            remainder = re.sub(r"(?i)^PRIORIDADES\s+DEL\s+BLOQUE\s*[:\-]?\s*", "", line).strip()
            if remainder:
                add_priority_text(remainder)
        elif upper.startswith("DURACIÓN INICIAL") or upper.startswith("LA CLAVE"):
            flush_general()
            flush_progress()
            flush_priorities()
            mode = "duration"
            duration_items.append(line)
        elif re.match(r"^\d+\.\s*", line):
            if mode != "priorities":
                flush_general()
                flush_progress()
                mode = "priorities"
            add_priority_text(line)
        else:
            if mode == "progress":
                progress_items.append(line)
            elif mode == "priorities":
                add_priority_text(line)
            elif mode == "duration":
                duration_items.append(line)
            else:
                general_items.append(line)

    flush_general()
    flush_progress()
    flush_priorities()
    flush_duration()

    # Render each item on its own line with a bullet and comfortable vertical spacing.
    def bullet_card(y, label, items, accent=True):
        items = [str(item).strip() for item in items if str(item).strip()]
        if not items:
            return y
        label_lines = wrap(label, "Helvetica-Bold", 8.0, CW-10*mm)
        prepared = [wrap(item, "Helvetica", 9.0, CW-14*mm) for item in items]
        body_height = sum(max(1, len(lines))*11.8 + 2.2 for lines in prepared)
        card_h = 5*mm + len(label_lines)*10 + body_height + 4*mm
        if y-card_h < FOOT+3*mm:
            finish_page()
            y = continuation_header("SOBRE ESTA RUTINA")
        c.setFillColor(PALE)
        c.roundRect(M, y-card_h, CW, card_h, 1.8*mm, stroke=0, fill=1)
        c.setFillColor(ORANGE if accent else MID)
        c.roundRect(M, y-card_h, 2*mm, card_h, .7*mm, stroke=0, fill=1)
        yy = y-5*mm
        yy = draw_lines(label_lines, M+5*mm, yy, "Helvetica-Bold", 8.0, 10, ORANGE if accent else GRAPHITE)
        yy -= 1.8*mm
        for item_lines in prepared:
            c.setFillColor(ORANGE)
            c.circle(M+6.2*mm, yy+1.3, 1.05, stroke=0, fill=1)
            yy = draw_lines(item_lines, M+9*mm, yy, "Helvetica", 9.0, 11.8, INK)
            yy -= 2.2
        return y-card_h-3*mm

    y = section_heading(y, "DETALLES DEL BLOQUE")
    for label, items in desc_sections:
        # Empty general-information cards are intentionally omitted.
        if label == "INDICACIONES GENERALES" and not any(str(x).strip() for x in items):
            continue
        y = bullet_card(y, label, items)

    # Progression guide gets a distinct visual section after routine-specific notes.
    if y-15*mm < FOOT+3*mm:
        finish_page()
        y=continuation_header("GUÍA PARA ENTRENAR Y PROGRESAR")
    else:
        y=section_heading(y,"GUÍA PARA ENTRENAR Y PROGRESAR")

    intro="La rutina es una guía de trabajo. La prioridad es ejecutar cada repetición con control y sostener el progreso semana a semana."
    if y-25*mm < FOOT+3*mm:
        finish_page(); y=continuation_header("GUÍA PARA ENTRENAR Y PROGRESAR")
    y=info_card(y,"OBJETIVO","La prioridad es entrenar con control, sostener el progreso semana a semana y acumular sesiones de calidad.",False)

    advice=[
        ("01  INTENSIDAD Y REPETICIONES EN RECÁMARA",[
            ("EJERCICIOS COMPUESTOS","Terminá normalmente con 1 a 3 repeticiones en reserva. No hace falta llegar al fallo en todas las series."),
            ("EJERCICIOS DE AISLAMIENTO","Podés acercarte a 0–2 repeticiones en reserva si mantenés la técnica y no aparece dolor.")]),
        ("02  CÓMO PROGRESAR",[
            ("PROGRESIÓN DE CARGA","Cuando completes el máximo del rango de repeticiones en todas las series con buena técnica, aumentá un poco la carga en la próxima sesión."),
            ("SI LA TÉCNICA SE DETERIORA","Si no llegás al mínimo del rango o la técnica se deteriora, mantené el peso o reducí la carga. No sacrifiques ejecución para levantar más.")]),
        ("03  TÉCNICA Y CONTROL",[
            ("EJECUCIÓN","Realizá cada repetición con recorrido controlado. Evitá impulsos innecesarios y respetá la postura indicada para cada ejercicio."),
            ("SEÑALES DE ALERTA","Si aparece dolor agudo, mareo o una molestia fuera de lo habitual, detené el ejercicio y consultá al profesional a cargo.")]),
        ("04  REGISTRO Y CONSTANCIA",[
            ("REGISTRÁ TUS RESULTADOS","Anotá las cargas y repeticiones realizadas. Comparar esos datos te permite comprobar si estás progresando y ajustar el entrenamiento con criterio."),
            ("RECUPERACIÓN","La recuperación, el descanso y la constancia también forman parte del entrenamiento. No busques terminar destruido: buscá acumular buenas sesiones.")])
    ]

    for title,entries in advice:
        # One complete card per advice topic; if it does not fit, continue page.
        prepared=[]
        h=9*mm
        for label,body in entries:
            ll=wrap(label,"Helvetica-Bold",7.7,CW-12*mm)
            bl=wrap(body,"Helvetica",9.0,CW-12*mm)
            prepared.append((ll,bl))
            h += len(ll)*10+len(bl)*11.5+4*mm
        if y-h < FOOT+3*mm:
            finish_page()
            y=continuation_header("GUÍA PARA ENTRENAR Y PROGRESAR")
        c.setFillColor(PALE); c.roundRect(M,y-h,CW,h,1.8*mm,stroke=0,fill=1)
        c.setFillColor(GRAPHITE); c.roundRect(M,y-8*mm,CW,8*mm,1.5*mm,stroke=0,fill=1)
        c.setFillColor(ORANGE); c.roundRect(M,y-8*mm,9*mm,8*mm,1.4*mm,stroke=0,fill=1)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7.8)
        c.drawCentredString(M+4.5*mm,y-5.2*mm,title[:2])
        c.setFont("Helvetica-Bold",7.5)
        c.drawString(M+12*mm,y-5.2*mm,title[4:])
        yy=y-13*mm
        for ll,bl in prepared:
            yy=draw_lines(ll,M+4*mm,yy,"Helvetica-Bold",7.7,10,ORANGE)
            yy=draw_lines(bl,M+4*mm,yy-1.2*mm,"Helvetica",9.0,11.5,INK)-3*mm
        y -= h+3*mm

    # Branded close-out; keep on the current page only if safely above footer.
    if y-10*mm < FOOT+2*mm:
        finish_page()
        y=continuation_header("COMUNIDAD FORJAGYM")
    c.setFillColor(DARK); c.roundRect(M,y-9*mm,CW,9*mm,1.7*mm,stroke=0,fill=1)
    c.setFillColor(ORANGE); c.rect(M,y-1.4*mm,CW,1.4*mm,stroke=0,fill=1)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
    c.drawCentredString(W/2,y-5.7*mm,"COMUNIDAD FORJAGYM  •  Entrená con método. Gestioná con claridad.")

    footer()
    c.save()


RutinasSociosWindow._create_pdf = _create_pdf_mobile_final



class RoutineViewerWindow(ctk.CTkToplevel):
    """Visor interno de la copia individual de rutina asignada a un socio."""

    def __init__(self, parent, member, detail):
        super().__init__(parent)
        self.member = member
        self.detail = detail
        self.days_by_weekday = {
            item["day"]["weekday"]: item for item in detail.get("days", [])
        }
        self.title("FORJAGYM | Consulta de rutina")
        self.geometry("1040x760")
        self.minsize(820, 600)
        self.configure(fg_color=BACKGROUND)
        self.transient(parent)
        self.grab_set()
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        assignment = self.detail["assignment"]
        header = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header, text="CONSULTA DE RUTINA", text_color=ORANGE,
            font=("Arial", 23, "bold")
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 3))
        ctk.CTkLabel(
            header,
            text=f'{self.member["first_name"]} {self.member["last_name"]}  |  DNI {self.member["dni"]}',
            text_color=TEXT, font=("Arial", 14, "bold")
        ).grid(row=1, column=0, sticky="w", padx=18, pady=2)
        ctk.CTkLabel(
            header,
            text=f'Rutina: {assignment["routine_name"]}  •  Desde: {assignment["start_date"]}',
            text_color=SECONDARY, font=("Arial", 11)
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(2, 14))

        self.tabs = ctk.CTkTabview(
            self, fg_color=CARD, segmented_button_fg_color="#30363D",
            segmented_button_selected_color=ORANGE,
            segmented_button_selected_hover_color="#D95700",
            segmented_button_unselected_color="#30363D",
            segmented_button_unselected_hover_color="#454C54"
        )
        self.tabs.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 12))
        self.tabs.add("HOY")
        self._build_today_tab(self.tabs.tab("HOY"))

        weekdays = sorted(self.days_by_weekday)
        if weekdays:
            self.tabs.add("SEMANA")
            self._build_week_tab(self.tabs.tab("SEMANA"), weekdays)
            for weekday in weekdays:
                tab_name = DAYS[weekday].upper()
                self.tabs.add(tab_name)
                self._render_day(self.tabs.tab(tab_name), self.days_by_weekday[weekday])

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 16))
        ctk.CTkButton(
            footer, text="CERRAR", width=130, fg_color="#343A40",
            hover_color="#4A5159", command=self.destroy
        ).pack(side="right")

    def _build_today_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        today = date.today()
        ctk.CTkLabel(
            parent, text=f"ENTRENAMIENTO DE HOY  •  {DAYS[today.weekday()].upper()} {today.strftime('%d/%m/%Y')}",
            text_color=ORANGE, font=("Arial", 16, "bold")
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))
        item = self.days_by_weekday.get(today.weekday())
        if item:
            self._render_day(parent, item, row=1)
        else:
            empty = ctk.CTkFrame(parent, fg_color="#171A1E", corner_radius=10)
            empty.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
            ctk.CTkLabel(
                empty, text="HOY NO TIENE ENTRENAMIENTO ASIGNADO",
                text_color=ORANGE, font=("Arial", 17, "bold")
            ).pack(pady=(35, 8), padx=18)
            ctk.CTkLabel(
                empty, text="Este día figura como descanso en la planificación semanal.",
                text_color=SECONDARY, font=("Arial", 12)
            ).pack(pady=(0, 35), padx=18)

    def _build_week_tab(self, parent, weekdays):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            parent, text="RESUMEN SEMANAL", text_color=ORANGE,
            font=("Arial", 16, "bold")
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))
        scroll = ctk.CTkScrollableFrame(parent, fg_color="#171A1E", corner_radius=10)
        scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        scroll.grid_columnconfigure(0, weight=1)
        for weekday in weekdays:
            item = self.days_by_weekday[weekday]
            day = item["day"]
            groups = (day.get("muscle_groups") or "Sin grupo muscular especificado").strip()
            card = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=9)
            card.pack(fill="x", padx=7, pady=6)
            ctk.CTkLabel(
                card, text=f'{DAYS[weekday].upper()}  •  {groups}',
                text_color=ORANGE, font=("Arial", 13, "bold"), anchor="w"
            ).pack(fill="x", padx=12, pady=(10, 4))
            exercises = item.get("exercises", [])
            summary = "   |   ".join(
                f'{ex.get("name", "Ejercicio")} ({ex.get("sets", "-")} x {ex.get("reps", "-")})'
                for ex in exercises
            ) if exercises else "Sin ejercicios cargados"
            ctk.CTkLabel(
                card, text=summary, text_color=TEXT, font=("Arial", 11),
                anchor="w", justify="left", wraplength=820
            ).pack(fill="x", padx=12, pady=(0, 10))

    def _render_day(self, parent, item, row=0):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(row, weight=1)
        scroll = ctk.CTkScrollableFrame(parent, fg_color="#171A1E", corner_radius=10)
        scroll.grid(row=row, column=0, sticky="nsew", padx=10, pady=10)
        scroll.grid_columnconfigure(0, weight=1)
        day = item["day"]
        weekday = day["weekday"]
        groups = (day.get("muscle_groups") or "Sin grupos especificados").strip()
        title = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=9)
        title.pack(fill="x", padx=6, pady=(6, 10))
        ctk.CTkLabel(
            title, text=f'{DAYS[weekday].upper()}  •  {groups}',
            text_color=ORANGE, font=("Arial", 16, "bold"), anchor="w"
        ).pack(fill="x", padx=14, pady=(12, 5))
        day_notes = (day.get("notes") or "").strip()
        if day_notes:
            ctk.CTkLabel(
                title, text=f"NOTAS DEL DÍA: {day_notes}", text_color=SECONDARY,
                font=("Arial", 11), anchor="w", justify="left", wraplength=850
            ).pack(fill="x", padx=14, pady=(0, 12))
        else:
            ctk.CTkLabel(title, text="", height=5).pack()

        exercises = item.get("exercises", [])
        if not exercises:
            ctk.CTkLabel(
                scroll, text="No hay ejercicios cargados para este día.",
                text_color=SECONDARY, font=("Arial", 12)
            ).pack(pady=20)
            return

        for index, exercise in enumerate(exercises, start=1):
            card = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=9)
            card.pack(fill="x", padx=6, pady=5)
            ctk.CTkLabel(
                card, text=f'{index:02d}  |  {exercise.get("name") or "Ejercicio sin nombre"}',
                text_color=TEXT, font=("Arial", 13, "bold"), anchor="w"
            ).pack(fill="x", padx=13, pady=(10, 5))
            metrics = ctk.CTkFrame(card, fg_color="transparent")
            metrics.pack(fill="x", padx=10, pady=(0, 5))
            values = [
                ("SERIES", exercise.get("sets")),
                ("REPETICIONES", exercise.get("reps")),
                ("PESO", exercise.get("reference_weight")),
            ]
            for col, (label, value) in enumerate(values):
                metrics.grid_columnconfigure(col, weight=1)
                cell = ctk.CTkFrame(metrics, fg_color="#30363D", corner_radius=7)
                cell.grid(row=0, column=col, sticky="ew", padx=3, pady=2)
                ctk.CTkLabel(
                    cell, text=label, text_color=SECONDARY, font=("Arial", 9, "bold")
                ).pack(pady=(6, 1))
                ctk.CTkLabel(
                    cell, text=(str(value).strip() if value not in (None, "") else "—"),
                    text_color=TEXT, font=("Arial", 12, "bold")
                ).pack(pady=(0, 6))
            notes = (exercise.get("notes") or "").strip()
            if notes:
                ctk.CTkLabel(
                    card, text=f"NOTA TÉCNICA: {notes}", text_color=SECONDARY,
                    font=("Arial", 10), anchor="w", justify="left", wraplength=850
                ).pack(fill="x", padx=13, pady=(0, 10))
            else:
                ctk.CTkLabel(card, text="", height=4).pack()
