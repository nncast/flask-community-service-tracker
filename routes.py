from flask import render_template, request, redirect, url_for, flash, session
from datetime import datetime,timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from models import (
    User, AcademicYear, Semester, YearLevel, Student,
    Event, EventAttendance, EventAttendanceHistory
)
import csv
from io import StringIO      # <--- required
from flask import Response, request
# -------------------- Authentication --------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            if user.status != "active":
                flash("User is inactive.")
                return redirect(url_for("login"))
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    # Total students (active only)
    total_students = Student.query.filter_by(status='active').count()

    # Total events
    total_events = Event.query.count()

    # Upcoming events (future only)
    upcoming_events = Event.query.filter(Event.date >= datetime.now()).order_by(Event.date).all()

    # Recent attendance changes (last 7 days)
    one_week_ago = datetime.now() - timedelta(days=7)
    recent_changes = EventAttendanceHistory.query.filter(
        EventAttendanceHistory.changed_at >= one_week_ago,
    ).order_by(EventAttendanceHistory.changed_at.desc()).limit(5).all()


    return render_template(
        "dashboard.html",
        username=session.get("username"),
        role=session.get("role"),
        total_students=total_students,
        total_events=total_events,
        upcoming_events=upcoming_events,
        recent_changes=recent_changes
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for("login"))

# -------------------- Users CRUD --------------------
@app.route("/users")
def users():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    # Restrict access to admin only
    if session.get('role') != 'admin':
        flash("You do not have permission to access this page.", "error")
        return redirect(url_for("dashboard"))

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
                           users=query.all(),
                           search=search,
                           role_filter=role_filter,
                           status_filter=status_filter)


@app.route("/users/add", methods=["POST"])
def add_user():
    username = request.form.get("username")
    password = request.form.get("password")
    role = request.form.get("role")
    status = request.form.get("status")

    if User.query.filter_by(username=username).first():
        flash("Username already exists.")
        return redirect(url_for("users"))

    user = User(username=username,
                password=generate_password_hash(password),
                role=role,
                status=status)
    db.session.add(user)
    db.session.commit()
    flash("User added successfully.")
    return redirect(url_for("users"))

