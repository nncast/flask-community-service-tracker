from flask import render_template, request, redirect, url_for, flash, session
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from models import (
    User, AcademicYear, Semester, YearLevel, Student,
    Event, EventAttendance, EventAttendanceHistory
)

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
    return render_template("dashboard.html",
                           username=session.get("username"),
                           role=session.get("role"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for("login"))


# -------------------- Users CRUD --------------------
@app.route("/users")
def users():
    if 'user_id' not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

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


@app.route("/users/edit/<int:user_id>", methods=["POST"])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    user.username = request.form.get("username")
    password = request.form.get("password")
    if password:
        user.password = generate_password_hash(password)
    user.role = request.form.get("role")
    user.status = request.form.get("status")
    db.session.commit()
    flash("User updated successfully.")
    return redirect(url_for("users"))


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
    events_list = Event.query.order_by(Event.date.desc()).all()
    year_levels = YearLevel.query.order_by(YearLevel.level, YearLevel.section).all()
    return render_template("events.html", events=events_list, year_levels=year_levels)


@app.route("/events/add", methods=["POST"])
def add_event():
    name = request.form.get("name")
    date_str = request.form.get("date")
    required_hours = float(request.form.get("required_hours", 2.0))
    selected_year_levels = request.form.getlist("year_levels")

    if not date_str:
        flash("Date is required.")
        return redirect(url_for("events"))

    date = datetime.strptime(date_str, "%Y-%m-%d").date()
    target_years_str = ",".join(selected_year_levels)

    event = Event(name=name, date=date, required_hours=required_hours, target_years=target_years_str)
    db.session.add(event)
    db.session.commit()

    if "all" in selected_year_levels:
        students = Student.query.filter_by(status="active").all()
    else:
        students = Student.query.filter(Student.status=="active",
                                        Student.year_level_id.in_([int(yl) for yl in selected_year_levels])).all()

    for student in students:
        attendance = EventAttendance(event_id=event.id,
                                     student_id=student.id,
                                     accumulated_hours=required_hours)
        db.session.add(attendance)
    db.session.commit()
    flash("Event created successfully with attendance.")
    return redirect(url_for("events"))

# -------------------- Edit Event --------------------
@app.route("/events/edit/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    year_levels = YearLevel.query.order_by(YearLevel.level, YearLevel.section).all()

    if request.method == "POST":
        name = request.form.get("name")
        date_str = request.form.get("date")
        required_hours = float(request.form.get("required_hours", 2.0))
        target_years = request.form.getlist("target_years")

        event.name = name
        event.date = datetime.strptime(date_str, "%Y-%m-%d").date()
        event.required_hours = required_hours
        event.target_years = "all" if "all" in target_years else ",".join(target_years)

        db.session.commit()
        flash("Event updated successfully.")
        return redirect(url_for("events"))

    # GET request
    return render_template("edit_event.html", event=event, year_levels=year_levels)


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
        attendance.update_hours()  # Make sure your EventAttendance model has this method

    db.session.commit()
    flash("Attendance saved successfully.")
    return redirect(url_for("event_attendance", event_id=event_id))


# -------------------- Attendance Dashboard --------------------
@app.route("/attendance_dashboard")
def attendance_dashboard():
    students = Student.query.join(YearLevel).filter(Student.status=="active") \
               .order_by(YearLevel.level, YearLevel.section, Student.student_id).all()

    current_ay = AcademicYear.query.order_by(AcademicYear.year.desc()).first()
    if current_ay:
        events = Event.query.join(EventAttendance, isouter=True) \
                .join(Student, EventAttendance.student_id == Student.id, isouter=True) \
                .join(YearLevel, Student.year_level_id == YearLevel.id, isouter=True) \
                .filter(YearLevel.academic_year_id == current_ay.id) \
                .order_by(Event.date).all()
    else:
        events = []

    return render_template("attendance_dashboard.html", students=students, events=events)


@app.route("/attendance_dashboard/save", methods=["POST"])
def save_all_attendance():
    current_user_id = session["user_id"]

    for key, value in request.form.items():
        parts = key.split("_")
        if len(parts) != 2:
            continue
        field, att_id = parts
        attendance = EventAttendance.query.get(int(att_id))
        if not attendance:
            continue

        if field == "timein":
            attendance.timed_in = True
        elif field == "timeout":
            attendance.timed_out = True
        elif field == "hours":
            try:
                new_hours = float(value)
            except:
                new_hours = attendance.accumulated_hours
            if new_hours != attendance.accumulated_hours:
                log = EventAttendanceHistory(
                    attendance_id=attendance.id,
                    old_hours=attendance.accumulated_hours,
                    new_hours=new_hours,
                    changed_by=current_user_id,
                    reason="Manual adjustment via attendance dashboard"
                )
                db.session.add(log)
                attendance.accumulated_hours = new_hours

    db.session.commit()
    flash("Attendance and hour adjustments saved.")
    return redirect(url_for("attendance_dashboard"))


# -------------------- Attendance History --------------------
@app.route("/attendance_history")
def attendance_history():
    logs = EventAttendanceHistory.query.order_by(
        EventAttendanceHistory.changed_at.desc()
    ).all()
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
