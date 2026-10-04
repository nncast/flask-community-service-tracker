import csv
import re
from datetime import datetime, date, timedelta
from functools import wraps
from io import StringIO

from flask import render_template, request, redirect, url_for, flash, session, g, Response
from werkzeug.security import generate_password_hash, check_password_hash

from app import app, db
from models import (
    User, AcademicYear, Semester, YearLevel, Student,
    Event, EventAttendance, EventAttendanceHistory,
    ROLES, USER_STATUSES, STUDENT_STATUSES, SEMESTER_NAMES
)

ACADEMIC_YEAR_PATTERN = re.compile(r"^(\d{4})-(\d{4})$")


# -------------------- Access control --------------------
@app.before_request
def load_current_user():
    """Re-check the logged-in user on every request so deleted/deactivated users
    are logged out and role changes take effect immediately."""
    g.user = None
    if request.endpoint == "static":
        return
    user_id = session.get("user_id")
    if user_id is None:
        return
    user = db.session.get(User, user_id)
    if user is None or user.status != "active":
        session.clear()
        return
    g.user = user
    session["username"] = user.username
    session["role"] = user.role


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please login first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please login first.", "error")
            return redirect(url_for("login"))
        if g.user.role != "admin":
            flash("You do not have permission to access this page.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


# -------------------- Helpers --------------------
def parse_date(value):
    """'YYYY-MM-DD' -> date, or None when empty/invalid."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date() if value else None
    except ValueError:
        return None


def clean(value):
    return (value or "").strip()


def semester_for_date(d):
    """Semester whose date range contains d. A date in the break between two
    semesters of the same academic year belongs to the semester that just ended."""
    sem = Semester.query.filter(Semester.start_date <= d, Semester.end_date >= d).order_by(Semester.id).first()
    if sem:
        return sem
    previous = Semester.query.filter(Semester.end_date < d).order_by(Semester.end_date.desc()).first()
    if previous:
        next_in_same_ay = Semester.query.filter(
            Semester.academic_year_id == previous.academic_year_id,
            Semester.start_date > d
        ).first()
        if next_in_same_ay:
            return previous
    return None


def reassign_event_semesters():
    """Keep every event linked to the right semester after semester dates change."""
    for event in Event.query.all():
        sem = semester_for_date(event.date)
        event.semester_id = sem.id if sem else None


def resolve_target_year_levels(selected, semester):
    """Turn the submitted year-level checkboxes into (target_years value, [YearLevel ids]).
    "All" means all year levels of the event's academic year, not of every year."""
    if "all" in selected:
        query = YearLevel.query
        if semester:
            query = query.filter_by(academic_year_id=semester.academic_year_id)
        return "all", [yl.id for yl in query.all()]
    ids = {int(x) for x in selected if x.isdigit()}
    ids = sorted(yl.id for yl in YearLevel.query.filter(YearLevel.id.in_(ids)).all()) if ids else []
    return ",".join(str(i) for i in ids), ids


def event_targets_year_level(event, year_level):
    if event.target_years == "all":
        return event.semester is None or event.semester.academic_year_id == year_level.academic_year_id
    return year_level.id in event.target_year_ids


def new_attendance(event, student):
    # No sign-in/out yet, so the student owes the full required hours.
    # Both parents are set, otherwise the delete-orphan cascades reject the record.
    return EventAttendance(event=event, student=student,
                           accumulated_hours=EventAttendance.hours_owed(event.required_hours, False, False))


def sync_event_attendance(event, year_level_ids):
    """Add attendance for newly targeted active students and drop untouched records
    of students whose year level is no longer targeted (records with real
    sign-ins or history are kept)."""
    existing = {att.student_id for att in event.attendance}
    for att in list(event.attendance):
        untouched = not att.timed_in and not att.timed_out and not att.history_logs
        if att.student.year_level_id not in year_level_ids and untouched:
            event.attendance.remove(att)
    if year_level_ids:
        students = Student.query.filter(Student.status == "active",
                                        Student.year_level_id.in_(year_level_ids)).all()
        for student in students:
            if student.id not in existing:
                db.session.add(new_attendance(event, student))


def bind_student_to_upcoming_events(student, year_level):
    """A student added (or moved) mid-year joins the upcoming events of their year level."""
    if student.status != "active":
        return
    already = {att.event_id for att in student.event_attendances}
    for event in Event.query.filter(Event.date >= date.today()).all():
        if event.id not in already and event_targets_year_level(event, year_level):
            db.session.add(new_attendance(event, student))


def set_attendance(attendance, timed_in, timed_out, reason):
    """Update sign-in/out, recalculate hours and log the change. Returns True if hours changed."""
    old_hours = attendance.accumulated_hours or 0.0
    attendance.timed_in = timed_in
    attendance.timed_out = timed_out
    attendance.update_hours()
    if old_hours == attendance.accumulated_hours:
        return False
    db.session.add(EventAttendanceHistory(
        attendance=attendance,
        old_hours=old_hours,
        new_hours=attendance.accumulated_hours,
        changed_by=g.user.id,
        reason=reason
    ))
    return True


def academic_year_ranges():
    """Semester date ranges per academic year, used by the event forms' JavaScript."""
    return [
        {
            "id": ay.id,
            "year": ay.year,
            "semesters": [
                {"start": s.start_date.isoformat() if s.start_date else None,
                 "end": s.end_date.isoformat() if s.end_date else None}
                for s in ay.semesters
            ],
        }
        for ay in AcademicYear.query.order_by(AcademicYear.year.desc()).all()
    ]


# -------------------- Authentication --------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = clean(request.form.get("username"))
        password = request.form.get("password") or ""
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            if user.status != "active":
                flash("This account is inactive. Please contact an administrator.", "error")
                return redirect(url_for("login"))
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    # Total students (active only)
    total_students = Student.query.filter_by(status='active').count()

    # Total events
    total_events = Event.query.count()

    # Upcoming events (today onwards) - Event.date is a date, so compare with a date
    upcoming_query = Event.query.filter(Event.date >= date.today())
    upcoming_count = upcoming_query.count()
    upcoming_events = upcoming_query.order_by(Event.date).limit(5).all()

    # Recent attendance changes (last 7 days)
    one_week_ago = datetime.now() - timedelta(days=7)
    recent_query = EventAttendanceHistory.query.filter(EventAttendanceHistory.changed_at >= one_week_ago)
    recent_count = recent_query.count()
    recent_changes = recent_query.order_by(EventAttendanceHistory.changed_at.desc()).limit(5).all()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        total_events=total_events,
        upcoming_count=upcoming_count,
        upcoming_events=upcoming_events,
        recent_count=recent_count,
        recent_changes=recent_changes
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))

