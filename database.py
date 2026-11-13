
import sqlite3
import sys
import time

from pathlib import Path
from contextlib import contextmanager
from datetime import date, datetime, timedelta


# ==========================================
# RUTAS
# ==========================================

def get_app_directory():

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


APP_DIR = get_app_directory()
DATA_DIR = APP_DIR / "datos"
DB_PATH = DATA_DIR / "forjagym.db"


# ==========================================
# BASE DE DATOS
# ==========================================

class Database:

    def __init__(self):

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        self.initialize_database()


    # ======================================
    # CONEXION
    # ======================================

    @contextmanager
    def connection(self, immediate=False):
        """Abre una conexión breve y garantiza commit/rollback/cierre.

        immediate=True reserva el turno de escritura al comienzo de la
        transacción y evita que dos procesos intenten escalar escrituras
        simultáneamente sobre la misma base SQLite.
        """
        conn = sqlite3.connect(
            str(DB_PATH),
            timeout=8,
            isolation_level="DEFERRED"
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 8000")

        try:
            if immediate:
                conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
            raise
        finally:
            conn.close()


    # ======================================
    # CREAR TABLAS
    # ======================================

    def initialize_database(self):

        with self.connection() as conn:

            conn.execute("PRAGMA journal_mode = WAL")

            conn.executescript("""

                CREATE TABLE IF NOT EXISTS members (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    dni TEXT NOT NULL UNIQUE,
                    phone TEXT,
                    emergency_contact TEXT,
                    created_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1

                );


                CREATE TABLE IF NOT EXISTS plans (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,

                    days_per_week INTEGER NOT NULL
                    CHECK(days_per_week BETWEEN 1 AND 7),

                    price INTEGER NOT NULL DEFAULT 0
                    CHECK(price >= 0),

                    active INTEGER NOT NULL DEFAULT 1

                );


                CREATE TABLE IF NOT EXISTS payments (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id INTEGER NOT NULL,
                    plan_id INTEGER,
                    plan_name TEXT NOT NULL,
                    days_per_week INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    payment_date TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,

                    FOREIGN KEY(member_id)
                    REFERENCES members(id),

                    FOREIGN KEY(plan_id)
                    REFERENCES plans(id)
                    ON DELETE SET NULL

                );


                CREATE TABLE IF NOT EXISTS attendances (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id INTEGER NOT NULL,
                    attendance_date TEXT NOT NULL,
                    checked_at TEXT NOT NULL,

                    FOREIGN KEY(member_id)
                    REFERENCES members(id)

                );


                CREATE TABLE IF NOT EXISTS checkin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attendance_id INTEGER UNIQUE,
                    member_id INTEGER,
                    dni TEXT NOT NULL,
                    member_name TEXT NOT NULL DEFAULT '',
                    attendance_date TEXT NOT NULL,
                    checked_at TEXT NOT NULL,
                    result TEXT NOT NULL,
                    message TEXT NOT NULL,
                    used INTEGER,
                    limit_count INTEGER,
                    FOREIGN KEY(attendance_id) REFERENCES attendances(id),
                    FOREIGN KEY(member_id) REFERENCES members(id)
                );


                CREATE INDEX IF NOT EXISTS idx_members_dni
                ON members(dni);

                CREATE INDEX IF NOT EXISTS idx_payments_member
                ON payments(member_id);

                CREATE INDEX IF NOT EXISTS idx_payments_date
                ON payments(payment_date);

                CREATE INDEX IF NOT EXISTS idx_attendance_member
                ON attendances(member_id);

                CREATE INDEX IF NOT EXISTS idx_attendance_date
                ON attendances(attendance_date);

            """)



            # MIGRACIÓN SEGURA: incorporar duración a planes y pagos existentes.
            # Los registros previos reciben 30 días como valor histórico predeterminado.
            plan_columns = {
                row["name"] for row in
                conn.execute("PRAGMA table_info(plans)").fetchall()
            }
            if "duration_days" not in plan_columns:
                conn.execute("""
                    ALTER TABLE plans
                    ADD COLUMN duration_days INTEGER NOT NULL DEFAULT 30
                    CHECK(duration_days >= 1)
                """)

            payment_columns = {
                row["name"] for row in
                conn.execute("PRAGMA table_info(payments)").fetchall()
            }
            if "duration_days" not in payment_columns:
                conn.execute("""
                    ALTER TABLE payments
                    ADD COLUMN duration_days INTEGER NOT NULL DEFAULT 30
                    CHECK(duration_days >= 1)
                """)

            # MIGRACIÓN SEGURA: permitir múltiples fichajes del mismo socio por día.
            # Conserva IDs, fechas, horas y relaciones de todos los registros existentes.
            attendance_sql_row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'attendances'"
            ).fetchone()
            attendance_sql = attendance_sql_row["sql"] if attendance_sql_row else ""
            normalized_attendance_sql = " ".join((attendance_sql or "").upper().split())
            if "UNIQUE" in normalized_attendance_sql and "MEMBER_ID" in normalized_attendance_sql and "ATTENDANCE_DATE" in normalized_attendance_sql:
                conn.execute("PRAGMA foreign_keys = OFF")
                conn.execute("""
                    CREATE TABLE attendances_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        member_id INTEGER NOT NULL,
                        attendance_date TEXT NOT NULL,
                        checked_at TEXT NOT NULL,
                        FOREIGN KEY(member_id) REFERENCES members(id)
                    )
                """)
                conn.execute("""
                    INSERT INTO attendances_new (id, member_id, attendance_date, checked_at)
                    SELECT id, member_id, attendance_date, checked_at FROM attendances
                """)
                conn.execute("DROP TABLE attendances")
                conn.execute("ALTER TABLE attendances_new RENAME TO attendances")
                conn.execute("PRAGMA foreign_keys = ON")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_member ON attendances(member_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendances(attendance_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_member_date ON attendances(member_id, attendance_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_checkin_logs_date ON checkin_logs(attendance_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_checkin_logs_dni ON checkin_logs(dni)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_checkin_logs_result ON checkin_logs(result)")

            # Migración: incorporar al historial los fichajes exitosos anteriores.
            # attendance_id único evita duplicarlos al iniciar ADMIN o FICHAJE nuevamente.
            conn.execute("""
                INSERT OR IGNORE INTO checkin_logs
                (attendance_id, member_id, dni, member_name, attendance_date, checked_at, result, message)
                SELECT a.id, m.id, m.dni,
                       TRIM(COALESCE(m.first_name, '') || ' ' || COALESCE(m.last_name, '')),
                       a.attendance_date, a.checked_at, 'allowed', 'ACCESO PERMITIDO'
                FROM attendances a
                JOIN members m ON m.id = a.member_id
            """)

            # ENTRENAMIENTOS: plantillas maestras independientes de los planes de cuotas.
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS workout_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workout_template_days (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id INTEGER NOT NULL,
                    weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
                    muscle_groups TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    UNIQUE(template_id, weekday),
                    FOREIGN KEY(template_id) REFERENCES workout_templates(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS workout_template_exercises (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day_id INTEGER NOT NULL,
                    exercise_order INTEGER NOT NULL DEFAULT 0,
                    name TEXT NOT NULL,
                    sets TEXT DEFAULT '',
                    reps TEXT DEFAULT '',
                    reference_weight TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    FOREIGN KEY(day_id) REFERENCES workout_template_days(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_workout_days_template ON workout_template_days(template_id);
                CREATE INDEX IF NOT EXISTS idx_workout_exercises_day ON workout_template_exercises(day_id);
            """)

            # ASIGNACIONES DE RUTINAS A SOCIOS: cada asignación guarda una copia
            # independiente de la plantilla para que futuras ediciones maestras no
            # modifiquen los planes ya entregados.
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS member_workout_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id INTEGER NOT NULL,
                    template_id INTEGER,
                    routine_name TEXT NOT NULL,
                    routine_description TEXT DEFAULT '',
                    start_date TEXT NOT NULL,
                    assigned_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE,
                    FOREIGN KEY(template_id) REFERENCES workout_templates(id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS member_workout_days (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assignment_id INTEGER NOT NULL,
                    weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
                    muscle_groups TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    FOREIGN KEY(assignment_id) REFERENCES member_workout_assignments(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS member_workout_exercises (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day_id INTEGER NOT NULL,
                    exercise_order INTEGER NOT NULL DEFAULT 0,
                    name TEXT NOT NULL,
                    sets TEXT DEFAULT '',
                    reps TEXT DEFAULT '',
                    reference_weight TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    FOREIGN KEY(day_id) REFERENCES member_workout_days(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_member_workout_member ON member_workout_assignments(member_id, active, start_date);
                CREATE INDEX IF NOT EXISTS idx_member_workout_days_assignment ON member_workout_days(assignment_id);
                CREATE INDEX IF NOT EXISTS idx_member_workout_exercises_day ON member_workout_exercises(day_id);
            """)

            default_plans = [

                ("Plan 2 días", 2, 60000),
                ("Plan 3 días", 3, 65000),
                ("Plan 5 días", 5, 70000),
                ("Personalizado 3 días", 3, 150000),
                ("Personalizado 4 días", 4, 200000),

            ]


            conn.executemany("""

                INSERT OR IGNORE INTO plans
                (name, days_per_week, duration_days, price)

                VALUES (?, ?, 30, ?)

            """, default_plans)


    # ======================================
    # REGISTRAR SOCIO
    # ======================================

    def add_member(
        self,
        first_name,
        last_name,
        dni,
        phone="",
        emergency_contact=""
    ):

        with self.connection() as conn:

            cursor = conn.execute("""

                INSERT INTO members (

                    first_name,
                    last_name,
                    dni,
                    phone,
                    emergency_contact,
                    created_at

                )

                VALUES (?, ?, ?, ?, ?, ?)

            """, (

                first_name.strip(),
                last_name.strip(),
                dni.strip(),
                phone.strip(),
                emergency_contact.strip(),
                date.today().isoformat()

            ))

            return cursor.lastrowid


    # ======================================
    # MODIFICAR SOCIO
    # ======================================

    def update_member(
        self,
        member_id,
        first_name,
        last_name,
        dni,
        phone,
        emergency_contact
    ):

        with self.connection() as conn:

            conn.execute("""

                UPDATE members

                SET
                    first_name = ?,
                    last_name = ?,
                    dni = ?,
                    phone = ?,
                    emergency_contact = ?

                WHERE id = ?
                AND active = 1

            """, (

                first_name.strip(),
                last_name.strip(),
                dni.strip(),
                phone.strip(),
                emergency_contact.strip(),
                member_id

            ))


    # ======================================
    # OBTENER SOCIO POR ID
    # ======================================

    def get_member_by_id(self, member_id):

        with self.connection() as conn:

            member = conn.execute("""

                SELECT *

                FROM members

                WHERE id = ?
                AND active = 1

            """, (member_id,)).fetchone()

            return dict(member) if member else None


    # ======================================
    # BUSCAR Y LISTAR SOCIOS
    # ======================================

    def get_members(self, search="", include_archived=False):

        today = date.today().isoformat()

        with self.connection() as conn:

            members = conn.execute("""

                SELECT

                    m.id,
                    m.first_name,
                    m.last_name,
                    m.dni,
                    m.phone,
                    m.emergency_contact,
                    m.created_at,
                    m.active,

                    p.plan_name,
                    p.days_per_week,
                    p.duration_days,
                    p.start_date,
                    p.end_date,
                    p.payment_date,

                    CASE

                        WHEN p.id IS NULL
                        THEN 'Sin cuota'

                        WHEN p.start_date > ?
                        THEN 'Pendiente'

                        WHEN p.end_date < ?
                        THEN 'Vencida'

                        ELSE 'Abonado'

                    END AS status

                FROM members m

                LEFT JOIN payments p

                    ON p.id = (

                        SELECT p2.id

                        FROM payments p2

                        WHERE p2.member_id = m.id

                        ORDER BY
                            p2.start_date DESC,
                            p2.id DESC

                        LIMIT 1

                    )

                WHERE

                    (? = 1 OR m.active = 1)

                AND (

                    m.first_name LIKE ?
                    OR m.last_name LIKE ?
                    OR m.dni LIKE ?

                )

                ORDER BY

                    m.last_name,
                    m.first_name

            """, (

                today,
                today,
                1 if include_archived else 0,
                f"%{search.strip()}%",
                f"%{search.strip()}%",
                f"%{search.strip()}%"

            )).fetchall()

            return [dict(member) for member in members]


    # ======================================
    # ARCHIVAR SOCIO
    # ======================================

    def archive_member(self, member_id):

        with self.connection() as conn:

            conn.execute("""

                UPDATE members

                SET active = 0

                WHERE id = ?

            """, (member_id,))


    # ======================================
    # ELIMINAR DEFINITIVAMENTE UN SOCIO
    # ======================================

    def delete_member_permanently(self, member_id):
        """Elimina un socio y todos sus registros dependientes de forma atómica.

        Se reintenta únicamente ante bloqueos transitorios SQLITE_BUSY/LOCKED.
        Cada intento usa una conexión nueva y una transacción BEGIN IMMEDIATE.
        """
        max_attempts = 4

        for attempt in range(max_attempts):
            try:
                with self.connection(immediate=True) as conn:
                    member = conn.execute(
                        "SELECT id FROM members WHERE id = ?",
                        (member_id,)
                    ).fetchone()

                    if not member:
                        raise ValueError("El socio no existe.")

                    # Primero se eliminan los logs que referencian tanto al
                    # socio como a sus asistencias (incluye logs históricos).
                    conn.execute("""
                        DELETE FROM checkin_logs
                        WHERE member_id = ?
                           OR attendance_id IN (
                               SELECT id FROM attendances WHERE member_id = ?
                           )
                    """, (member_id, member_id))

                    conn.execute(
                        "DELETE FROM attendances WHERE member_id = ?",
                        (member_id,)
                    )
                    conn.execute(
                        "DELETE FROM payments WHERE member_id = ?",
                        (member_id,)
                    )
                    conn.execute(
                        "DELETE FROM members WHERE id = ?",
                        (member_id,)
                    )

                return True

            except sqlite3.OperationalError as error:
                message = str(error).lower()
                is_lock = (
                    "database is locked" in message
                    or "database table is locked" in message
                    or "database is busy" in message
                )
                if not is_lock or attempt == max_attempts - 1:
                    if is_lock:
                        raise RuntimeError(
                            "La base de datos está ocupada por otra operación "
                            "(ADMIN o FICHAJE). Esperá unos segundos y volvé a "
                            "intentarlo. No se eliminó ningún dato."
                        ) from error
                    raise

                # Espera creciente y acotada antes de abrir otra conexión.
                time.sleep(0.25 * (2 ** attempt))

        return False


    # ======================================
    # OBTENER PLANES
    # ======================================

    def get_plans(self, active_only=True):

        with self.connection() as conn:

            if active_only:

                plans = conn.execute("""

                    SELECT *

                    FROM plans

                    WHERE active = 1

                    ORDER BY days_per_week, name

                """).fetchall()

            else:

                plans = conn.execute("""

                    SELECT *

                    FROM plans

                    ORDER BY days_per_week, name

                """).fetchall()


            return [dict(plan) for plan in plans]


    # ======================================
    # CREAR PLAN
    # ======================================

    def add_plan(self, name, days_per_week, duration_days, price):

        name = str(name).strip()

        if not name:
            raise ValueError("El nombre del plan es obligatorio.")

        try:
            days_per_week = int(days_per_week)
            duration_days = int(duration_days)
            price = int(price)
        except (TypeError, ValueError):
            raise ValueError("Frecuencia, duración y precio deben ser números enteros.")

        if not 1 <= days_per_week <= 7:
            raise ValueError("La frecuencia semanal debe estar entre 1 y 7 días.")

        if duration_days < 1:
            raise ValueError("La duración debe ser de al menos 1 día.")

        if price < 0:
            raise ValueError("El precio no puede ser negativo.")

        with self.connection() as conn:
            duplicate = conn.execute(
                "SELECT id FROM plans WHERE name = ? COLLATE NOCASE",
                (name,)
            ).fetchone()

            if duplicate:
                raise ValueError("Ya existe un plan con ese nombre.")

            cursor = conn.execute("""
                INSERT INTO plans
                    (name, days_per_week, duration_days, price, active)
                VALUES (?, ?, ?, ?, 1)
            """, (name, days_per_week, duration_days, price))

            return cursor.lastrowid

    def update_plan(self, plan_id, name, days_per_week, duration_days, price):

        name = str(name).strip()

        if not name:
            raise ValueError("El nombre del plan es obligatorio.")

        try:
            plan_id = int(plan_id)
            days_per_week = int(days_per_week)
            duration_days = int(duration_days)
            price = int(price)
        except (TypeError, ValueError):
            raise ValueError("Frecuencia, duración y precio deben ser números enteros.")

        if not 1 <= days_per_week <= 7:
            raise ValueError("La frecuencia semanal debe estar entre 1 y 7 días.")

        if duration_days < 1:
            raise ValueError("La duración debe ser de al menos 1 día.")

        if price < 0:
            raise ValueError("El precio no puede ser negativo.")

        with self.connection() as conn:
            plan = conn.execute(
                "SELECT id FROM plans WHERE id = ?",
                (plan_id,)
            ).fetchone()

            if not plan:
                raise ValueError("El plan seleccionado no existe.")

            duplicate = conn.execute("""
                SELECT id FROM plans
                WHERE name = ? COLLATE NOCASE AND id <> ?
            """, (name, plan_id)).fetchone()

            if duplicate:
                raise ValueError("Ya existe otro plan con ese nombre.")

            conn.execute("""
                UPDATE plans
                SET name = ?, days_per_week = ?,
                    duration_days = ?, price = ?
                WHERE id = ?
            """, (name, days_per_week, duration_days, price, plan_id))

    def set_plan_active(self, plan_id, active):

        try:
            plan_id = int(plan_id)
        except (TypeError, ValueError):
            raise ValueError("El plan seleccionado no es válido.")

        active_value = 1 if bool(active) else 0

        with self.connection() as conn:
            cursor = conn.execute("""
                UPDATE plans
                SET active = ?
                WHERE id = ?
            """, (active_value, plan_id))

            if cursor.rowcount == 0:
                raise ValueError("El plan seleccionado no existe.")


    # ======================================
    # OBTENER PLAN POR ID
    # ======================================

    def get_plan_by_id(self, plan_id):

        with self.connection() as conn:
            plan = conn.execute("""
                SELECT *
                FROM plans
                WHERE id = ?
            """, (plan_id,)).fetchone()

            return dict(plan) if plan else None


    # ======================================
    # REGISTRAR PAGO
    # ======================================

    def register_payment(
        self,
        member_id,
        plan_id,
        amount,
        payment_date,
        start_date,
        end_date,
        duration_days=None
    ):

        try:
            payment_day = date.fromisoformat(payment_date)
            start_day = date.fromisoformat(start_date)
            end_day = date.fromisoformat(end_date)
        except (TypeError, ValueError):
            raise ValueError("Las fechas deben tener formato AAAA-MM-DD.")

        if end_day < start_day:
            raise ValueError("El vencimiento no puede ser anterior al inicio.")

        try:
            amount = int(amount)
        except (TypeError, ValueError):
            raise ValueError("El importe debe ser un número entero.")

        if amount < 0:
            raise ValueError("El importe no puede ser negativo.")

        with self.connection() as conn:
            member = conn.execute("""
                SELECT id
                FROM members
                WHERE id = ? AND active = 1
            """, (member_id,)).fetchone()

            if not member:
                raise ValueError("El socio no existe o está archivado.")

            plan = conn.execute("""
                SELECT *
                FROM plans
                WHERE id = ? AND active = 1
            """, (plan_id,)).fetchone()

            if not plan:
                raise ValueError("El plan no existe o está inactivo.")

            # Si no se indica duración (compatibilidad con llamadas anteriores),
            # se utiliza la duración vigente del plan.
            if duration_days is None:
                duration_days = plan["duration_days"]

            try:
                duration_days = int(duration_days)
            except (TypeError, ValueError):
                raise ValueError("La duración de la cuota debe ser un número entero.")

            if duration_days < 1:
                raise ValueError("La duración de la cuota debe ser de al menos 1 día.")

            cursor = conn.execute("""
                INSERT INTO payments (
                    member_id,
                    plan_id,
                    plan_name,
                    days_per_week,
                    duration_days,
                    amount,
                    payment_date,
                    start_date,
                    end_date,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                member_id,
                plan["id"],
                plan["name"],
                plan["days_per_week"],
                duration_days,
                amount,
                payment_day.isoformat(),
                start_day.isoformat(),
                end_day.isoformat(),
                datetime.now().isoformat(timespec="seconds")
            ))

            return cursor.lastrowid

    def get_payments(self, search=""):

        with self.connection() as conn:

            payments = conn.execute("""

                SELECT

                    p.id,
                    p.member_id,
                    m.first_name,
                    m.last_name,
                    m.dni,
                    p.plan_name,
                    p.days_per_week,
                    p.duration_days,
                    p.amount,
                    p.payment_date,
                    p.start_date,
                    p.end_date

                FROM payments p

                INNER JOIN members m

                    ON m.id = p.member_id

                WHERE

                    m.first_name LIKE ?
                    OR m.last_name LIKE ?
                    OR m.dni LIKE ?

                ORDER BY

                    p.payment_date DESC,
                    p.id DESC

            """, (

                f"%{search.strip()}%",
                f"%{search.strip()}%",
                f"%{search.strip()}%"

            )).fetchall()

            return [dict(payment) for payment in payments]


    # ======================================
    # ELIMINAR UN PAGO
    # ======================================

    def delete_payment(self, payment_id):

        with self.connection() as conn:

            cursor = conn.execute("""

                DELETE FROM payments

                WHERE id = ?

            """, (payment_id,))


            if cursor.rowcount == 0:

                raise ValueError(
                    "El pago seleccionado no existe."
                )


    # ======================================
    # HISTORIAL DE UN SOCIO
    # ======================================

    def get_payment_history(self, member_id):

        with self.connection() as conn:

            payments = conn.execute("""

                SELECT *

                FROM payments

                WHERE member_id = ?

                ORDER BY payment_date DESC, id DESC

            """, (member_id,)).fetchall()

            return [dict(payment) for payment in payments]


    # ======================================
    # FICHAJE POR DNI
    # ======================================

    def check_in_by_dni(self, dni, current_datetime=None):
        """Valida un intento de ingreso, registra la asistencia si corresponde y audita el resultado."""
        dni = str(dni).strip()
        now = current_datetime or datetime.now()
        today = now.date()
        today_str = today.isoformat()
        checked_at = now.isoformat(timespec="seconds")
        if not dni:
            return {"status": "not_found", "message": "Ingresá un DNI."}

        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)

        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")

            def save_attempt(status, message, member=None, payment=None, used=None, limit=None,
                             attendance_id=None):
                member_data = dict(member) if member else {}
                full_name = " ".join(
                    part for part in (member_data.get("first_name", ""), member_data.get("last_name", ""))
                    if part
                ).strip()
                conn.execute("""
                    INSERT INTO checkin_logs
                    (attendance_id, member_id, dni, member_name, attendance_date,
                     checked_at, result, message, used, limit_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    attendance_id,
                    member_data.get("id"),
                    dni,
                    full_name,
                    today_str,
                    checked_at,
                    status,
                    message,
                    used,
                    limit
                ))
                result = {
                    "status": status,
                    "message": message,
                    "dni": dni,
                    "checked_at": checked_at
                }
                if member:
                    result["member"] = member_data
                if payment:
                    result["payment"] = dict(payment)
                if used is not None:
                    result["used"] = used
                if limit is not None:
                    result["limit"] = limit
                    result["remaining"] = max(0, limit - used) if used is not None else None
                return result

            member = conn.execute("""
                SELECT id, first_name, last_name, dni, active
                FROM members WHERE dni = ?
            """, (dni,)).fetchone()

            if not member:
                return save_attempt("not_found", "SOCIO NO ENCONTRADO")
            if not member["active"]:
                return save_attempt("inactive", "SOCIO INACTIVO", member)

            payment = conn.execute("""
                SELECT id, plan_name, days_per_week, duration_days, start_date, end_date
                FROM payments WHERE member_id = ?
                ORDER BY start_date DESC, id DESC LIMIT 1
            """, (member["id"],)).fetchone()

            if not payment:
                return save_attempt("no_payment", "SIN CUOTA REGISTRADA", member)
            if payment["start_date"] > today_str:
                return save_attempt("pending", "CUOTA AÚN NO VIGENTE", member, payment)
            if payment["end_date"] < today_str:
                return save_attempt("expired", "CUOTA VENCIDA - DEBE ABONAR", member, payment)

            count_from = max(monday.isoformat(), payment["start_date"])
            count_to = min(today_str, sunday.isoformat(), payment["end_date"])
            used = conn.execute("""
                SELECT COUNT(*) FROM attendances
                WHERE member_id = ? AND attendance_date BETWEEN ? AND ?
            """, (member["id"], count_from, count_to)).fetchone()[0]
            limit = int(payment["days_per_week"])

            if used >= limit:
                return save_attempt(
                    "limit_reached", "SIN ASISTENCIAS DISPONIBLES ESTA SEMANA",
                    member, payment, used, limit
                )

            cursor = conn.execute("""
                INSERT INTO attendances (member_id, attendance_date, checked_at)
                VALUES (?, ?, ?)
            """, (member["id"], today_str, checked_at))
            attendance_id = cursor.lastrowid
            return save_attempt(
                "allowed", "ACCESO PERMITIDO", member, payment,
                used + 1, limit, attendance_id
            )

    def get_attendance_history(
        self, search="", date_from="", date_to="", result_filter="Todos", limit=2000
    ):
        """Devuelve intentos de fichaje recientes con filtros opcionales."""
        conditions = []
        params = []

        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append("(l.dni LIKE ? OR l.member_name LIKE ?)")
            params.extend([term, term])
        if date_from and date_from.strip():
            conditions.append("l.attendance_date >= ?")
            params.append(date_from.strip())
        if date_to and date_to.strip():
            conditions.append("l.attendance_date <= ?")
            params.append(date_to.strip())
        if result_filter and result_filter != "Todos":
            conditions.append("l.result = ?")
            params.append(result_filter)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        try:
            limit = max(1, min(int(limit), 10000))
        except (TypeError, ValueError):
            limit = 2000

        with self.connection() as conn:
            rows = conn.execute(f"""
                SELECT l.id, l.dni, l.member_name, l.attendance_date, l.checked_at,
                       l.result, l.message, l.used, l.limit_count,
                       CASE WHEN l.result = 'allowed' THEN 'Permitido' ELSE 'Rechazado' END AS outcome
                FROM checkin_logs l
                {where_clause}
                ORDER BY l.checked_at DESC, l.id DESC
                LIMIT ?
            """, (*params, limit)).fetchall()
            return [dict(row) for row in rows]

    def get_attendance_history_summary(self):
        """Resumen de intentos y accesos registrados."""
        today_str = date.today().isoformat()
        with self.connection() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS total_attempts,
                    SUM(CASE WHEN result = 'allowed' THEN 1 ELSE 0 END) AS allowed,
                    SUM(CASE WHEN result <> 'allowed' THEN 1 ELSE 0 END) AS rejected,
                    SUM(CASE WHEN attendance_date = ? THEN 1 ELSE 0 END) AS today_attempts
                FROM checkin_logs
            """, (today_str,)).fetchone()
            return {
                "total_attempts": int(row["total_attempts"] or 0),
                "allowed": int(row["allowed"] or 0),
                "rejected": int(row["rejected"] or 0),
                "today_attempts": int(row["today_attempts"] or 0)
            }

    def get_attendance_count_for_week(self, member_id, reference_date=None):
        reference_date = reference_date or date.today()
        if isinstance(reference_date, str):
            reference_date = date.fromisoformat(reference_date)
        monday = reference_date - timedelta(days=reference_date.weekday())
        sunday = monday + timedelta(days=6)
        with self.connection() as conn:
            row = conn.execute("""
                SELECT COUNT(*) AS total FROM attendances
                WHERE member_id = ? AND attendance_date BETWEEN ? AND ?
            """, (member_id, monday.isoformat(), sunday.isoformat())).fetchone()
            return int(row["total"])

    # ======================================
    # ESTADISTICAS Y REPORTES
    # ======================================

    def get_statistics_data(self, date_from, date_to, inactive_days=14):
        """Devuelve indicadores y series para el panel de estadísticas."""
        try:
            start = date.fromisoformat(str(date_from))
            end = date.fromisoformat(str(date_to))
            inactive_days = max(1, int(inactive_days))
        except (TypeError, ValueError):
            raise ValueError("El período o los días de inactividad no son válidos.")
        if end < start:
            raise ValueError("La fecha final no puede ser anterior a la inicial.")

        today = date.today()
        today_s = today.isoformat()
        cutoff = (today - timedelta(days=inactive_days)).isoformat()
        start_s, end_s = start.isoformat(), end.isoformat()
        next_day = (end + timedelta(days=1)).isoformat()

        with self.connection() as conn:
            totals = conn.execute("""
                SELECT
                    (SELECT COUNT(*) FROM attendances
                     WHERE attendance_date >= ? AND attendance_date < ?) AS visits,
                    (SELECT COUNT(DISTINCT member_id) FROM attendances
                     WHERE attendance_date >= ? AND attendance_date < ?) AS unique_visitors,
                    (SELECT COALESCE(SUM(amount), 0) FROM payments
                     WHERE payment_date >= ? AND payment_date < ?) AS income,
                    (SELECT COUNT(*) FROM members WHERE active = 1) AS registered_active
            """, (start_s, next_day, start_s, next_day, start_s, next_day)).fetchone()

            member_status = conn.execute("""
                WITH latest AS (
                    SELECT p.*, ROW_NUMBER() OVER (
                        PARTITION BY member_id ORDER BY start_date DESC, id DESC
                    ) AS rn
                    FROM payments p
                )
                SELECT
                    SUM(CASE WHEN m.active = 1 AND l.id IS NOT NULL
                              AND l.start_date <= ? AND l.end_date >= ? THEN 1 ELSE 0 END) AS current_members,
                    SUM(CASE WHEN m.active = 1 AND l.id IS NOT NULL
                              AND l.end_date < ? THEN 1 ELSE 0 END) AS expired_members,
                    SUM(CASE WHEN m.active = 1 AND (l.id IS NULL OR l.start_date > ?) THEN 1 ELSE 0 END) AS without_current_payment,
                    SUM(CASE WHEN m.active = 0 THEN 1 ELSE 0 END) AS archived_members
                FROM members m
                LEFT JOIN latest l ON l.member_id = m.id AND l.rn = 1
            """, (today_s, today_s, today_s, today_s)).fetchone()

            daily_rows = conn.execute("""
                SELECT attendance_date AS day, COUNT(*) AS visits
                FROM attendances
                WHERE attendance_date >= ? AND attendance_date < ?
                GROUP BY attendance_date ORDER BY attendance_date
            """, (start_s, next_day)).fetchall()

            monthly_rows = conn.execute("""
                SELECT substr(payment_date, 1, 7) AS month, COALESCE(SUM(amount), 0) AS income
                FROM payments
                WHERE payment_date >= ? AND payment_date < ?
                GROUP BY substr(payment_date, 1, 7) ORDER BY month
            """, (start_s, next_day)).fetchall()

            plan_rows = conn.execute("""
                WITH latest AS (
                    SELECT p.*, ROW_NUMBER() OVER (
                        PARTITION BY member_id ORDER BY start_date DESC, id DESC
                    ) AS rn
                    FROM payments p
                )
                SELECT l.plan_name AS plan, COUNT(*) AS members
                FROM members m JOIN latest l ON l.member_id = m.id AND l.rn = 1
                WHERE m.active = 1 AND l.start_date <= ? AND l.end_date >= ?
                GROUP BY l.plan_name ORDER BY members DESC, l.plan_name
            """, (today_s, today_s)).fetchall()

            inactive_rows = conn.execute("""
                WITH latest AS (
                    SELECT p.*, ROW_NUMBER() OVER (
                        PARTITION BY member_id ORDER BY start_date DESC, id DESC
                    ) AS rn
                    FROM payments p
                ), last_visit AS (
                    SELECT member_id, MAX(attendance_date) AS last_attendance
                    FROM attendances GROUP BY member_id
                )
                SELECT m.id, m.first_name, m.last_name, m.dni,
                       lv.last_attendance,
                       CAST(julianday(?) - julianday(COALESCE(lv.last_attendance, m.created_at)) AS INTEGER) AS days_absent,
                       CASE WHEN l.id IS NULL THEN 'Sin cuota'
                            WHEN l.start_date > ? THEN 'Pendiente'
                            WHEN l.end_date < ? THEN 'Vencida'
                            ELSE 'Abonado' END AS status
                FROM members m
                LEFT JOIN latest l ON l.member_id = m.id AND l.rn = 1
                LEFT JOIN last_visit lv ON lv.member_id = m.id
                WHERE m.active = 1
                  AND (lv.last_attendance IS NULL OR lv.last_attendance <= ?)
                ORDER BY days_absent DESC, m.last_name, m.first_name
                LIMIT 500
            """, (today_s, today_s, today_s, cutoff)).fetchall()

            checkin_rows = conn.execute("""
                SELECT result, COUNT(*) AS total
                FROM checkin_logs
                WHERE attendance_date >= ? AND attendance_date < ?
                GROUP BY result
            """, (start_s, next_day)).fetchall()

        return {
            "date_from": start_s,
            "date_to": end_s,
            "inactive_days": inactive_days,
            "visits": int(totals["visits"] or 0),
            "unique_visitors": int(totals["unique_visitors"] or 0),
            "income": int(totals["income"] or 0),
            "registered_active": int(totals["registered_active"] or 0),
            "current_members": int(member_status["current_members"] or 0),
            "expired_members": int(member_status["expired_members"] or 0),
            "without_current_payment": int(member_status["without_current_payment"] or 0),
            "archived_members": int(member_status["archived_members"] or 0),
            "daily_attendance": [dict(r) for r in daily_rows],
            "monthly_income": [dict(r) for r in monthly_rows],
            "plan_distribution": [dict(r) for r in plan_rows],
            "inactive_members": [dict(r) for r in inactive_rows],
            "checkin_results": {r["result"]: int(r["total"]) for r in checkin_rows},
        }

    # ======================================
    # RESUMEN DEL DASHBOARD
    # ======================================

    def get_dashboard_summary(self):

        today = date.today()

        current_month = today.strftime("%Y-%m")

        today_str = today.isoformat()

        with self.connection() as conn:

            total_members = conn.execute("""

                SELECT COUNT(*)

                FROM members

                WHERE active = 1

            """).fetchone()[0]


            active_members = conn.execute("""

                SELECT COUNT(*)

                FROM members m

                WHERE m.active = 1

                AND EXISTS (

                    SELECT 1

                    FROM payments p

                    WHERE p.member_id = m.id

                    AND p.start_date <= ?

                    AND p.end_date >= ?

                )

            """, (

                today_str,
                today_str

            )).fetchone()[0]


            # INGRESOS DEL MES CALENDARIO

            monthly_income = conn.execute("""

                SELECT COALESCE(SUM(amount), 0)

                FROM payments

                WHERE payment_date >= ?

                AND payment_date < ?

            """, (

                f"{current_month}-01",

                date(

                    today.year + (today.month == 12),

                    today.month % 12 + 1,

                    1

                ).isoformat()

            )).fetchone()[0]


        return {

            "total_members": total_members,

            "active_members": active_members,

            "monthly_income": monthly_income

        }


    # ======================================
    # PLANTILLAS MAESTRAS DE ENTRENAMIENTO
    # ======================================

    def get_workout_templates(self):
        with self.connection() as conn:
            return conn.execute("SELECT * FROM workout_templates ORDER BY name COLLATE NOCASE").fetchall()

    def save_workout_template(self, template_id, name, description):
        name = (name or "").strip()
        if not name:
            raise ValueError("El nombre de la rutina es obligatorio.")
        with self.connection(immediate=True) as conn:
            if template_id:
                conn.execute("UPDATE workout_templates SET name=?, description=? WHERE id=?", (name, description or "", template_id))
                return template_id
            cur = conn.execute("INSERT INTO workout_templates(name, description, created_at) VALUES(?,?,?)", (name, description or "", datetime.now().isoformat(timespec="seconds")))
            return cur.lastrowid

    def delete_workout_template(self, template_id):
        with self.connection(immediate=True) as conn:
            conn.execute("DELETE FROM workout_templates WHERE id=?", (template_id,))

    def get_workout_template_detail(self, template_id):
        with self.connection() as conn:
            template = conn.execute("SELECT * FROM workout_templates WHERE id=?", (template_id,)).fetchone()
            if not template:
                return None
            days = conn.execute("SELECT * FROM workout_template_days WHERE template_id=? ORDER BY weekday", (template_id,)).fetchall()
            result = {"template": template, "days": []}
            for day in days:
                exercises = conn.execute("SELECT * FROM workout_template_exercises WHERE day_id=? ORDER BY exercise_order, id", (day["id"],)).fetchall()
                result["days"].append({"day": day, "exercises": exercises})
            return result

    def save_workout_day(self, template_id, weekday, muscle_groups, day_notes, exercises):
        with self.connection(immediate=True) as conn:
            row = conn.execute("SELECT id FROM workout_template_days WHERE template_id=? AND weekday=?", (template_id, weekday)).fetchone()
            if row:
                day_id = row["id"]
                conn.execute("UPDATE workout_template_days SET muscle_groups=?, notes=? WHERE id=?", (muscle_groups or "", day_notes or "", day_id))
                conn.execute("DELETE FROM workout_template_exercises WHERE day_id=?", (day_id,))
            else:
                cur = conn.execute("INSERT INTO workout_template_days(template_id, weekday, muscle_groups, notes) VALUES(?,?,?,?)", (template_id, weekday, muscle_groups or "", day_notes or ""))
                day_id = cur.lastrowid
            for order, exercise in enumerate(exercises):
                if (exercise.get("name") or "").strip():
                    conn.execute("""INSERT INTO workout_template_exercises
                        (day_id, exercise_order, name, sets, reps, reference_weight, notes)
                        VALUES(?,?,?,?,?,?,?)""", (day_id, order, exercise["name"].strip(), exercise.get("sets", ""), exercise.get("reps", ""), exercise.get("weight", ""), exercise.get("notes", "")))

    def delete_workout_day(self, template_id, weekday):
        with self.connection(immediate=True) as conn:
            conn.execute("DELETE FROM workout_template_days WHERE template_id=? AND weekday=?", (template_id, weekday))

    # ======================================
    # ASIGNACIONES PERSONALIZADAS A SOCIOS
    # ======================================

    def assign_workout_to_member(self, member_id, template_id, start_date):
        """Asigna una copia independiente de una plantilla al socio."""
        start_date = (start_date or "").strip()
        try:
            date.fromisoformat(start_date)
        except ValueError:
            raise ValueError("La fecha debe tener el formato AAAA-MM-DD.")

        with self.connection(immediate=True) as conn:
            member = conn.execute(
                "SELECT id FROM members WHERE id=? AND active=1", (member_id,)
            ).fetchone()
            if not member:
                raise ValueError("El socio no existe o está archivado.")
            template = conn.execute(
                "SELECT * FROM workout_templates WHERE id=?", (template_id,)
            ).fetchone()
            if not template:
                raise ValueError("La rutina maestra seleccionada ya no existe.")

            days = conn.execute(
                "SELECT * FROM workout_template_days WHERE template_id=? ORDER BY weekday", (template_id,)
            ).fetchall()
            if not days:
                raise ValueError("La rutina maestra no tiene días cargados.")

            conn.execute(
                "UPDATE member_workout_assignments SET active=0 WHERE member_id=? AND active=1", (member_id,)
            )
            cur = conn.execute("""INSERT INTO member_workout_assignments
                (member_id, template_id, routine_name, routine_description, start_date, assigned_at, active)
                VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (member_id, template_id, template["name"], template["description"] or "",
                 start_date, datetime.now().isoformat(timespec="seconds")))
            assignment_id = cur.lastrowid

            for day in days:
                day_cur = conn.execute("""INSERT INTO member_workout_days
                    (assignment_id, weekday, muscle_groups, notes) VALUES (?, ?, ?, ?)""",
                    (assignment_id, day["weekday"], day["muscle_groups"] or "", day["notes"] or ""))
                exercises = conn.execute("""SELECT * FROM workout_template_exercises
                    WHERE day_id=? ORDER BY exercise_order, id""", (day["id"],)).fetchall()
                for ex in exercises:
                    conn.execute("""INSERT INTO member_workout_exercises
                        (day_id, exercise_order, name, sets, reps, reference_weight, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (day_cur.lastrowid, ex["exercise_order"], ex["name"], ex["sets"],
                         ex["reps"], ex["reference_weight"], ex["notes"]))
            return assignment_id

    def get_member_workout_assignment(self, member_id, assignment_id=None):
        with self.connection() as conn:
            if assignment_id is None:
                assignment = conn.execute("""SELECT * FROM member_workout_assignments
                    WHERE member_id=? AND active=1 ORDER BY id DESC LIMIT 1""", (member_id,)).fetchone()
            else:
                assignment = conn.execute("""SELECT * FROM member_workout_assignments
                    WHERE member_id=? AND id=?""", (member_id, assignment_id)).fetchone()
            if not assignment:
                return None
            days = conn.execute("SELECT * FROM member_workout_days WHERE assignment_id=? ORDER BY weekday", (assignment["id"],)).fetchall()
            result = {"assignment": dict(assignment), "days": []}
            for day in days:
                exercises = conn.execute("""SELECT * FROM member_workout_exercises
                    WHERE day_id=? ORDER BY exercise_order, id""", (day["id"],)).fetchall()
                result["days"].append({"day": dict(day), "exercises": [dict(e) for e in exercises]})
            return result

    def get_member_workout_history(self, member_id):
        with self.connection() as conn:
            rows = conn.execute("""SELECT id, routine_name, start_date, assigned_at, active
                FROM member_workout_assignments WHERE member_id=? ORDER BY id DESC""", (member_id,)).fetchall()
            return [dict(row) for row in rows]