@app.route('/edit_user/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if session.get('role') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)

    user.username = request.form.get('username')

    # Only update password if a new one is entered
    new_password = request.form.get('password')
    if new_password:  # skip if empty
        user.password = generate_password_hash(new_password)

    user.role = request.form.get('role')

    # Handle checkbox: if it's not checked, set to 'inactive'
    user.status = 'active' if request.form.get('status') == 'active' else 'inactive'

    db.session.commit()
    flash('User updated successfully.', 'success')
    return redirect(url_for('users'))



@app.route("/users/delete/<int:user_id>")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.")
    return redirect(url_for("users"))


# -------------------- Academic Years --------------------
@app.route("/academic_years")
def academic_years():
    if 'user_id' not in session:
        flash("Please login first.")
        return redirect(url_for("login"))
    years = AcademicYear.query.order_by(AcademicYear.id.desc()).all()
    return render_template("academic_years.html", years=years)


@app.route("/academic_years/add", methods=["POST"])
def add_academic_year():
    year = request.form.get("year")
    status = request.form.get("status", "active")
    start1_str = request.form.get("start1")
    end1_str = request.form.get("end1")
    start2_str = request.form.get("start2")
    end2_str = request.form.get("end2")

    if AcademicYear.query.filter_by(year=year).first():
        flash("Academic year already exists")
        return redirect(url_for("academic_years"))

    ay = AcademicYear(year=year, status=status)
    db.session.add(ay)
    db.session.commit()

    sem1 = Semester(
        academic_year_id=ay.id,
        name="1st Semester",
        start_date=datetime.strptime(start1_str, "%Y-%m-%d").date() if start1_str else None,
        end_date=datetime.strptime(end1_str, "%Y-%m-%d").date() if end1_str else None
    )
    sem2 = Semester(
        academic_year_id=ay.id,
        name="2nd Semester",
        start_date=datetime.strptime(start2_str, "%Y-%m-%d").date() if start2_str else None,
        end_date=datetime.strptime(end2_str, "%Y-%m-%d").date() if end2_str else None
    )
    db.session.add_all([sem1, sem2])
    db.session.commit()
    flash("Academic year added successfully")
    return redirect(url_for("academic_years"))


@app.route("/academic_years/edit/<int:ay_id>", methods=["POST"])
def edit_academic_year(ay_id):
    ay = AcademicYear.query.get_or_404(ay_id)
    ay.year = request.form.get("year")
    ay.status = request.form.get("status", "active")

    if len(ay.semesters) < 2:
        while len(ay.semesters) < 2:
            ay.semesters.append(Semester(academic_year_id=ay.id, name="Missing"))

    sem1 = ay.semesters[0]
    sem2 = ay.semesters[1]

    sem1.start_date = datetime.strptime(request.form.get("start1"), "%Y-%m-%d").date() if request.form.get("start1") else None
    sem1.end_date = datetime.strptime(request.form.get("end1"), "%Y-%m-%d").date() if request.form.get("end1") else None
    sem2.start_date = datetime.strptime(request.form.get("start2"), "%Y-%m-%d").date() if request.form.get("start2") else None
    sem2.end_date = datetime.strptime(request.form.get("end2"), "%Y-%m-%d").date() if request.form.get("end2") else None

    db.session.commit()
    flash("Academic year updated successfully")
    return redirect(url_for("academic_years"))


@app.route("/academic_years/delete/<int:ay_id>")
def delete_academic_year(ay_id):
    ay = AcademicYear.query.get_or_404(ay_id)
    db.session.delete(ay)
    db.session.commit()
    flash("Academic year deleted successfully")
    return redirect(url_for("academic_years"))


# -------------------- Year Levels --------------------
@app.route("/year_levels")
def year_levels():
    search = request.args.get("search", "").strip()
    ay_filter = request.args.get("academic_year", "")
    query = YearLevel.query.join(AcademicYear)
    if search:
        query = query.filter(
            (db.cast(YearLevel.level, db.String).like(f"%{search}%")) |
            (YearLevel.section.like(f"%{search}%"))
        )
    if ay_filter:
        query = query.filter(YearLevel.academic_year_id == int(ay_filter))
    year_levels_list = query.order_by(YearLevel.level, YearLevel.section).all()
    academic_years = AcademicYear.query.order_by(AcademicYear.year.desc()).all()
    return render_template("year_levels.html", year_levels=year_levels_list, academic_years=academic_years,
                           search=search, ay_filter=ay_filter)


@app.route("/year_levels/add", methods=["POST"])
def add_year_level():
    level = int(request.form.get("level"))
    section = request.form.get("section")
    academic_year_id = int(request.form.get("academic_year"))

    if YearLevel.query.filter_by(level=level, section=section, academic_year_id=academic_year_id).first():
        flash("Year level + section already exists for this academic year.")
        return redirect(url_for("year_levels"))

    yl = YearLevel(level=level, section=section, academic_year_id=academic_year_id)
    db.session.add(yl)
    db.session.commit()
    flash("Year level added successfully.")
    return redirect(url_for("year_levels"))


@app.route("/year_levels/edit/<int:yl_id>", methods=["POST"])
def edit_year_level(yl_id):
    yl = YearLevel.query.get_or_404(yl_id)
    yl.level = int(request.form.get("level"))
    yl.section = request.form.get("section")
    yl.academic_year_id = int(request.form.get("academic_year"))
    db.session.commit()
    flash("Year level updated successfully.")
    return redirect(url_for("year_levels"))


@app.route("/year_levels/delete/<int:yl_id>")
def delete_year_level(yl_id):
    yl = YearLevel.query.get_or_404(yl_id)
    db.session.delete(yl)
    db.session.commit()
    flash("Year level deleted successfully.")
    return redirect(url_for("year_levels"))

# -------------------- Students --------------------
@app.route("/students")
def students():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    # Restrict access to admin only
    if session.get('role') != 'admin':
        flash("You do not have permission to access this page.", "error")
        return redirect(url_for("dashboard"))

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
    if yl_filter:
        query = query.filter(Student.year_level_id == int(yl_filter))
    if ay_filter:
        query = query.filter(YearLevel.academic_year_id == int(ay_filter))

    students_list = query.order_by(Student.student_id).all()
    academic_years = AcademicYear.query.order_by(AcademicYear.year.desc()).all()
    year_levels = YearLevel.query.order_by(YearLevel.level, YearLevel.section).all()
    
    return render_template("students.html", students=students_list, academic_years=academic_years,
                           year_levels=year_levels, search=search, status_filter=status_filter,
                           ay_filter=ay_filter, yl_filter=yl_filter)


@app.route("/students/add", methods=["POST"])
def add_student():
    student_id = request.form.get("student_id")
    fname = request.form.get("fname")
    mname = request.form.get("mname")
    lname = request.form.get("lname")
    year_level_id = int(request.form.get("year_level"))
    status = request.form.get("status", "active")

    if Student.query.filter_by(student_id=student_id).first():
        flash("Student ID already exists.")
        return redirect(url_for("students"))

    student = Student(student_id=student_id, fname=fname, mname=mname, lname=lname,
                      year_level_id=year_level_id, status=status)
    db.session.add(student)
    db.session.commit()
    flash("Student added successfully.")
    return redirect(url_for("students"))


@app.route("/students/edit/<int:student_id>", methods=["POST"])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    student.student_id = request.form.get("student_id")
    student.fname = request.form.get("fname")
    student.mname = request.form.get("mname")
    student.lname = request.form.get("lname")
    student.year_level_id = int(request.form.get("year_level"))
    student.status = request.form.get("status")
    db.session.commit()
    flash("Student updated successfully.")
    return redirect(url_for("students"))


@app.route("/students/delete/<int:student_id>")
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    flash("Student deleted successfully.")
    return redirect(url_for("students"))


# -------------------- Events --------------------
@app.route("/events")
def events():
    search = request.args.get("search", "").strip()
    ay_filter = request.args.get("academic_year")
    sem_filter = request.args.get("semester")

    query = Event.query.join(Semester, isouter=True).join(AcademicYear, isouter=True)

    if search:
        query = query.filter(Event.name.ilike(f"%{search}%"))
    if ay_filter:
        query = query.filter(AcademicYear.id == int(ay_filter))
    if sem_filter:
        query = query.filter(Semester.name == sem_filter)

    events_list = query.order_by(Event.date.desc()).all()
    year_levels = YearLevel.query.order_by(YearLevel.level, YearLevel.section).all()
    academic_years = AcademicYear.query.order_by(AcademicYear.year.desc()).all()
    return render_template("events.html", events=events_list, year_levels=year_levels, academic_years=academic_years)


@app.route("/events/add", methods=["POST"])
def add_event():
    name = request.form.get("name")
    date_str = request.form.get("date")
    required_hours = float(request.form.get("required_hours", 2.0))
    selected_year_levels = request.form.getlist("year_levels")  # match the form checkbox name

    if not date_str:
        flash("Date is required.")
        return redirect(url_for("events"))

    date = datetime.strptime(date_str, "%Y-%m-%d").date()

    # Find matching semester
    semester = Semester.query.filter(
        Semester.start_date <= date,
        Semester.end_date >= date
    ).first()
    semester_id = semester.id if semester else None

    # Convert selected year levels to comma-separated string
    target_years_str = "all" if "all" in selected_year_levels else ",".join(selected_year_levels)

    event = Event(
        name=name,
        date=date,
        required_hours=required_hours,
        target_years=target_years_str,
        semester_id=semester_id
    )
    db.session.add(event)
    db.session.commit()

    # Bind students to event
    if "all" in selected_year_levels:
        students = Student.query.filter_by(status="active").all()
    else:
        students = Student.query.filter(
            Student.status == "active",
            Student.year_level_id.in_([int(yl) for yl in selected_year_levels])
        ).all()

    for student in students:
        attendance = EventAttendance(
            event_id=event.id,
            student_id=student.id,
            accumulated_hours=required_hours
        )
        db.session.add(attendance)

    db.session.commit()
    flash("Event created successfully with semester auto-detected.")
    return redirect(url_for("events"))

# -------------------- Edit Event --------------------
@app.route("/events/edit/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    year_levels = YearLevel.query.order_by(YearLevel.level, YearLevel.section).all()
    academic_years = AcademicYear.query.order_by(AcademicYear.year.desc()).all()

    if request.method == "POST":
        name = request.form.get("name")
        date_str = request.form.get("date")
        required_hours = float(request.form.get("required_hours", 2.0))
        selected_year_levels = request.form.getlist("target_years")

        event.name = name
        event.date = datetime.strptime(date_str, "%Y-%m-%d").date()
        event.required_hours = required_hours
        event.target_years = "all" if "all" in selected_year_levels else ",".join(selected_year_levels)

        semester = Semester.query.filter(
            Semester.start_date <= event.date,
            Semester.end_date >= event.date
        ).first()
        event.semester_id = semester.id if semester else None

        db.session.commit()
        flash("Event updated successfully.")
        return redirect(url_for("events"))

    return render_template(
        "edit_event.html",
        event=event,
        year_levels=year_levels,
        academic_years=academic_years
    )


# -------------------- Delete Event --------------------
@app.route("/events/delete/<int:event_id>")
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    # Delete associated attendance records first
    EventAttendance.query.filter_by(event_id=event.id).delete()
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted successfully.")
    return redirect(url_for("events"))


# -------------------- Event Attendance --------------------
@app.route("/events/<int:event_id>/attendance")
def event_attendance(event_id):
    event = Event.query.get_or_404(event_id)
    attendances = EventAttendance.query.filter_by(event_id=event_id).join(Student).order_by(Student.student_id).all()
    return render_template("event_attendance.html", event=event, attendances=attendances)


@app.route("/events/<int:event_id>/attendance/save", methods=["POST"])
def save_event_attendance(event_id):
    event = Event.query.get_or_404(event_id)
    attendances = EventAttendance.query.filter_by(event_id=event_id).all()

    for attendance in attendances:
        attendance.timed_in = bool(request.form.get(f"timed_in_{attendance.id}"))
        attendance.timed_out = bool(request.form.get(f"timed_out_{attendance.id}"))
        attendance.update_hours()  # Ensure this method exists

    db.session.commit()
    flash("Attendance saved successfully.")
    return redirect(url_for("event_attendance", event_id=event_id))

# -------------------- Attendance Dashboard --------------------
@app.route("/attendance_dashboard")
def attendance_dashboard():
    # Get filter params
    selected_ay_id = request.args.get("academic_year", type=int)
    selected_sem_id = request.args.get("semester", type=int)

    # Academic years, ordered descending
    academic_years = AcademicYear.query.order_by(AcademicYear.year.desc()).all()

    # Default: latest academic year
    if not selected_ay_id and academic_years:
        current_ay = academic_years[0]
        selected_ay_id = current_ay.id
    else:
        current_ay = AcademicYear.query.get(selected_ay_id)

    # Semesters for the selected academic year
    semesters = current_ay.semesters if current_ay else []

    # Default: selected semester (None if not chosen)
    current_semester = Semester.query.get(selected_sem_id) if selected_sem_id else None

    # Students active in the selected academic year
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
    else:
        students = []
        year_levels = []

    # Events filtered by semester if selected, otherwise all semesters in that AY
    if current_ay:
        if current_semester:
            events = (
                Event.query.filter_by(semester_id=current_semester.id)
                .order_by(Event.date)
                .all()
            )
        else:
            sem_ids = [sem.id for sem in semesters]
            events = (
                Event.query.filter(Event.semester_id.in_(sem_ids))
                .order_by(Event.date)
                .all()
            )
    else:
        events = []

    return render_template(
        "attendance_dashboard.html",
        students=students,
        events=events,
        year_levels=year_levels,
        academic_years=academic_years,
        semesters=semesters,
        selected_ay_id=selected_ay_id,
        selected_sem_id=selected_sem_id
    )



    # Get filter params
    selected_ay_id = request.args.get("academic_year", type=int)
    selected_sem_id = request.args.get("semester", type=int)

    # Academic years and semesters
    academic_years = AcademicYear.query.order_by(AcademicYear.year.desc()).all()

    # Default: latest academic year
    if not selected_ay_id and academic_years:
        current_ay = academic_years[0]
        selected_ay_id = current_ay.id
    else:
        current_ay = AcademicYear.query.get(selected_ay_id)

    # Semesters for the selected academic year
    semesters = current_ay.semesters if current_ay else []

    # Default: if no semester selected, include all
    current_semester = None
    if selected_sem_id:
        current_semester = Semester.query.get(selected_sem_id)

    # Students active in the selected academic year
    if current_ay:
        students = Student.query.join(YearLevel) \
                   .filter(Student.status=="active", YearLevel.academic_year_id==current_ay.id) \
                   .order_by(Student.lname, Student.fname, Student.mname).all()
        year_levels = YearLevel.query.filter_by(academic_year_id=current_ay.id) \
                        .order_by(YearLevel.level, YearLevel.section).all()
    else:
        students = []
        year_levels = []

    # Events filtered by semester if selected, otherwise all semesters in that AY
    if current_ay:
        if current_semester:
            events = Event.query.filter_by(semester_id=current_semester.id).order_by(Event.date).all()
        else:
            # All semesters in this AY
            sem_ids = [sem.id for sem in semesters]
            events = Event.query.filter(Event.semester_id.in_(sem_ids)).order_by(Event.date).all()
    else:
        events = []
    year_levels = YearLevel.query.order_by(YearLevel.academic_year_id, YearLevel.level, YearLevel.section).all()

    return render_template(
        "attendance_dashboard.html",
        students=students,
        events=events,
        year_levels=year_levels,
        academic_years=academic_years,
        semesters=semesters,
        selected_ay_id=selected_ay_id,
        selected_sem_id=selected_sem_id
    )

@app.route("/attendance_dashboard/save", methods=["POST"])
def save_all_attendance():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    for attendance in EventAttendance.query.all():
        old_hours = attendance.accumulated_hours
        event_hours = attendance.event.required_hours

        # Update timed_in and timed_out from form
        timed_in = bool(request.form.get(f"timein_{attendance.id}"))
        timed_out = bool(request.form.get(f"timeout_{attendance.id}"))
        attendance.timed_in = timed_in
        attendance.timed_out = timed_out

        # Calculate accumulated_hours
        if timed_in and timed_out:
            new_hours = 0
        elif timed_in or timed_out:
            new_hours = max(event_hours / 2, 0)
        else:
            new_hours = max(event_hours, 0)

        if old_hours != new_hours:
            attendance.accumulated_hours = new_hours
            history = EventAttendanceHistory(
                attendance_id=attendance.id,
                old_hours=old_hours,
                new_hours=new_hours,
                changed_by=user_id,
                reason="Manual adjustment via attendance dashboard"
            )
            db.session.add(history)

    db.session.commit()
    flash("Attendance saved successfully.", "success")
    return redirect(url_for("attendance_dashboard"))

    for attendance in EventAttendance.query.all():
        old_hours = attendance.accumulated_hours
        event_hours = attendance.event.required_hours

        # Update timed_in and timed_out from form
        timed_in = bool(request.form.get(f"timein_{attendance.id}"))
        timed_out = bool(request.form.get(f"timeout_{attendance.id}"))
        attendance.timed_in = timed_in
        attendance.timed_out = timed_out

        # Calculate accumulated_hours based on your logic
        if timed_in and timed_out:
            new_hours = 0
        elif timed_in or timed_out:
            new_hours = max(event_hours / 2, 0)
        else:
            new_hours = max(event_hours, 0)

        # Only update if changed
        if old_hours != new_hours:
            attendance.accumulated_hours = new_hours
            # optional: log history
            history = EventAttendanceHistory(
                attendance_id=attendance.id,
                old_hours=old_hours,
                new_hours=new_hours,
                changed_by=current_user.id,
                reason="Updated via dashboard"
            )
            db.session.add(history)

    db.session.commit()
    flash("Attendance saved successfully.", "success")
    return redirect(url_for("attendance_dashboard"))


@app.route("/export_attendance")
def export_attendance():
    # Get filters from query parameters
    name_filter = request.args.get("name", "").lower()
    ay_filter = request.args.get("ay")
    sem_filter = request.args.get("semester")
    year_level_filter = request.args.get("year_level")
    event_filter = request.args.get("event")

    # Query all students and events (replace with filtered queries if needed)
    students = Student.query.all()
    events = Event.query.all()

    # Optional: apply filtering here
    if name_filter:
        students = [s for s in students if name_filter in f"{s.fname} {s.lname}".lower()]
    if ay_filter:
        students = [s for s in students if str(s.year_level.academic_year_id) == ay_filter]
    if year_level_filter:
        students = [s for s in students if f"{s.year_level.level}-{s.year_level.section}" == year_level_filter]
    if sem_filter:
        students = [s for s in students if any(str(att.event.semester_id) == sem_filter for att in s.event_attendances)]
    if event_filter:
        students = [s for s in students if any(str(att.event_id) == event_filter for att in s.event_attendances)]
        events = [e for e in events if str(e.id) == event_filter]

    # Create CSV in memory
    si = StringIO()
    writer = csv.writer(si)

    # Header row
    header = ["Student ID", "Name", "Year Level", "Total CS Hours"]
    for event in events:
        header += [f"{event.name} Time In", f"{event.name} Time Out", f"{event.name} Hours"]
    writer.writerow(header)

    # Data rows
    for student in students:
        row = [
            student.student_id,
            f"{student.lname}, {student.fname} {student.mname}",
            f"{student.year_level.level}-{student.year_level.section}",
            round(sum([att.accumulated_hours for att in student.event_attendances]), 2)
        ]
        for event in events:
            attendance = next((att for att in student.event_attendances if att.event_id == event.id), None)
            row += [
                "Yes" if attendance and attendance.timed_in else "No",
                "Yes" if attendance and attendance.timed_out else "No",
                attendance.accumulated_hours if attendance else 0
            ]
        writer.writerow(row)

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=attendance.csv"}
    )
# -------------------- Attendance History --------------------
@app.route("/attendance_history")
def attendance_history():
    if 'user_id' not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    # Optional time filter
    time_filter = request.args.get("time", "all")  # all, today, week, month
    query = EventAttendanceHistory.query.join(User, EventAttendanceHistory.changed_by == User.id)

    now = datetime.now()
    if time_filter == "today":
        query = query.filter(EventAttendanceHistory.changed_at >= now.replace(hour=0, minute=0, second=0))
    elif time_filter == "week":
        query = query.filter(EventAttendanceHistory.changed_at >= now - timedelta(days=7))
    elif time_filter == "month":
        query = query.filter(EventAttendanceHistory.changed_at >= now - timedelta(days=30))

    logs = query.order_by(EventAttendanceHistory.changed_at.desc()).all()

    return render_template("attendance_history.html", logs=logs)


# -------------------- Student Promotion --------------------
@app.route("/students/promote/<int:student_id>")
def promote_student(student_id):
    student = Student.query.get_or_404(student_id)
    current_yl = student.year_level
    current_ay = current_yl.academic_year

    start_year, end_year = map(int, current_ay.year.split('-'))
    next_ay_str = f"{start_year + 1}-{end_year + 1}"

    next_ay = AcademicYear.query.filter_by(year=next_ay_str).first()
    if not next_ay:
        next_ay = AcademicYear(year=next_ay_str, status="active")
        db.session.add(next_ay)
        db.session.commit()

    next_level = current_yl.level + 1
    if next_level > 4:
        student.status = "graduate"
        db.session.commit()
        flash(f"{student.fname} {student.lname} has graduated.")
        return redirect(url_for("students"))

    next_yl = YearLevel.query.filter_by(
        academic_year_id=next_ay.id,
        level=next_level,
        section=current_yl.section
    ).first()
    if not next_yl:
        next_yl = YearLevel(level=next_level, section=current_yl.section, academic_year_id=next_ay.id)
        db.session.add(next_yl)
        db.session.commit()

    student.year_level_id = next_yl.id
    db.session.commit()
    flash(f"{student.fname} {student.lname} promoted to {next_level}-{next_yl.section} ({next_ay.year})")
    return redirect(url_for("students"))