# -------------------- Users CRUD --------------------
@app.route("/users")
@admin_required
def users():
    search = request.args.get("search", "").strip()
    role_filter = request.args.get("role", "")
    status_filter = request.args.get("status", "")

    query = User.query
    if search:
        query = query.filter(User.username.like(f"%{search}%"))
    if role_filter:
        query = query.filter_by(role=role_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)

    return render_template("users.html",
                           users=query.order_by(User.id).all(),
                           search=search,
                           role_filter=role_filter,
                           status_filter=status_filter)


@app.route("/users/add", methods=["POST"])
@admin_required
def add_user():
    username = clean(request.form.get("username"))
    password = request.form.get("password") or ""
    role = request.form.get("role")
    status = request.form.get("status")

    if not username or not password:
        flash("Username and password are required.", "error")
        return redirect(url_for("users"))
    if len(username) > 50:
        flash("Username must be 50 characters or fewer.", "error")
        return redirect(url_for("users"))
    if role not in ROLES or status not in USER_STATUSES:
        flash("Invalid role or status.", "error")
        return redirect(url_for("users"))
    if User.query.filter_by(username=username).first():
        flash("Username already exists.", "error")
        return redirect(url_for("users"))

    user = User(username=username,
                password=generate_password_hash(password),
                role=role,
                status=status)
    db.session.add(user)
    db.session.commit()
    flash("User added successfully.", "success")
    return redirect(url_for("users"))

