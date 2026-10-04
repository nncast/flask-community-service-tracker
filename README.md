<p align="center">
  <img src="static/imgs/cit_logo.png" alt="CIT Community Service Tracker" width="120">
</p>

<h1 align="center">CIT Community Service Tracker</h1>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.3-8038C5?style=flat-square" alt="version">
  <img src="https://img.shields.io/badge/status-stable-2772BD?style=flat-square" alt="status">
  <img src="https://img.shields.io/badge/python-3.12%2B-2B9580?style=flat-square&logo=python&logoColor=white" alt="python">
  <img src="https://img.shields.io/badge/Flask-2.3-E59A18?style=flat-square&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/SQLite-SQLAlchemy-CA2A44?style=flat-square&logo=sqlite&logoColor=white" alt="SQLite">
</p>

<p align="center">
  <a href="#quick-start"><strong>Quick Start</strong></a> ·
  <a href="#screenshots">Screenshots</a> ·
  <a href="#roles">Roles</a> ·
  <a href="https://github.com/nncast/flask-community-service-tracker/releases" target="_blank" rel="noopener noreferrer">Release Notes</a>
</p>

The CIT Community Service Tracker is a Flask web app for the University of La Salette College of Information Technology. Officers record which students signed in and out of community service events, and the app tracks the service hours each student still owes per semester.

> **Current version: v0.1.3** — Server-Side Access Control, Safe Attendance Saving, Live Hour Totals, Event/Attendance Sync & Cleaner UI. See the [Release Notes](https://github.com/nncast/flask-community-service-tracker/releases) for the full version history.

## Screenshots

<table>
  <tr>
    <td width="50%"><img src="docs/screenshots/dashboard.png" alt="Dashboard"><br><sub><b>Dashboard</b>: students, events, upcoming events and recent attendance changes</sub></td>
    <td width="50%"><img src="docs/screenshots/attendance-dashboard.png" alt="Attendance Dashboard"><br><sub><b>Attendance Dashboard</b>: every student × event for a semester, with live hour totals</sub></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/events.png" alt="Events"><br><sub><b>Events</b>: create events for specific year levels, grouped by academic year and semester</sub></td>
    <td><img src="docs/screenshots/event-attendance.png" alt="Event Attendance"><br><sub><b>Event Attendance</b>: sign students in and out; hours owed update as you tick</sub></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/students.png" alt="Students"><br><sub><b>Students</b>: records per year level, with promotion to the next year</sub></td>
    <td><img src="docs/screenshots/attendance-history.png" alt="Attendance History"><br><sub><b>Attendance History</b>: every hours change, who made it and why</sub></td>
  </tr>
</table>

## How hours work

Each event has a number of **required hours**. Every student in the event's target year levels owes those hours until they attend:

| Signed in | Signed out | Hours owed |
|:---:|:---:|:---:|
| Yes | Yes | 0 |
| Yes | No | half |
| No | Yes | half |
| No | No | full |

A student's **Total CS Hours** is the sum for the selected academic year or semester, and every change is logged in Attendance History.

## Roles

- **Admin**: everything, including Students, Year Levels, Academic Years and Users.
- **Officer**: Dashboard, Events and Attendance.

## Contributing

Contributions are welcome. Fork the repository, work on a branch from `main`, and open a pull request describing what changed and why.

## Security

Please don't report vulnerabilities in public issues. Contact the maintainers privately instead.

## Quick Start

Requires [Python 3.12+](https://www.python.org/downloads/) and optionally [Git](https://git-scm.com/downloads).

```
git clone https://github.com/nncast/flask-community-service-tracker.git
cd flask-community-service-tracker

python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000** and sign in with `admin` / `admin123`. **Change this password after the first login.**

On first run the app creates its SQLite database (`dbcs.db`) and a random session secret key (`secret_key`) in the `instance/` folder. To use your own secret key, set the `SECRET_KEY` environment variable before starting the app.

**First-time setup:** add an **Academic Year** with its semester dates, then **Year Levels**, then **Students**. After that you can create **Events** and record attendance.

## Developers

- Kimberly Bernabe
- Janelle Ann Castillo
- Hazel Sebastian
- Louisse Glaze Villarente

---

<p align="center"><i>CIT Community Service Tracker · Flask · SQLAlchemy · SQLite · Vanilla JS</i></p>
