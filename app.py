from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)

# =========================================================
# APPLICATION SETTINGS
# =========================================================

app.secret_key = "EventHub_Final_Demo_Secret_2026"

DATABASE = "database.db"

# Demo admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    conn = get_db()

    # -----------------------------------------------------
    # EVENTS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT,
            capacity INTEGER NOT NULL
        )
    """)

    # -----------------------------------------------------
    # BOOKINGS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            seats INTEGER NOT NULL,
            booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)

    # -----------------------------------------------------
    # ATTENDANCE
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'Absent',
            FOREIGN KEY (booking_id) REFERENCES bookings(id)
        )
    """)

    # -----------------------------------------------------
    # FEEDBACK
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comments TEXT,
            feedback_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)

    # -----------------------------------------------------
    # SAMPLE EVENTS
    # -----------------------------------------------------

    event_count = conn.execute("""
        SELECT COUNT(*)
        FROM events
    """).fetchone()[0]

    if event_count == 0:

        sample_events = [

            (
                "Tech Innovation Summit",
                "Technology",
                "2026-09-10",
                "Pune",
                "A technology event featuring innovation, artificial intelligence, emerging technologies and the future of digital transformation.",
                100
            ),

            (
                "CodeFest 2026",
                "Coding",
                "2026-09-15",
                "Mumbai",
                "A coding competition designed for students, developers and technology enthusiasts to demonstrate their programming skills.",
                80
            ),

            (
                "Cultural Night",
                "Cultural",
                "2026-09-20",
                "Pune",
                "An exciting evening celebrating music, dance, art and cultural performances from different communities.",
                150
            ),

            (
                "Annual Sports Meet",
                "Sports",
                "2026-09-25",
                "Nashik",
                "An inter-college sports event featuring competitions, teamwork, fitness activities and exciting sporting events.",
                200
            )

        ]

        conn.executemany("""
            INSERT INTO events
            (
                name,
                category,
                date,
                location,
                description,
                capacity
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_events)

    # -----------------------------------------------------
    # CREATE ATTENDANCE FOR EXISTING BOOKINGS
    # -----------------------------------------------------

    bookings_without_attendance = conn.execute("""
        SELECT bookings.id
        FROM bookings
        LEFT JOIN attendance
        ON bookings.id = attendance.booking_id
        WHERE attendance.id IS NULL
    """).fetchall()

    for booking in bookings_without_attendance:

        conn.execute("""
            INSERT INTO attendance
            (
                booking_id,
                status
            )
            VALUES (?, ?)
        """, (
            booking["id"],
            "Absent"
        ))

    conn.commit()
    conn.close()
# =========================================================
# INITIALIZE DATABASE
# =========================================================
init_db()


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def admin_required():

    return session.get("admin_logged_in") is True


def get_available_seats(conn, event_id):

    event = conn.execute("""
        SELECT capacity
        FROM events
        WHERE id = ?
    """, (event_id,)).fetchone()

    if event is None:
        return 0

    booked = conn.execute("""
        SELECT COALESCE(SUM(seats), 0)
        FROM bookings
        WHERE event_id = ?
    """, (event_id,)).fetchone()[0]

    return max(event["capacity"] - booked, 0)


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    conn = get_db()

    events = conn.execute("""
        SELECT
            events.*,
            COALESCE(
                (
                    SELECT SUM(bookings.seats)
                    FROM bookings
                    WHERE bookings.event_id = events.id
                ),
                0
            ) AS booked_seats
        FROM events
        ORDER BY date
        LIMIT 6
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        events=events
    )


# =========================================================
# EVENTS PAGE
# =========================================================

@app.route("/events")
def events():

    conn = get_db()

    events = conn.execute("""
        SELECT
            events.*,
            COALESCE(
                (
                    SELECT SUM(bookings.seats)
                    FROM bookings
                    WHERE bookings.event_id = events.id
                ),
                0
            ) AS booked_seats
        FROM events
        ORDER BY date
    """).fetchall()

    conn.close()

    return render_template(
        "events.html",
        events=events
    )


# =========================================================
# EVENT DETAILS
# =========================================================