@app.route('/edit_user/<int:user_id>', methods=['POST'])
@admin_required
def edit_user(user_id):
    user = db.get_or_404(User, user_id)

    username = clean(request.form.get('username'))
    role = request.form.get('role')
    # Unchecked status switch is not submitted, so it means 'inactive'
    status = 'active' if request.form.get('status') == 'active' else 'inactive'

    if not username or len(username) > 50:
        flash('Username is required (50 characters max).', 'error')
        return redirect(url_for('users'))
    if role not in ROLES:
        flash('Invalid role.', 'error')
        return redirect(url_for('users'))
    if User.query.filter(User.username == username, User.id != user.id).first():
        flash(f'Username "{username}" is already taken.', 'error')
        return redirect(url_for('users'))
    if user.id == g.user.id and (role != 'admin' or status != 'active'):
        flash('You cannot remove your own admin role or deactivate your own account.', 'error')
        return redirect(url_for('users'))

    user.username = username
    user.role = role
    user.status = status

    # Only update password if a new one is entered
    new_password = request.form.get('password')
    if new_password:
        user.password = generate_password_hash(new_password)

    db.session.commit()
    flash('User updated successfully.', 'success')
    return redirect(url_for('users'))


@app.route("/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == g.user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("users"))
    if EventAttendanceHistory.query.filter_by(changed_by=user.id).first():
        flash(f'"{user.username}" has attendance history records. Deactivate the account instead so the history stays accurate.', "error")
        return redirect(url_for("users"))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.", "success")
    return redirect(url_for("users"))


# -------------------- Academic Years --------------------
def read_academic_year_form():
    """Validate the academic year form. Returns (data, error message)."""
    year = clean(request.form.get("year"))
    status = request.form.get("status", "active")
    match = ACADEMIC_YEAR_PATTERN.match(year)
    if not match or int(match.group(2)) != int(match.group(1)) + 1:
        return None, "Academic year must look like 2025-2026."
    if status not in USER_STATUSES:
        return None, "Invalid status."

    dates = {}
    for field in ("start1", "end1", "start2", "end2"):
        raw = request.form.get(field)
        dates[field] = parse_date(raw)
        if raw and dates[field] is None:
            return None, "Invalid semester date."
    for start, end, label in (("start1", "end1", "1st"), ("start2", "end2", "2nd")):
        if dates[start] and dates[end] and dates[start] > dates[end]:
            return None, f"{label} semester start date must be before its end date."
    if dates["end1"] and dates["start2"] and dates["start2"] <= dates["end1"]:
        return None, "2nd semester must start after the 1st semester ends."
    return {"year": year, "status": status, **dates}, None


@app.route("/academic_years")
@admin_required
def academic_years():
    years = AcademicYear.query.order_by(AcademicYear.year.desc()).all()
    return render_template("academic_years.html", years=years)


@app.route("/academic_years/add", methods=["POST"])
@admin_required
def add_academic_year():
    data, error = read_academic_year_form()
    if error:
        flash(error, "error")
        return redirect(url_for("academic_years"))
    if AcademicYear.query.filter_by(year=data["year"]).first():
        flash("Academic year already exists.", "error")
        return redirect(url_for("academic_years"))

    ay = AcademicYear(year=data["year"], status=data["status"])
    ay.semesters = [
        Semester(name="1st Semester", start_date=data["start1"], end_date=data["end1"]),
        Semester(name="2nd Semester", start_date=data["start2"], end_date=data["end2"]),
    ]
    db.session.add(ay)
    db.session.flush()
    reassign_event_semesters()
    db.session.commit()
    flash("Academic year added successfully.", "success")
    return redirect(url_for("academic_years"))


@app.route("/academic_years/edit/<int:ay_id>", methods=["POST"])
@admin_required
def edit_academic_year(ay_id):
    ay = db.get_or_404(AcademicYear, ay_id)
    data, error = read_academic_year_form()
    if error:
        flash(error, "error")
        return redirect(url_for("academic_years"))
    if AcademicYear.query.filter(AcademicYear.year == data["year"], AcademicYear.id != ay.id).first():
        flash("Another academic year already uses that name.", "error")
        return redirect(url_for("academic_years"))

    ay.year = data["year"]
    ay.status = data["status"]

    # Academic years created by student promotion may be missing semesters
    while len(ay.semesters) < 2:
        ay.semesters.append(Semester(name=SEMESTER_NAMES[len(ay.semesters)]))

    sem1, sem2 = ay.semesters[0], ay.semesters[1]
    sem1.start_date, sem1.end_date = data["start1"], data["end1"]
    sem2.start_date, sem2.end_date = data["start2"], data["end2"]

    db.session.flush()
    reassign_event_semesters()
    db.session.commit()
    flash("Academic year updated successfully.", "success")
    return redirect(url_for("academic_years"))


@app.route("/academic_years/delete/<int:ay_id>", methods=["POST"])
@admin_required
def delete_academic_year(ay_id):
    ay = db.get_or_404(AcademicYear, ay_id)
    db.session.delete(ay)
    db.session.flush()
    reassign_event_semesters()
    db.session.commit()
    flash("Academic year deleted successfully.", "success")
    return redirect(url_for("academic_years"))


# -------------------- Year Levels --------------------
def read_year_level_form():
    level = request.form.get("level", type=int)
    section = clean(request.form.get("section"))
    academic_year_id = request.form.get("academic_year", type=int)
    if level is None or not 1 <= level <= 4:
        return None, "Level must be between 1 and 4."
    if not section or len(section) > 5:
        return None, "Section is required (5 characters max)."
    if academic_year_id is None or db.session.get(AcademicYear, academic_year_id) is None:
        return None, "Please select a valid academic year."
    return {"level": level, "section": section, "academic_year_id": academic_year_id}, None


@app.route("/year_levels")
@admin_required
def year_levels():
    search = request.args.get("search", "").strip()
    ay_filter = request.args.get("academic_year", "")
    query = YearLevel.query.join(AcademicYear)
    if search:
        query = query.filter(
            (db.cast(YearLevel.level, db.String).like(f"%{search}%")) |
            (YearLevel.section.like(f"%{search}%"))
        )
    if ay_filter.isdigit():
        query = query.filter(YearLevel.academic_year_id == int(ay_filter))
    year_levels_list = query.order_by(AcademicYear.year.desc(), YearLevel.level, YearLevel.section).all()
    academic_years = AcademicYear.query.order_by(AcademicYear.year.desc()).all()
    return render_template("year_levels.html", year_levels=year_levels_list, academic_years=academic_years,
                           search=search, ay_filter=ay_filter)


@app.route("/year_levels/add", methods=["POST"])
@admin_required
def add_year_level():
    data, error = read_year_level_form()
    if error:
        flash(error, "error")
        return redirect(url_for("year_levels"))

    if YearLevel.query.filter_by(**data).first():
        flash("Year level + section already exists for this academic year.", "error")
        return redirect(url_for("year_levels"))

    db.session.add(YearLevel(**data))
    db.session.commit()
    flash("Year level added successfully.", "success")
    return redirect(url_for("year_levels"))


@app.route("/year_levels/edit/<int:yl_id>", methods=["POST"])
@admin_required
def edit_year_level(yl_id):
    yl = db.get_or_404(YearLevel, yl_id)
    data, error = read_year_level_form()
    if error:
        flash(error, "error")
        return redirect(url_for("year_levels"))

    if YearLevel.query.filter_by(**data).filter(YearLevel.id != yl.id).first():
        flash("Year level + section already exists for this academic year.", "error")
        return redirect(url_for("year_levels"))

    yl.level = data["level"]
    yl.section = data["section"]
    yl.academic_year_id = data["academic_year_id"]
    db.session.commit()
    flash("Year level updated successfully.", "success")
    return redirect(url_for("year_levels"))


@app.route("/year_levels/delete/<int:yl_id>", methods=["POST"])
@admin_required
def delete_year_level(yl_id):
    yl = db.get_or_404(YearLevel, yl_id)
    db.session.delete(yl)
    db.session.commit()
    flash("Year level deleted successfully.", "success")
    return redirect(url_for("year_levels"))

# -------------------- Students --------------------
def read_student_form():
    data = {
        "student_id": clean(request.form.get("student_id")),
        "fname": clean(request.form.get("fname")),
        "mname": clean(request.form.get("mname")) or None,
        "lname": clean(request.form.get("lname")),
        "status": request.form.get("status", "active"),
    }
    if not data["student_id"] or len(data["student_id"]) > 8:
        return None, None, "Student ID is required (8 characters max)."
    if not data["fname"] or not data["lname"]:
        return None, None, "First and last name are required."
    if data["status"] not in STUDENT_STATUSES:
        return None, None, "Invalid status."
    year_level = db.session.get(YearLevel, request.form.get("year_level", type=int) or 0)
    if year_level is None:
        return None, None, "Please select a valid year level."
    return data, year_level, None


@app.route("/students")
@admin_required
def students():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "")
    ay_filter = request.args.get("academic_year", "")
    yl_filter = request.args.get("year_level", "")

    query = Student.query.join(YearLevel).join(AcademicYear)

    if search:
        query = query.filter(
            (Student.student_id.like(f"%{search}%")) |
            (Student.fname.like(f"%{search}%")) |
            (Student.lname.like(f"%{search}%"))
        )
    if status_filter:
        query = query.filter(Student.status == status_filter)
    if yl_filter.isdigit():
        query = query.filter(Student.year_level_id == int(yl_filter))
    if ay_filter.isdigit():
        query = query.filter(YearLevel.academic_year_id == int(ay_filter))

    students_list = query.order_by(Student.student_id).all()
    academic_years = AcademicYear.query.order_by(AcademicYear.year.desc()).all()
    year_levels = YearLevel.query.order_by(YearLevel.level, YearLevel.section).all()

    return render_template("students.html", students=students_list, academic_years=academic_years,
                           year_levels=year_levels, search=search, status_filter=status_filter,
                           ay_filter=ay_filter, yl_filter=yl_filter)


