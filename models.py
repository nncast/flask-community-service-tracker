from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ----------------- User -----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # store hashed
    role = db.Column(db.String(20), nullable=False)       # admin / officer
    status = db.Column(db.String(20), nullable=False)     # active / inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.username}>"

# ----------------- Academic Year -----------------
class AcademicYear(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    semesters = db.relationship("Semester", backref="academic_year", cascade="all, delete-orphan")
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    students = db.relationship("Student", backref="year_level", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("academic_year_id", "level", "section", name="uq_year_level_section"),
    )

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ----------------- Event -----------------
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    required_hours = db.Column(db.Float, default=2.0, nullable=False)
    target_years = db.Column(db.String(255), nullable=False)   # CSV of YearLevel IDs or "all"
    semester_id = db.Column(db.Integer, db.ForeignKey("semester.id"), nullable=True)
    semester = db.relationship("Semester", backref="events")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    attendance = db.relationship("EventAttendance", backref="event", cascade="all, delete-orphan")

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship("Student", backref="event_attendances")

    __table_args__ = (
        db.UniqueConstraint("event_id", "student_id", name="uq_event_student"),
    )

    def calculate_accumulated_hours(self):
        total_hours = self.event.required_hours
        if self.timed_in and self.timed_out:
            return 0
        if self.timed_in != self.timed_out:
            return total_hours / 2
        return total_hours

    def update_hours(self):
        self.accumulated_hours = self.calculate_accumulated_hours()

# ----------------- EventAttendanceHistory -----------------
class EventAttendanceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey("event_attendance.id"), nullable=False)
    old_hours = db.Column(db.Float, nullable=False)
    new_hours = db.Column(db.Float, nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.String(255))

    attendance = db.relationship("EventAttendance", backref="history_logs")
    user = db.relationship("User")

    def __repr__(self):
        return f"<AttendanceHistory att={self.attendance_id} old={self.old_hours} new={self.new_hours}>"