@app.route("/event/<int:event_id>")
def event_details(event_id):

    conn = get_db()

    event = conn.execute("""
        SELECT
            events.*,
            COALESCE(
                (
                    SELECT SUM(bookings.seats)
                    FROM bookings
                    WHERE bookings.event_id = events.id
                ),
                0
            ) AS booked_seats
        FROM events
        WHERE events.id = ?
    """, (event_id,)).fetchone()

    if event is None:

        conn.close()

        return "Event not found", 404

    available_seats = max(
        event["capacity"] - event["booked_seats"],
        0
    )

    feedback = conn.execute("""
        SELECT
            name,
            rating,
            comments,
            feedback_date
        FROM feedback
        WHERE event_id = ?
        ORDER BY feedback_date DESC
        LIMIT 5
    """, (event_id,)).fetchall()

    average_rating = conn.execute("""
        SELECT COALESCE(AVG(rating), 0)
        FROM feedback
        WHERE event_id = ?
    """, (event_id,)).fetchone()[0]

    conn.close()

    return render_template(
        "event_details.html",
        event=event,
        available_seats=available_seats,
        feedback=feedback,
        average_rating=round(average_rating, 1)
    )


# =========================================================
# EVENT REGISTRATION
# =========================================================

@app.route(
    "/register/<int:event_id>",
    methods=["GET", "POST"]
)
def register(event_id):

    conn = get_db()

    event = conn.execute("""
        SELECT *
        FROM events
        WHERE id = ?
    """, (event_id,)).fetchone()

    if event is None:

        conn.close()

        return "Event not found", 404

    available_seats = get_available_seats(
        conn,
        event_id
    )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        try:

            seats = int(
                request.form.get(
                    "seats",
                    "1"
                )
            )

        except ValueError:

            conn.close()

            return "Invalid number of seats.", 400

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not name:

            conn.close()

            return "Please enter your name.", 400

        if not email:

            conn.close()

            return "Please enter your email.", 400

        if not phone:

            conn.close()

            return "Please enter your phone number.", 400

        if seats < 1:

            conn.close()

            return "Number of seats must be at least 1.", 400

        if seats > available_seats:

            conn.close()

            return (
                f"Only {available_seats} seat(s) "
                f"are currently available.",
                400
            )

        # -------------------------------------------------
        # CREATE BOOKING
        # -------------------------------------------------

        cursor = conn.execute("""
            INSERT INTO bookings
            (
                event_id,
                name,
                email,
                phone,
                seats
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            event_id,
            name,
            email,
            phone,
            seats
        ))

        booking_id = cursor.lastrowid

        # -------------------------------------------------
        # CREATE ATTENDANCE RECORD
        # -------------------------------------------------

        conn.execute("""
            INSERT INTO attendance
            (
                booking_id,
                status
            )
            VALUES (?, ?)
        """, (
            booking_id,
            "Absent"
        ))

        conn.commit()
        conn.close()

        return render_template(
            "booking_success.html",
            event=event,
            name=name,
            email=email,
            seats=seats
        )

    conn.close()

    return render_template(
        "register.html",
        event=event,
        available_seats=available_seats
    )


# =========================================================
# FEEDBACK
# =========================================================

@app.route(
    "/feedback/<int:event_id>",
    methods=["GET", "POST"]
)
def feedback(event_id):

    conn = get_db()

    event = conn.execute("""
        SELECT *
        FROM events
        WHERE id = ?
    """, (event_id,)).fetchone()

    if event is None:

        conn.close()

        return "Event not found", 404

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        comments = request.form.get(
            "comments",
            ""
        ).strip()

        try:

            rating = int(
                request.form.get(
                    "rating",
                    "5"
                )
            )

        except ValueError:

            rating = 5

        if not name or not email:

            conn.close()

            return (
                "Name and email are required.",
                400
            )

        if rating < 1 or rating > 5:

            conn.close()

            return (
                "Rating must be between 1 and 5.",
                400
            )

        conn.execute("""
            INSERT INTO feedback
            (
                event_id,
                name,
                email,
                rating,
                comments
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            event_id,
            name,
            email,
            rating,
            comments
        ))

        conn.commit()
        conn.close()

        return render_template(
            "feedback.html",
            event=event,
            submitted=True
        )

    conn.close()

    return render_template(
        "feedback.html",
        event=event,
        submitted=False
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session["admin_logged_in"] = True

            return redirect(
                url_for("admin")
            )

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template(
        "login.html",
        error=None
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin():

    if not admin_required():

        return redirect(
            url_for("login")
        )

    conn = get_db()

    # -----------------------------------------------------
    # MAIN STATISTICS
    # -----------------------------------------------------

    total_events = conn.execute("""
        SELECT COUNT(*)
        FROM events
    """).fetchone()[0]

    total_bookings = conn.execute("""
        SELECT COUNT(*)
        FROM bookings
    """).fetchone()[0]

    total_seats = conn.execute("""
        SELECT COALESCE(SUM(seats), 0)
        FROM bookings
    """).fetchone()[0]

    total_capacity = conn.execute("""
        SELECT COALESCE(SUM(capacity), 0)
        FROM events
    """).fetchone()[0]

    total_feedback = conn.execute("""
        SELECT COUNT(*)
        FROM feedback
    """).fetchone()[0]

    present_count = conn.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE status = 'Present'
    """).fetchone()[0]

    absent_count = conn.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE status = 'Absent'
    """).fetchone()[0]

    average_rating = conn.execute("""
        SELECT COALESCE(AVG(rating), 0)
        FROM feedback
    """).fetchone()[0]

    # -----------------------------------------------------
    # EVENTS
    # -----------------------------------------------------

    events = conn.execute("""
        SELECT
            events.*,

            COALESCE(
                (
                    SELECT SUM(bookings.seats)
                    FROM bookings
                    WHERE bookings.event_id = events.id
                ),
                0
            ) AS booked_seats

        FROM events

        ORDER BY date
    """).fetchall()

    # -----------------------------------------------------
    # BOOKINGS
    # -----------------------------------------------------

    bookings = conn.execute("""
        SELECT

            bookings.id,
            bookings.name,
            bookings.email,
            bookings.phone,
            bookings.seats,
            bookings.booking_date,

            events.name AS event_name,

            COALESCE(
                attendance.status,
                'Absent'
            ) AS attendance_status

        FROM bookings

        JOIN events
        ON bookings.event_id = events.id

        LEFT JOIN attendance
        ON bookings.id = attendance.booking_id

        ORDER BY bookings.booking_date DESC
    """).fetchall()

    # -----------------------------------------------------
    # FEEDBACK
    # -----------------------------------------------------

    feedback_list = conn.execute("""
        SELECT

            feedback.name,
            feedback.email,
            feedback.rating,
            feedback.comments,
            feedback.feedback_date,

            events.name AS event_name

        FROM feedback

        JOIN events
        ON feedback.event_id = events.id

        ORDER BY feedback.feedback_date DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin.html",

        total_events=total_events,

        total_bookings=total_bookings,

        total_seats=total_seats,

        total_capacity=total_capacity,

        total_feedback=total_feedback,

        present_count=present_count,

        absent_count=absent_count,

        average_rating=round(
            average_rating,
            1
        ),

        events=events,

        bookings=bookings,

        feedback_list=feedback_list
    )


# =========================================================
# ADD EVENT
# =========================================================

@app.route(
    "/admin/event/add",
    methods=["POST"]
)
def add_event():

    if not admin_required():

        return redirect(
            url_for("login")
        )

    name = request.form.get(
        "name",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    date = request.form.get(
        "date",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    try:

        capacity = int(
            request.form.get(
                "capacity",
                "0"
            )
        )

    except ValueError:

        capacity = 0

    if (
        not name
        or not category
        or not date
        or not location
        or capacity <= 0
    ):

        return (
            "Please enter valid event details.",
            400
        )

    conn = get_db()

    conn.execute("""
        INSERT INTO events
        (
            name,
            category,
            date,
            location,
            description,
            capacity
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        name,
        category,
        date,
        location,
        description,
        capacity
    ))

    conn.commit()
    conn.close()

    return redirect(
        url_for("admin")
    )


# =========================================================
# DELETE EVENT
# =========================================================

@app.route(
    "/admin/event/delete/<int:event_id>",
    methods=["POST"]
)
def delete_event(event_id):

    if not admin_required():

        return redirect(
            url_for("login")
        )

    conn = get_db()

    # Delete attendance for bookings
    conn.execute("""
        DELETE FROM attendance
        WHERE booking_id IN (
            SELECT id
            FROM bookings
            WHERE event_id = ?
        )
    """, (event_id,))

    # Delete bookings
    conn.execute("""
        DELETE FROM bookings
        WHERE event_id = ?
    """, (event_id,))

    # Delete feedback
    conn.execute("""
        DELETE FROM feedback
        WHERE event_id = ?
    """, (event_id,))

    # Delete event
    conn.execute("""
        DELETE FROM events
        WHERE id = ?
    """, (event_id,))

    conn.commit()
    conn.close()

    return redirect(
        url_for("admin")
    )


# =========================================================
# ATTENDANCE
# =========================================================

@app.route(
    "/admin/attendance/<int:booking_id>",
    methods=["POST"]
)
def mark_attendance(booking_id):

    if not admin_required():

        return redirect(
            url_for("login")
        )

    status = request.form.get(
        "status",
        "Absent"
    )

    if status not in [
        "Present",
        "Absent"
    ]:

        status = "Absent"

    conn = get_db()

    existing = conn.execute("""
        SELECT id
        FROM attendance
        WHERE booking_id = ?
    """, (booking_id,)).fetchone()

    if existing:

        conn.execute("""
            UPDATE attendance

            SET status = ?

            WHERE booking_id = ?
        """, (
            status,
            booking_id
        ))

    else:

        conn.execute("""
            INSERT INTO attendance
            (
                booking_id,
                status
            )
            VALUES (?, ?)
        """, (
            booking_id,
            status
        ))

    conn.commit()
    conn.close()

    return redirect(
        url_for("admin")
    )


# =========================================================
# REPORTS
# =========================================================

@app.route("/admin/reports")
def reports():

    if not admin_required():

        return redirect(
            url_for("login")
        )

    conn = get_db()

    # -----------------------------------------------------
    # EVENT REPORTS
    # -----------------------------------------------------

    event_reports = conn.execute("""
        SELECT

            events.id,
            events.name,
            events.category,
            events.date,
            events.capacity,

            COALESCE(
                (
                    SELECT SUM(bookings.seats)
                    FROM bookings
                    WHERE bookings.event_id = events.id
                ),
                0
            ) AS booked_seats,

            (
                SELECT COUNT(*)
                FROM bookings
                WHERE bookings.event_id = events.id
            ) AS registrations,

            (
                SELECT COUNT(*)
                FROM feedback
                WHERE feedback.event_id = events.id
            ) AS feedback_count,

            COALESCE(
                (
                    SELECT AVG(feedback.rating)
                    FROM feedback
                    WHERE feedback.event_id = events.id
                ),
                0
            ) AS average_rating

        FROM events

        ORDER BY events.date
    """).fetchall()

    # -----------------------------------------------------
    # GLOBAL REPORT STATISTICS
    # -----------------------------------------------------

    total_events = conn.execute("""
        SELECT COUNT(*)
        FROM events
    """).fetchone()[0]

    total_bookings = conn.execute("""
        SELECT COUNT(*)
        FROM bookings
    """).fetchone()[0]

    total_seats = conn.execute("""
        SELECT COALESCE(SUM(seats), 0)
        FROM bookings
    """).fetchone()[0]

    total_capacity = conn.execute("""
        SELECT COALESCE(SUM(capacity), 0)
        FROM events
    """).fetchone()[0]

    present = conn.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE status = 'Present'
    """).fetchone()[0]

    absent = conn.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE status = 'Absent'
    """).fetchone()[0]

    feedback_count = conn.execute("""
        SELECT COUNT(*)
        FROM feedback
    """).fetchone()[0]

    average_rating = conn.execute("""
        SELECT COALESCE(AVG(rating), 0)
        FROM feedback
    """).fetchone()[0]

    conn.close()

    occupancy = 0

    if total_capacity > 0:

        occupancy = round(
            (total_seats / total_capacity) * 100,
            1
        )

    attendance_total = present + absent

    attendance_rate = 0

    if attendance_total > 0:

        attendance_rate = round(
            (present / attendance_total) * 100,
            1
        )

    return render_template(
        "reports.html",

        event_reports=event_reports,

        total_events=total_events,

        total_bookings=total_bookings,

        total_seats=total_seats,

        total_capacity=total_capacity,

        present=present,

        absent=absent,

        feedback_count=feedback_count,

        average_rating=round(
            average_rating,
            1
        ),

        occupancy=occupancy,

        attendance_rate=attendance_rate
    )


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True
    )