@app.route("/students/add", methods=["POST"])
@admin_required
def add_student():
    data, year_level, error = read_student_form()
    if error:
        flash(error, "error")
        return redirect(url_for("students"))

    if Student.query.filter_by(student_id=data["student_id"]).first():
        flash("Student ID already exists.", "error")
        return redirect(url_for("students"))

    student = Student(year_level_id=year_level.id, **data)
    db.session.add(student)
    db.session.flush()
    bind_student_to_upcoming_events(student, year_level)
    db.session.commit()
    flash("Student added successfully.", "success")
    return redirect(url_for("students"))


@app.route("/students/edit/<int:student_id>", methods=["POST"])
@admin_required
def edit_student(student_id):
    student = db.get_or_404(Student, student_id)
    data, year_level, error = read_student_form()
    if error:
        flash(error, "error")
        return redirect(url_for("students"))

    if Student.query.filter(Student.student_id == data["student_id"], Student.id != student.id).first():
        flash(f'Student ID "{data["student_id"]}" is already used by another student.', "error")
        return redirect(url_for("students"))

    joins_events = student.year_level_id != year_level.id or (student.status != "active" and data["status"] == "active")
    for field, value in data.items():
        setattr(student, field, value)
    student.year_level_id = year_level.id
    if joins_events:
        bind_student_to_upcoming_events(student, year_level)
    db.session.commit()
    flash("Student updated successfully.", "success")
    return redirect(url_for("students"))


