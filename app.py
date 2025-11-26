from flask import Flask
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash
from models import db, User, AcademicYear, Semester, YearLevel, Student, Event, EventAttendance, EventAttendanceHistory

# ----------------- 1. Create app -----------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# ----------------- 2. Configure app -----------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dbcs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ----------------- 3. Initialize extensions -----------------
db.init_app(app)
migrate = Migrate(app, db)

# ----------------- 4. Import routes after app creation -----------------
from routes import *


# ----------------- 5. Create tables and default admin -----------------
with app.app_context():
    db.create_all()

    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            password=generate_password_hash("admin123"),
            role="admin",
            status="active"
        )
        db.session.add(admin)
        db.session.commit()

# ----------------- 6. Run app -----------------
if __name__ == "__main__":
    app.run(debug=True)
