from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

ROLES = ("admin", "officer")
USER_STATUSES = ("active", "inactive")
STUDENT_STATUSES = ("active", "inactive", "graduate")
SEMESTER_NAMES = ("1st Semester", "2nd Semester")

# ----------------- User -----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # store hashed
    role = db.Column(db.String(20), nullable=False)       # admin / officer
    status = db.Column(db.String(20), nullable=False)     # active / inactive
    created_at = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<User {self.username}>"

# ----------------- Academic Year -----------------
class AcademicYear(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(20), unique=True, nullable=False)   # e.g., "2025-2026"
    status = db.Column(db.String(20), nullable=False, default="active")
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Ordered so semesters[0] is always the 1st semester and semesters[1] the 2nd
    semesters = db.relationship("Semester", backref="academic_year", cascade="all, delete-orphan",
                                order_by="Semester.id")
    year_levels = db.relationship("YearLevel", backref="academic_year", cascade="all, delete-orphan")

# ----------------- Semester -----------------
class Semester(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_year.id"), nullable=False)
    name = db.Column(db.String(20), nullable=False)       # e.g., "1st Semester"
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

# ----------------- YearLevel -----------------
class YearLevel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_year.id"), nullable=False)
    level = db.Column(db.Integer, nullable=False)         # 1-4
    section = db.Column(db.String(5), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    students = db.relationship("Student", backref="year_level", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("academic_year_id", "level", "section", name="uq_year_level_section"),
    )

    @property
    def label(self):
        return f"{self.level}-{self.section}"

    def __repr__(self):
        return f"<YearLevel {self.level}-{self.section} AY:{self.academic_year_id}>"

# ----------------- Student -----------------
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(8), unique=True, nullable=False)
    fname = db.Column(db.String(50), nullable=False)
    mname = db.Column(db.String(50), nullable=True)
    lname = db.Column(db.String(50), nullable=False)
    year_level_id = db.Column(db.Integer, db.ForeignKey("year_level.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")  # active, inactive, graduate
    created_at = db.Column(db.DateTime, default=datetime.now)

    @property
    def full_name(self):
        """'Last, First Middle' without a trailing 'None' when there is no middle name."""
        return f"{self.lname}, {self.fname} {self.mname or ''}".strip()

# ----------------- Event -----------------
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    required_hours = db.Column(db.Float, default=2.0, nullable=False)
    target_years = db.Column(db.String(255), nullable=False)   # CSV of YearLevel IDs or "all"
    semester_id = db.Column(db.Integer, db.ForeignKey("semester.id"), nullable=True)
    semester = db.relationship("Semester", backref="events")
    created_at = db.Column(db.DateTime, default=datetime.now)
    attendance = db.relationship("EventAttendance", backref="event", cascade="all, delete-orphan")

    @property
    def target_year_ids(self):
        """YearLevel IDs stored in target_years (empty list when it is "all")."""
        if not self.target_years or self.target_years == "all":
            return []
        return [int(x) for x in self.target_years.split(",") if x.strip().isdigit()]

    @property
    def target_label(self):
        """Readable target year levels, e.g. "1-A, 2-B" instead of the raw "3,4"."""
        if self.target_years == "all":
            return "All year levels"
        ids = self.target_year_ids
        if not ids:
            return "None"
        levels = YearLevel.query.filter(YearLevel.id.in_(ids)).order_by(YearLevel.level, YearLevel.section).all()
        return ", ".join(yl.label for yl in levels) or "None"

    def __repr__(self):
        return f"<Event {self.name} ({self.date})>"

# ----------------- EventAttendance -----------------
class EventAttendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    timed_in = db.Column(db.Boolean, default=False)
    timed_out = db.Column(db.Boolean, default=False)
    accumulated_hours = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    # Deleting a student also deletes their attendance (student_id cannot be NULL)
    student = db.relationship("Student", backref=db.backref("event_attendances", cascade="all, delete-orphan"))

    __table_args__ = (
        db.UniqueConstraint("event_id", "student_id", name="uq_event_student"),
    )

    @staticmethod
    def hours_owed(required_hours, timed_in, timed_out):
        """CS hours a student owes for an event: 0 if they signed in and out,
        half if they did only one, the full required hours if they did neither."""
        if timed_in and timed_out:
            return 0.0
        if timed_in or timed_out:
            return required_hours / 2
        return required_hours

    def calculate_accumulated_hours(self):
        return self.hours_owed(self.event.required_hours, self.timed_in, self.timed_out)

    def update_hours(self):
        self.accumulated_hours = self.calculate_accumulated_hours()

# ----------------- EventAttendanceHistory -----------------
class EventAttendanceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey("event_attendance.id"), nullable=False)
    old_hours = db.Column(db.Float, nullable=False)
    new_hours = db.Column(db.Float, nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.now)
    reason = db.Column(db.String(255))

    # Deleting an attendance record (event/student deleted) also deletes its log entries
    attendance = db.relationship("EventAttendance", backref=db.backref("history_logs", cascade="all, delete-orphan"))
    user = db.relationship("User")

    def __repr__(self):
        return f"<AttendanceHistory att={self.attendance_id} old={self.old_hours} new={self.new_hours}>"