@app.route("/students/delete/<int:student_id>", methods=["POST"])
@admin_required
def delete_student(student_id):
    student = db.get_or_404(Student, student_id)
    db.session.delete(student)
    db.session.commit()
    flash("Student deleted successfully.", "success")
    return redirect(url_for("students"))


# -------------------- Events --------------------
@app.route("/events")
@login_required
def events():
    events_list = Event.query.order_by(Event.date.desc()).all()

    # Group by academic year -> semester; events outside every semester go under "Unassigned"
    grouped = {}
    for event in events_list:
        if event.semester:
            ay_name, sem_name = event.semester.academic_year.year, event.semester.name
        else:
            ay_name, sem_name = "Unassigned", "No semester"
        grouped.setdefault(ay_name, {}).setdefault(sem_name, []).append(event)
    unassigned = grouped.pop("Unassigned", None)
    event_groups = [(ay, sorted(sems.items())) for ay, sems in sorted(grouped.items(), reverse=True)]
    if unassigned:
        event_groups.append(("Unassigned", sorted(unassigned.items())))

    year_levels = YearLevel.query.order_by(YearLevel.level, YearLevel.section).all()
    academic_years = AcademicYear.query.order_by(AcademicYear.year.desc()).all()
    return render_template("events.html", events=events_list, event_groups=event_groups,
                           year_levels=year_levels, academic_years=academic_years,
                           ay_ranges=academic_year_ranges())


