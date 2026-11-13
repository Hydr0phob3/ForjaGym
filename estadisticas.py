import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import date, timedelta
from pathlib import Path
import sys
from PIL import Image

ORANGE = "#FF6600"
BACKGROUND = "#111315"
CARD = "#202429"
TEXT = "#FFFFFF"
SECONDARY = "#A0A5AB"


def resource_path(relative_path):
    """Resuelve recursos en desarrollo y en ejecutables PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative_path


class EstadisticasWindow(ctk.CTkToplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        self.title("FORJAGYM | Estadísticas y reportes")
        self.geometry("1180x790")
        self.minsize(1000, 680)
        self.configure(fg_color=BACKGROUND)
        self.data = None
        self._chart_canvases = []
        self.period_var = ctk.StringVar(value="Este mes")
        self.inactive_var = ctk.StringVar(value="14")
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self, fg_color="#191C20", corner_radius=14,
                              border_width=1, border_color="#41474E")
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(16, 10))
        header.grid_columnconfigure(1, weight=1)
        logo_path = resource_path("assets/logo_forjagym.png")
        self.logo_image = ctk.CTkImage(
            light_image=Image.open(logo_path), dark_image=Image.open(logo_path),
            size=(66, 66)
        )
        ctk.CTkLabel(header, text="", image=self.logo_image).grid(
            row=0, column=0, rowspan=2, padx=(12, 14), pady=6
        )
        ctk.CTkLabel(
            header, text="ESTADÍSTICAS Y REPORTES",
            font=("Segoe UI Black", 22, "bold"), text_color=TEXT
        ).grid(row=0, column=1, sticky="sw", pady=(10, 0))
        ctk.CTkLabel(
            header, text="GESTIÓN INTEGRAL PARA GIMNASIOS",
            font=("Segoe UI", 9, "bold"), text_color=ORANGE
        ).grid(row=1, column=1, sticky="nw", pady=(0, 10))
        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.grid(row=0, column=2, rowspan=2, sticky="e", padx=12)
        ctk.CTkLabel(controls, text="Período", text_color=SECONDARY).pack(side="left", padx=(0, 6))
        ctk.CTkOptionMenu(controls, values=["Este mes", "Últimos 30 días", "Últimos 12 meses"], variable=self.period_var, width=150, command=lambda _v: self.refresh_data()).pack(side="left", padx=5)
        ctk.CTkLabel(controls, text="Inactividad", text_color=SECONDARY).pack(side="left", padx=(12, 5))
        ctk.CTkOptionMenu(controls, values=["7", "14", "30"], variable=self.inactive_var, width=75, command=lambda _v: self.refresh_data()).pack(side="left", padx=5)
        ctk.CTkButton(controls, text="Actualizar", fg_color=ORANGE, hover_color="#D95700", command=self.refresh_data, width=105).pack(side="left", padx=(8, 0))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.scroll.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.cards = {}
        card_specs = [("visits", "ASISTENCIAS DEL PERÍODO"), ("current_members", "SOCIOS CON CUOTA VIGENTE"), ("expired_members", "SOCIOS VENCIDOS"), ("income", "INGRESOS DEL PERÍODO")]
        for col, (key, title) in enumerate(card_specs):
            card = ctk.CTkFrame(
                self.scroll, fg_color=CARD, corner_radius=14, height=112,
                border_width=1, border_color="#303840"
            )
            card.grid(row=0, column=col, sticky="ew", padx=5, pady=5)
            card.grid_propagate(False)
            ctk.CTkLabel(card, text=title, text_color=SECONDARY, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(16, 5))
            val = ctk.CTkLabel(card, text="—", text_color=ORANGE, font=("Segoe UI", 23, "bold"))
            val.pack(anchor="w", padx=12)
            self.cards[key] = val

        self.attendance_card = self._panel("Asistencias por día", 1, 0, colspan=2)
        self.income_card = self._panel("Ingresos por mes", 1, 2, colspan=2)
        self.plans_card = self._panel("Socios por plan vigente", 2, 0, colspan=2)
        self.inactive_card = self._panel("Socios sin actividad reciente", 2, 2, colspan=2)

        footer = ctk.CTkFrame(self.scroll, fg_color="transparent")
        footer.grid(row=3, column=0, columnspan=4, sticky="ew", padx=5, pady=(12, 18))
        ctk.CTkLabel(footer, text="Exportar reportes:", text_color=SECONDARY, font=("Arial", 12, "bold")).pack(side="left", padx=(0, 10))
        ctk.CTkButton(footer, text="Exportar Excel (.xlsx)", fg_color="#217346", hover_color="#185C37", command=self.export_excel).pack(side="left", padx=5)
        ctk.CTkButton(footer, text="Generar PDF", fg_color="#B33A32", hover_color="#8E2E28", command=self.export_pdf).pack(side="left", padx=5)

    def _panel(self, title, row, col, colspan=1):
        panel = ctk.CTkFrame(
            self.scroll, fg_color=CARD, corner_radius=14,
            border_width=1, border_color="#303840"
        )
        panel.grid(row=row, column=col, columnspan=colspan, sticky="nsew", padx=5, pady=5)
        ctk.CTkLabel(panel, text=title, text_color=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(14, 8))
        content = ctk.CTkFrame(panel, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        return content

    def _period_dates(self):
        today = date.today()
        choice = self.period_var.get()
        if choice == "Este mes":
            start = today.replace(day=1)
        elif choice == "Últimos 30 días":
            start = today - timedelta(days=29)
        else:
            start = today.replace(day=1)
            for _ in range(11):
                start = (start.replace(day=1) - timedelta(days=1)).replace(day=1)
        return start, today

    def refresh_data(self):
        try:
            start, end = self._period_dates()
            self.data = self.db.get_statistics_data(start.isoformat(), end.isoformat(), int(self.inactive_var.get()))
            self.cards["visits"].configure(text=f"{self.data['visits']:,}".replace(",", "."))
            self.cards["current_members"].configure(text=str(self.data["current_members"]))
            self.cards["expired_members"].configure(text=str(self.data["expired_members"]))
            self.cards["income"].configure(
                text=("$" + f"{self.data['income']:,}".replace(",", "."))
                if self.parent.show_money else "••••••"
            )
            self._draw_wave_chart(self.attendance_card, self.data["daily_attendance"], "day", "visits", date_labels=True)
            self._draw_wave_chart(self.income_card, self.data["monthly_income"], "month", "income", money=True)
            self._draw_plans()
            self._draw_inactive()
        except Exception as exc:
            messagebox.showerror("Estadísticas", f"No se pudieron cargar los datos.\n\n{exc}", parent=self)

    def refresh_money_visibility(self):
        if not self.data:
            return
        self.cards["income"].configure(
            text=("$" + f"{self.data['income']:,}".replace(",", "."))
            if self.parent.show_money else "••••••"
        )
        self._draw_wave_chart(
            self.income_card, self.data["monthly_income"],
            "month", "income", money=True
        )

    @staticmethod
    def _format_money(value):
        if value >= 1_000_000:
            return f"${value / 1_000_000:.1f} M".replace(".", ",")
        if value >= 1_000:
            return f"${value / 1_000:.0f} mil"
        return f"${value:,}".replace(",", ".")

    @staticmethod
    def _mix_color(top, bottom, amount):
        def rgb(value):
            value = value.lstrip("#")
            return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
        a, b = rgb(top), rgb(bottom)
        return "#%02X%02X%02X" % tuple(
            round(a[i] + (b[i] - a[i]) * amount) for i in range(3)
        )

    def _draw_wave_chart(self, parent, rows, label_key, value_key,
                         date_labels=False, money=False):
        """Gráfico de tendencia suavizada con área naranja bajo la curva."""
        for widget in parent.winfo_children():
            widget.destroy()

        canvas = tk.Canvas(
            parent, height=255, bg=CARD, highlightthickness=0,
            bd=0, relief="flat"
        )
        canvas.pack(fill="both", expand=True)
        if not rows:
            canvas.create_text(
                22, 42, anchor="w",
                text="Sin datos disponibles para este período.",
                fill=SECONDARY, font=("Segoe UI", 10)
            )
            return

        natural_width = max(480, len(rows) * 30 + 90)
        width = max(natural_width, parent.winfo_width() - 24)
        height = 255
        canvas.configure(scrollregion=(0, 0, width, height))
        left, right, top, bottom = 62, width - 24, 24, 202
        plot_h = bottom - top
        values = [max(0, float(row[value_key] or 0)) for row in rows]
        max_value = max(values) or 1
        nice_max = max_value * 1.18
        hidden_money = money and not self.parent.show_money

        for tick in range(5):
            y = bottom - plot_h * tick / 4
            canvas.create_line(left, y, right, y, fill="#343B43", width=1)
            if not hidden_money:
                tick_value = nice_max * tick / 4
                label = self._format_money(int(tick_value)) if money else str(int(tick_value))
            else:
                label = ""
            canvas.create_text(
                left - 10, y, text=label, anchor="e",
                fill="#89939D", font=("Segoe UI", 8)
            )

        slot = (right - left) / max(1, len(rows) - 1)
        points = []
        for index, (row, value) in enumerate(zip(rows, values)):
            x = left + slot * index if len(rows) > 1 else (left + right) / 2
            y = bottom - (value / nice_max) * plot_h
            points.append((x, y))
            label = str(row[label_key])
            if date_labels and len(label) >= 10:
                label = label[8:10] + "/" + label[5:7]
            elif len(label) == 7:
                label = label[5:7] + "/" + label[2:4]
            canvas.create_text(
                x, bottom + 22, text=label, fill="#AAB3BC",
                font=("Segoe UI", 8)
            )

        if hidden_money:
            canvas.create_text(
                (left + right) / 2, (top + bottom) / 2,
                text="••••••", fill="#AAB3BC",
                font=("Segoe UI", 15, "bold")
            )
            return

        # Área bajo la curva con degradado vertical naranja -> grafito.
        gradient = [
            "#8A3A0B", "#78330D", "#682D10", "#592812",
            "#4B2414", "#3D2116", "#302019", "#25201D"
        ]
        strip_step = 4
        for x in range(int(left), int(right), strip_step):
            segment = 0
            while segment < len(points) - 2 and x > points[segment + 1][0]:
                segment += 1
            x0, y0 = points[segment]
            x1, y1 = points[min(segment + 1, len(points) - 1)]
            ratio = 0 if x1 == x0 else max(0, min(1, (x - x0) / (x1 - x0)))
            curve_y = y0 + (y1 - y0) * ratio
            for band, color in enumerate(gradient):
                band_top = top + plot_h * band / len(gradient)
                band_bottom = top + plot_h * (band + 1) / len(gradient)
                y_top = max(curve_y, band_top)
                if band_bottom > y_top:
                    canvas.create_rectangle(
                        x, y_top, min(right, x + strip_step + 1), band_bottom,
                        fill=color, outline=""
                    )

        # Rejilla discreta por encima del área.
        for tick in range(1, 4):
            y = bottom - plot_h * tick / 4
            canvas.create_line(left, y, right, y, fill="#343B43", width=1)

        if len(points) >= 2:
            flat = [coordinate for point in points for coordinate in point]
            canvas.create_line(
                *flat, fill="#8D3D0C", width=8, smooth=True,
                splinesteps=24, capstyle=tk.ROUND, joinstyle=tk.ROUND
            )
            canvas.create_line(
                *flat, fill=ORANGE, width=3, smooth=True,
                splinesteps=24, capstyle=tk.ROUND, joinstyle=tk.ROUND
            )

        for index, (x, y) in enumerate(points):
            canvas.create_oval(
                x - 5, y - 5, x + 5, y + 5,
                fill="#1B1F23", outline=ORANGE, width=2
            )
            if not money:
                canvas.create_text(
                    x, max(top + 8, y - 15),
                    text=str(int(values[index])),
                    fill="#E8EDF2", font=("Segoe UI", 8, "bold")
                )

        if width > max(520, parent.winfo_width() + 10):
            scrollbar = tk.Scrollbar(parent, orient="horizontal", command=canvas.xview)
            scrollbar.pack(fill="x", pady=(2, 0))
            canvas.configure(xscrollcommand=scrollbar.set)

    def _draw_plans(self):
        for widget in self.plans_card.winfo_children():
            widget.destroy()
        rows = self.data["plan_distribution"]
        if not rows:
            ctk.CTkLabel(
                self.plans_card, text="No hay socios con cuotas vigentes.",
                text_color=SECONDARY, font=("Segoe UI", 10)
            ).pack(anchor="w", padx=8, pady=12)
            return

        total = sum(row["members"] for row in rows) or 1
        palette = ["#FF6600", "#36B37E", "#4C9AFF", "#A78BFA", "#E5B567", "#718096"]
        chart = tk.Canvas(self.plans_card, height=205, bg=CARD, highlightthickness=0)
        chart.pack(side="left", fill="y", padx=(4, 12), pady=4)
        chart.create_oval(18, 20, 178, 180, outline="#343B43", width=20)
        start_angle = 90
        for index, row in enumerate(rows[:10]):
            extent = -360 * row["members"] / total
            chart.create_arc(18, 20, 178, 180, start=start_angle, extent=extent,
                             style="arc", outline=palette[index % len(palette)], width=20)
            start_angle += extent
        chart.create_text(98, 88, text=str(total), fill="#FFFFFF",
                          font=("Segoe UI", 20, "bold"))
        chart.create_text(98, 112, text="SOCIOS", fill="#A0A5AB",
                          font=("Segoe UI", 8, "bold"))

        legend = ctk.CTkFrame(self.plans_card, fg_color="transparent")
        legend.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=8)
        for index, row in enumerate(rows[:10]):
            pct = round(row["members"] * 100 / total)
            line = ctk.CTkFrame(legend, fg_color="transparent")
            line.pack(fill="x", pady=4)
            dot = tk.Canvas(line, width=12, height=12, bg=CARD, highlightthickness=0)
            dot.pack(side="left", padx=(2, 8))
            dot.create_oval(2, 2, 10, 10, fill=palette[index % len(palette)], outline="")
            ctk.CTkLabel(line, text=row["plan"], text_color=TEXT,
                         font=("Segoe UI", 10), anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(line, text=f"{row['members']} · {pct}%",
                         text_color="#C5CDD5", font=("Segoe UI", 9, "bold")).pack(side="right")

    def _draw_inactive(self):
        for widget in self.inactive_card.winfo_children(): widget.destroy()
        rows = self.data["inactive_members"]
        if not rows:
            ctk.CTkLabel(self.inactive_card, text="No se detectan socios sin actividad en este umbral.", text_color=SECONDARY, wraplength=450).pack(anchor="w", padx=5, pady=8)
            return
        table = ctk.CTkScrollableFrame(self.inactive_card, height=190, fg_color="transparent")
        table.pack(fill="both", expand=True)
        for row in rows[:100]:
            line = ctk.CTkFrame(table, fg_color="#292E34", corner_radius=7)
            line.pack(fill="x", pady=2)
            name = f"{row['last_name']}, {row['first_name']}"
            last = row["last_attendance"] or "Sin asistencias"
            ctk.CTkLabel(line, text=f"{name} · DNI {row['dni']}\nÚltima: {last}", text_color=TEXT, justify="left", anchor="w").pack(side="left", padx=8, pady=5, fill="x", expand=True)
            ctk.CTkLabel(line, text=f"{row['days_absent'] or 0} días", text_color="#FF8A65", font=("Arial", 11, "bold")).pack(side="right", padx=8)

    def _export_rows(self):
        d = self.data
        summary = [
            ["Indicador", "Valor"],
            ["Período", f"{d['date_from']} a {d['date_to']}"],
            ["Asistencias", d["visits"]],
            ["Visitantes únicos", d["unique_visitors"]],
            ["Socios con cuota vigente", d["current_members"]],
            ["Socios vencidos", d["expired_members"]],
            ["Socios sin cuota vigente", d["without_current_payment"]],
            ["Socios archivados", d["archived_members"]],
            ["Ingresos", d["income"]],
        ]
        return summary

    def export_excel(self):
        if not self.data: return
        path = filedialog.asksaveasfilename(parent=self, title="Guardar reporte Excel", defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], initialfile="ForjaGym_Estadisticas.xlsx")
        if not path: return
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
            wb = Workbook()
            ws = wb.active; ws.title = "Resumen"
            for row in self._export_rows(): ws.append(row)
            for cell in ws[1]: cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="FF6600")
            ws.column_dimensions["A"].width = 32; ws.column_dimensions["B"].width = 30
            sheets = [
                ("Asistencias", ["Fecha", "Fichajes"], [[r["day"], r["visits"]] for r in self.data["daily_attendance"]]),
                ("Ingresos", ["Mes", "Importe"], [[r["month"], r["income"]] for r in self.data["monthly_income"]]),
                ("Planes", ["Plan", "Socios"], [[r["plan"], r["members"]] for r in self.data["plan_distribution"]]),
                ("Inactividad", ["Apellido", "Nombre", "DNI", "Última asistencia", "Días sin asistir", "Estado cuota"], [[r["last_name"], r["first_name"], r["dni"], r["last_attendance"] or "Nunca", r["days_absent"], r["status"]] for r in self.data["inactive_members"]]),
            ]
            for title, headers, rows in sheets:
                sh = wb.create_sheet(title); sh.append(headers)
                for row in rows: sh.append(row)
                for cell in sh[1]: cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="FF6600")
                for col in sh.columns:
                    letter = col[0].column_letter
                    sh.column_dimensions[letter].width = min(34, max(14, max(len(str(c.value or "")) for c in col) + 2))
                sh.freeze_panes = "A2"
            wb.save(path)
            messagebox.showinfo("Reporte generado", f"El archivo Excel se guardó correctamente:\n{path}", parent=self)
        except ImportError:
            messagebox.showerror("Falta una dependencia", "Para exportar a Excel instalá openpyxl:\npython -m pip install openpyxl", parent=self)
        except Exception as exc:
            messagebox.showerror("Error al exportar", str(exc), parent=self)

    def export_pdf(self):
        if not self.data: return
        path = filedialog.asksaveasfilename(parent=self, title="Guardar reporte PDF", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="ForjaGym_Estadisticas.pdf")
        if not path: return
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            d = self.data
            doc = SimpleDocTemplate(path, pagesize=landscape(A4), rightMargin=14*mm, leftMargin=14*mm, topMargin=14*mm, bottomMargin=14*mm)
            styles = getSampleStyleSheet()
            story = [Paragraph("FORJAGYM — ESTADÍSTICAS Y REPORTES", styles["Title"]), Paragraph(f"Período: {d['date_from']} al {d['date_to']}", styles["Normal"]), Spacer(1, 8*mm)]
            data = [["Indicador", "Resultado"], ["Asistencias", str(d["visits"])], ["Visitantes únicos", str(d["unique_visitors"])], ["Socios con cuota vigente", str(d["current_members"])], ["Socios vencidos", str(d["expired_members"])], ["Socios sin cuota vigente", str(d["without_current_payment"])], ["Socios archivados", str(d["archived_members"])], ["Ingresos del período", "$" + f"{d['income']:,}".replace(",", ".")]]
            t = Table(data, colWidths=[90*mm, 55*mm]); t.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,0), colors.HexColor("#FF6600")), ("TEXTCOLOR", (0,0),(-1,0), colors.white), ("FONTNAME", (0,0),(-1,0), "Helvetica-Bold"), ("GRID", (0,0),(-1,-1), .4, colors.grey), ("PADDING", (0,0),(-1,-1), 6)])); story.append(t); story.append(Spacer(1, 8*mm))
            for title, headers, rows in [("Distribución por plan", ["Plan", "Socios"], [[r["plan"], str(r["members"])] for r in d["plan_distribution"]]), ("Socios sin actividad reciente", ["Apellido", "Nombre", "DNI", "Última asistencia", "Días", "Cuota"], [[r["last_name"], r["first_name"], r["dni"], r["last_attendance"] or "Nunca", str(r["days_absent"] or 0), r["status"]] for r in d["inactive_members"][:80]])]:
                story.append(Paragraph(title, styles["Heading2"]))
                table = Table([headers] + rows, repeatRows=1)
                table.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,0), colors.HexColor("#30343A")), ("TEXTCOLOR", (0,0),(-1,0), colors.white), ("GRID", (0,0),(-1,-1), .35, colors.grey), ("FONTSIZE", (0,0),(-1,-1), 8), ("PADDING", (0,0),(-1,-1), 4)]))
                story.extend([table, Spacer(1, 6*mm)])
            doc.build(story)
            messagebox.showinfo("Reporte generado", f"El PDF se guardó correctamente:\n{path}", parent=self)
        except ImportError:
            messagebox.showerror("Falta una dependencia", "Para exportar a PDF instalá reportlab:\npython -m pip install reportlab", parent=self)
        except Exception as exc:
            messagebox.showerror("Error al exportar", str(exc), parent=self)
