import os
import secrets
from flask import Flask
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash
from icons import icon
from models import db, User, AcademicYear, Semester, YearLevel, Student, Event, EventAttendance, EventAttendanceHistory

# ----------------- 1. Create app -----------------
app = Flask(__name__)


def load_secret_key():
    """Use SECRET_KEY from the environment, otherwise a random key saved in the
    instance folder so sessions survive restarts without a hardcoded secret."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    os.makedirs(app.instance_path, exist_ok=True)
    key_file = os.path.join(app.instance_path, "secret_key")
    if not os.path.exists(key_file):
        with open(key_file, "w") as f:
            f.write(secrets.token_hex(32))
    with open(key_file) as f:
        return f.read().strip()


# ----------------- 2. Configure app -----------------
app.secret_key = load_secret_key()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dbcs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'   # blocks cross-site form posts from reusing the session

# ----------------- 3. Initialize extensions -----------------
db.init_app(app)
migrate = Migrate(app, db)
app.jinja_env.globals["icon"] = icon

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