def read_event_form():
    name = clean(request.form.get("name"))
    event_date = parse_date(request.form.get("date"))
    required_hours = request.form.get("required_hours", type=float)
    if not name:
        return None, "Event name is required."
    if event_date is None:
        return None, "A valid date is required."
    if required_hours is None or required_hours <= 0:
        return None, "Required hours must be greater than 0."
    return {"name": name, "date": event_date, "required_hours": required_hours}, None


@app.route("/events/add", methods=["POST"])
@login_required
def add_event():
    data, error = read_event_form()
    if error:
        flash(error, "error")
        return redirect(url_for("events"))

    semester = semester_for_date(data["date"])
    target_years, year_level_ids = resolve_target_year_levels(request.form.getlist("year_levels"), semester)
    if not year_level_ids:
        flash("Select at least one target year level. The date must fall within an academic year's semesters.", "error")
        return redirect(url_for("events"))

    event = Event(target_years=target_years, semester_id=semester.id if semester else None, **data)
    db.session.add(event)
    sync_event_attendance(event, year_level_ids)
    db.session.commit()

    if semester:
        flash(f"Event created for {semester.academic_year.year} {semester.name}.", "success")
    else:
        flash("Event created, but its date is outside every semester, so it is listed under Unassigned.", "warning")
    return redirect(url_for("events"))

