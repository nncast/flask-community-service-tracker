# CommunityServiceTracker v0.1.3
(2026 October 4)

**CommunityServiceTracker** is a web-based application built with **Flask** for tracking and managing community service hours for students.  
The system supports role-based access for admins and officers, providing a centralized platform for logging, verifying, and reporting community service activities.

## Requirements
- Python 3.12 or later
  - [Download Python](https://www.python.org/downloads/)
- Git (optional, for cloning)
  - [Download Git](https://git-scm.com/downloads)
- Web browser (Chrome, Firefox, Edge, etc.)

## Installation
1. Clone or download the project `.zip` file and extract it.
2. Open terminal/command prompt and navigate to the project folder.
3. Create a virtual environment (recommended):
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```
4. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the application:
   ```bash
   # Windows
   python app.py
   
   # Linux/Mac
   python3 app.py
   ```
6. Open your web browser and go to `http://localhost:5000`
7. Login with default credentials:  
   - **Username:** `admin`  
   - **Password:** `admin123`

**Important:** Change default passwords after first login!

## Roles
- **Admin:** full access, including Students, Year Levels, Academic Years, and Users.
- **Officer:** Dashboard, Events, and Attendance only.

## Configuration
- The SQLite database (`dbcs.db`) and a randomly generated session secret key (`secret_key`) are created in the `instance/` folder on first run.
- To use your own secret key, set the `SECRET_KEY` environment variable before starting the app.

## Changelog
See [CHANGELOG.md](CHANGELOG.md) or the [Releases](https://github.com/nncast/flask-community-service-tracker/releases) page.

---

**Developers:** 
   - Kimberly Bernabe 
   - Janelle Ann Castillo
   - Hazel Sebastian
   - Louisse Glaze Villarente  

**GitHub Repository:** [community-service-tracker](https://github.com/nncast/flask-community-service-tracker)