# -------------------- Edit Event --------------------
@app.route("/events/edit/<int:event_id>", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    event = db.get_or_404(Event, event_id)

    if request.method == "POST":
        data, error = read_event_form()
        if error:
            flash(error, "error")
            return redirect(url_for("edit_event", event_id=event.id))

        semester = semester_for_date(data["date"])
        target_years, year_level_ids = resolve_target_year_levels(request.form.getlist("target_years"), semester)
        if not year_level_ids:
            flash("Select at least one target year level.", "error")
            return redirect(url_for("edit_event", event_id=event.id))

        hours_changed = event.required_hours != data["required_hours"]
        event.name = data["name"]
        event.date = data["date"]
        event.required_hours = data["required_hours"]
        event.target_years = target_years
        event.semester_id = semester.id if semester else None

        # Owed hours depend on the required hours, so recalculate existing records
        if hours_changed:
            for att in event.attendance:
                set_attendance(att, att.timed_in, att.timed_out, "Event required hours changed")
        sync_event_attendance(event, year_level_ids)

        db.session.commit()
        flash("Event updated successfully.", "success")
        return redirect(url_for("events"))

    year_levels = YearLevel.query.order_by(YearLevel.level, YearLevel.section).all()
    return render_template(
        "edit_event.html",
        event=event,
        year_levels=year_levels,
        ay_ranges=academic_year_ranges()
    )


# -------------------- Delete Event --------------------
@app.route("/events/delete/<int:event_id>", methods=["POST"])
@login_required
def delete_event(event_id):
    event = db.get_or_404(Event, event_id)
    # Attendance records and their history are removed through the cascade
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted successfully.", "success")
    return redirect(url_for("events"))


# -------------------- Event Attendance --------------------
@app.route("/events/<int:event_id>/attendance")
@login_required
def event_attendance(event_id):
    event = db.get_or_404(Event, event_id)
    attendances = (EventAttendance.query.filter_by(event_id=event_id)
                   .join(Student).order_by(Student.lname, Student.fname).all())
    return render_template("event_attendance.html", event=event, attendances=attendances)


@app.route("/events/<int:event_id>/attendance/save", methods=["POST"])
@login_required
def save_event_attendance(event_id):
    event = db.get_or_404(Event, event_id)

    changed = 0
    for attendance in event.attendance:
        changed += set_attendance(
            attendance,
            bool(request.form.get(f"timed_in_{attendance.id}")),
            bool(request.form.get(f"timed_out_{attendance.id}")),
            f"Updated via {event.name} attendance sheet"
        )

    db.session.commit()
    flash(f"Attendance saved ({changed} change(s)).", "success")
    return redirect(url_for("event_attendance", event_id=event_id))

# -------------------- Attendance Dashboard --------------------
def attendance_scope(ay_id, sem_id):
    """Selected academic year/semester plus the students, year levels and events in it.
    Shared by the dashboard and the CSV export so both show the same data."""
    academic_years = AcademicYear.query.order_by(AcademicYear.year.desc()).all()
    current_ay = next((ay for ay in academic_years if ay.id == ay_id), None)
    if current_ay is None and academic_years:
        current_ay = academic_years[0]   # Default: latest academic year

    semesters = current_ay.semesters if current_ay else []
    current_semester = next((s for s in semesters if s.id == sem_id), None)

    students, year_levels, events = [], [], []
    if current_ay:
        students = (
            Student.query.join(YearLevel)
            .filter(Student.status == "active", YearLevel.academic_year_id == current_ay.id)
            .order_by(Student.lname, Student.fname, Student.mname)
            .all()
        )
        year_levels = (
            YearLevel.query.filter_by(academic_year_id=current_ay.id)
            .order_by(YearLevel.level, YearLevel.section)
            .all()
        )
        sem_ids = [current_semester.id] if current_semester else [s.id for s in semesters]
        events = Event.query.filter(Event.semester_id.in_(sem_ids)).order_by(Event.date).all()

    # (student id, event id) -> attendance, for the students and events shown
    attendance_map = {}
    if students and events:
        records = EventAttendance.query.filter(
            EventAttendance.event_id.in_([e.id for e in events]),
            EventAttendance.student_id.in_([s.id for s in students])
        ).all()
        attendance_map = {(a.student_id, a.event_id): a for a in records}

    return {
        "academic_years": academic_years,
        "current_ay": current_ay,
        "semesters": semesters,
        "current_semester": current_semester,
        "students": students,
        "year_levels": year_levels,
        "events": events,
        "attendance_map": attendance_map,
    }


def student_totals(students, events, attendance_map):
    """Total CS hours owed per student for the events in view."""
    return {
        s.id: round(sum(attendance_map[(s.id, e.id)].accumulated_hours or 0
                        for e in events if (s.id, e.id) in attendance_map), 2)
        for s in students
    }


@app.route("/attendance_dashboard")
@login_required
def attendance_dashboard():
    scope = attendance_scope(request.args.get("academic_year", type=int),
                             request.args.get("semester", type=int))
    totals = student_totals(scope["students"], scope["events"], scope["attendance_map"])

    return render_template(
        "attendance_dashboard.html",
        students=scope["students"],
        events=scope["events"],
        year_levels=scope["year_levels"],
        academic_years=scope["academic_years"],
        semesters=scope["semesters"],
        attendance_map=scope["attendance_map"],
        totals=totals,
        selected_ay_id=scope["current_ay"].id if scope["current_ay"] else None,
        selected_sem_id=scope["current_semester"].id if scope["current_semester"] else None,
        total_hours=round(sum(totals.values()), 2)
    )


@app.route("/attendance_dashboard/save", methods=["POST"])
@login_required
def save_all_attendance():
    # Only the records shown on the page are submitted. Updating every record in the
    # database here would reset attendance for all other academic years/semesters.
    ids = request.form.getlist("attendance_ids", type=int)
    changed = 0
    if ids:
        for attendance in EventAttendance.query.filter(EventAttendance.id.in_(ids)).all():
            changed += set_attendance(
                attendance,
                bool(request.form.get(f"timein_{attendance.id}")),
                bool(request.form.get(f"timeout_{attendance.id}")),
                "Updated via attendance dashboard"
            )

    db.session.commit()
    flash(f"Attendance saved ({changed} change(s)).", "success")
    return redirect(url_for("attendance_dashboard",
                            academic_year=request.form.get("academic_year", type=int),
                            semester=request.form.get("semester", type=int)))



@app.route("/export_attendance")
@login_required
def export_attendance():
    scope = attendance_scope(request.args.get("ay", type=int), request.args.get("semester", type=int))
    students = scope["students"]
    events = scope["events"]
    attendance_map = scope["attendance_map"]

    name_filter = request.args.get("name", "").strip().lower()
    year_level_filter = request.args.get("year_level", "")
    event_filter = request.args.get("event", type=int)

    if name_filter:
        students = [s for s in students
                    if name_filter in s.full_name.lower() or name_filter in f"{s.fname} {s.lname}".lower()]
    if year_level_filter:
        students = [s for s in students if s.year_level.label == year_level_filter]
    if event_filter:
        events = [e for e in events if e.id == event_filter]

    totals = student_totals(students, events, attendance_map)

    # Create CSV in memory
    si = StringIO()
    writer = csv.writer(si)

    # Header row
    header = ["Student ID", "Name", "Year Level", "Total CS Hours"]
    for event in events:
        label = f"{event.name} ({event.date.strftime('%Y-%m-%d')})"
        header += [f"{label} Time In", f"{label} Time Out", f"{label} Hours"]
    writer.writerow(header)

    # Data rows ("-" = student was not targeted by that event)
    for student in students:
        row = [student.student_id, student.full_name, student.year_level.label, totals[student.id]]
        for event in events:
            attendance = attendance_map.get((student.id, event.id))
            if attendance:
                row += ["Yes" if attendance.timed_in else "No",
                        "Yes" if attendance.timed_out else "No",
                        attendance.accumulated_hours]
            else:
                row += ["-", "-", "-"]
        writer.writerow(row)

    ay_name = scope["current_ay"].year if scope["current_ay"] else "all"
    # BOM so Excel opens names with accents (e.g. ñ) correctly
    return Response(
        "﻿" + si.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=attendance_{ay_name}.csv"}
    )
# -------------------- Attendance History --------------------
@app.route("/attendance_history")
@login_required
def attendance_history():
    # Optional time filter
    time_filter = request.args.get("time", "all")  # all, today, week, month
    query = EventAttendanceHistory.query

    now = datetime.now()
    if time_filter == "today":
        query = query.filter(EventAttendanceHistory.changed_at >= now.replace(hour=0, minute=0, second=0, microsecond=0))
    elif time_filter == "week":
        query = query.filter(EventAttendanceHistory.changed_at >= now - timedelta(days=7))
    elif time_filter == "month":
        query = query.filter(EventAttendanceHistory.changed_at >= now - timedelta(days=30))

    logs = query.order_by(EventAttendanceHistory.changed_at.desc()).all()

    return render_template("attendance_history.html", logs=logs, time_filter=time_filter)


# -------------------- Student Promotion --------------------
@app.route("/students/promote/<int:student_id>", methods=["POST"])
@admin_required
def promote_student(student_id):
    student = db.get_or_404(Student, student_id)
    current_yl = student.year_level
    current_ay = current_yl.academic_year

    next_level = current_yl.level + 1
    if next_level > 4:
        student.status = "graduate"
        db.session.commit()
        flash(f"{student.fname} {student.lname} has graduated.", "success")
        return redirect(url_for("students"))

    match = ACADEMIC_YEAR_PATTERN.match(current_ay.year)
    if not match:
        flash(f'Cannot promote: academic year "{current_ay.year}" is not in the YYYY-YYYY format.', "error")
        return redirect(url_for("students"))
    start_year, end_year = int(match.group(1)), int(match.group(2))
    next_ay_str = f"{start_year + 1}-{end_year + 1}"

    next_ay = AcademicYear.query.filter_by(year=next_ay_str).first()
    if not next_ay:
        # Semester dates are left empty for the admin to fill in on the Academic Years page
        next_ay = AcademicYear(year=next_ay_str, status="active",
                               semesters=[Semester(name=n) for n in SEMESTER_NAMES])
        db.session.add(next_ay)
        db.session.flush()

    next_yl = YearLevel.query.filter_by(
        academic_year_id=next_ay.id,
        level=next_level,
        section=current_yl.section
    ).first()
    if not next_yl:
        next_yl = YearLevel(level=next_level, section=current_yl.section, academic_year_id=next_ay.id)
        db.session.add(next_yl)
        db.session.flush()

    student.year_level_id = next_yl.id
    bind_student_to_upcoming_events(student, next_yl)
    db.session.commit()
    flash(f"{student.fname} {student.lname} promoted to {next_yl.label} ({next_ay.year})", "success")
    return redirect(url_for("students"))
