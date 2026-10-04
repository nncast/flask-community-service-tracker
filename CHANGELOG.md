# Changelog

All notable changes to the CIT Community Service Tracker are documented here.

## [0.1.3] — 2026-10-04 — Security, Data-Integrity & UI Fixes

### Main Features

- Server-side access control on every route: officers can use Dashboard, Events, and Attendance; Students, Year Levels, Academic Years, and Users are admin-only. Previously only the sidebar hid these pages, so the routes themselves were open, including to logged-out visitors (routes.py: new login_required / admin_required decorators)
- The logged-in user is re-checked on every request: deleted or deactivated accounts are signed out immediately, and role changes apply without logging out (routes.py: load_current_user())
- The attendance dashboard's Academic Year and Semester filters now reload the page with that period's students and events. Before, they only changed the dropdowns while the table kept showing the latest year (templates/attendance_dashboard.html)
- Hours owed and per-student totals update live as Time In / Time Out are ticked, with a warning before leaving the page with unsaved changes (templates/attendance_dashboard.html, static/js/event_attendance.js)
- Editing an event keeps its attendance in sync: students in newly targeted year levels are added, untouched records for removed year levels are dropped, and changing the required hours recalculates everyone's hours, with the change logged (routes.py: edit_event(), sync_event_attendance())
- Students added, moved to another year level, or promoted mid-year are added to the upcoming events of their year level (routes.py: bind_student_to_upcoming_events())

### Minor Features

- Events outside every semester are listed under "Unassigned" with an explanation instead of disappearing, and events in a semester break belong to the semester that just ended (routes.py: semester_for_date(); templates/events.html)
- Event target years show as readable labels such as "1-A, 2-B" instead of raw IDs, and the events table shows how many students each event has (models.py: Event.target_label)
- Create/Edit Event share one script that only offers the year levels of the academic year containing the chosen date, and warns when no academic year covers it (static/js/event_form.js)
- Typing an academic year (for example 2025-2026) suggests default semester dates; the hardcoded 2025/2026 defaults are gone (templates/academic_years.html)
- Flash messages are color-coded (success, error, warning), can be dismissed, and errors stay until dismissed (templates/base.html, static/css/dashboard.css)
- Search boxes on Users, Students, and Year Levels wait for you to stop typing and keep the cursor after reloading, instead of reloading on every keystroke (templates/base.html: data-autosubmit)
- The CSV export follows the dashboard's academic year/semester, includes event dates, uses "-" for events a student isn't part of, and opens correctly in Excel with accented names such as ñ (routes.py: export_attendance())
- Password fields on the Users page are masked, and the sidebar highlights and opens the current page's section (templates/users.html, templates/base.html)
- A random secret key is generated and stored in instance/secret_key, or read from the SECRET_KEY environment variable, replacing the hardcoded key; session cookies use SameSite=Lax (app.py)
- Delete, promote, and graduate actions are sent as POST requests with clear confirmation messages that say what else gets deleted (templates/base.html: data-post)

### Fixes

- Fixed saving the attendance dashboard resetting Time In / Time Out and hours for every event not shown on the page, such as other academic years and semesters. Only the records on the page are updated now (routes.py: save_all_attendance())
- Fixed anyone, even without logging in, being able to create admin accounts, delete users/students/events, and change academic data by posting to the routes directly (routes.py)
- Fixed the Add Academic Year form never saving 2nd semester dates: its fields reused the 1st semester's names (templates/academic_years.html)
- Fixed a 500 error when deleting a student, year level, or academic year whose students had attendance records. Attendance and its history are now deleted with the student (models.py: cascade on Student.event_attendances and EventAttendance.history_logs)
- Fixed deleting an event leaving orphaned history entries (routes.py: delete_event())
- Fixed "All Year Levels" on an event enrolling active students from every academic year instead of only the event's academic year (routes.py: resolve_target_year_levels())
- Fixed "Total CS Hours" counting every event a student ever had instead of the selected period, and removed a fake "override" value that was never saved (routes.py: student_totals())
- Fixed today's events not counting as upcoming, and the Upcoming / Recent Changes counters stopping at 5 (routes.py: dashboard())
- Fixed "Recent Attendance Changes" crediting every change to whoever is logged in instead of the user who made it (templates/dashboard.html)
- Fixed every flash message showing twice, and success messages showing in red (templates/*.html)
- Fixed middle names showing and saving as the text "None" on the Students, Attendance, and export pages (models.py: Student.full_name; templates/students.html)
- Fixed crashes (500 errors) on invalid or duplicate input: duplicate usernames, student IDs, or year levels on edit; non-numeric hours or levels; missing year level; bad dates (routes.py: form validation helpers)
- Fixed being able to delete, demote, or deactivate your own account. Users with attendance history must be deactivated instead of deleted so the audit trail stays intact (routes.py: edit_user(), delete_user())
- Fixed promoting a 4th-year student creating an unnecessary next academic year, and promoted-into academic years having no semesters (routes.py: promote_student())
- Fixed the per-event attendance sheet not recording changes in Attendance History (routes.py: save_event_attendance())
- Fixed the attendance table squeezing all event columns into the screen width, and the four pinned columns piling on top of each other when scrolling sideways (static/css/attendance_dashboard.css)
- Fixed sidebar dropdowns closing immediately when clicking the menu text or icon (templates/base.html)
- Fixed Attendance History's "Today / Last 7 / Last 30 days" filters using the UTC date, which is a day off for part of the day in UTC+8 (static/js/attendance_history.js)
- Fixed event names with quotes breaking the page scripts (templates/events.html, attendance_dashboard.html: data passed with tojson)
- Fixed invalid CSS color values (white(...)) that left the sidebar dropdown without a background (static/css/dashboard.css)
- Removed a FullCalendar CDN link that returned 404 on every page load (templates/base.html)

### Cleanup

- Removed compiled __pycache__ files from the repository and added a .gitignore (Python caches, virtual environments, instance/ database and secret key)
- Pinned SQLAlchemy (>=2.0.41,<2.2) in requirements.txt so installs don't pick up an untested major version
- Timestamps are now stored in local server time to match the date filters (models.py)
- No database migration needed: existing dbcs.db files work as-is

## [0.1.2] — 2026-09-14 — Dashboard Totals, Null-safe History & README

### Main Features

- The attendance dashboard shows a Total Hours metric for the selected academic year (routes.py: attendance_dashboard(); templates/attendance_dashboard.html)
- Added README.md with a project overview, requirements, installation and run steps, default credentials, and the developer list

### Minor Features

- The Hours column on the attendance dashboard is now read-only; hours come only from Time In / Time Out (templates/attendance_dashboard.html)

### Fixes

- Fixed the Dashboard and Attendance History pages crashing when a history entry's attendance, student, or event no longer exists; these now show "Unknown Student" / "Unknown Event" (templates/dashboard.html, templates/attendance_history.html)
- Removed dead duplicate code in attendance_dashboard() and save_all_attendance(), including an unreachable block that referenced an undefined current_user (routes.py)

## [0.1.1] — 2025-12-08 — Requirements, CIT Branding & Attendance Dashboard Rework

### Main Features

- Added requirements.txt (Flask 2.3.3, Werkzeug 2.3.8, Flask-SQLAlchemy 3.0.5, Flask-Migrate 4.0.4), so the app now installs with a single pip install -r requirements.txt
- The CIT logo now replaces the emoji placeholder in the sidebar and on the login page (static/imgs/cit_logo.png; templates/base.html, templates/login.html)
- Reworked the attendance dashboard layout: sticky student columns, horizontal scrolling when there are many events, and event date chips in the headers (templates/attendance_dashboard.html, static/css/attendance_dashboard.css)
- Rewrote attendance dashboard saving: hours are recalculated from the Time In / Time Out checkboxes, and every change is written to the attendance history (routes.py: save_all_attendance())

### Minor Features

- Student ID input auto-formats as XX-XXXXX and is limited to 8 characters (templates/students.html)
- Academic Years page restyled: semester date fields grouped and row actions turned into icon buttons (templates/academic_years.html, static/css/academic_years.css)
- Styling updates for the Events, Dashboard, and Login pages (static/css/event.css, dashboard.css, login.css)

### Fixes

- Removed the tracked SQLite database file (instance/dbcs.db) so a fresh clone starts with a clean database
- Removed static/js/attendace_dashboard.js, a misspelled script that no page loaded

### Known Issues (fixed in v0.1.3)

- In the Add Academic Year form, the 2nd semester date fields reuse the 1st semester field names, so 2nd semester dates are not saved
- Saving the attendance dashboard also resets attendance for events not shown on the page

### Notes

- The 2025-11-26 "Version 1.1" branch (previously tagged v1.0.0 and published as release "v1.2") was a merge committed with unresolved conflict markers in 13 files and could not run. It was never merged into main and is replaced by this release.

## [0.1.0] — 2025-11-25 — Initial Release

### Main Features

- Login with role-based access (Admin, Officer); a default admin account (admin / admin123) is created automatically on first run (app.py; routes.py: login())
- Dashboard with active-student count, total events, upcoming events, and recent attendance changes (routes.py: dashboard(); templates/dashboard.html)
- User management: add, edit, and delete users, set role and active/inactive status, search and filter by role/status (routes.py: users(), add_user(), edit_user(), delete_user(); templates/users.html)
- Academic years with 1st and 2nd semester date ranges (routes.py: add_academic_year(), edit_academic_year(); templates/academic_years.html)
- Year levels and sections per academic year (routes.py: year_levels(); templates/year_levels.html)
- Student management: add, edit, and delete students, filter by academic year, year level, and status, and promote a student to the next year level (or mark them graduated after 4th year) (routes.py: students(), promote_student(); templates/students.html)
- Events with required hours and target year levels; the semester is auto-detected from the event date and attendance records are created automatically for every targeted active student (routes.py: add_event(), edit_event(); templates/events.html, templates/edit_event.html)
- Per-event attendance sheet (signed in / signed out) with community service hours computed automatically: signed in and out = 0 hours owed, only one = half, neither = full required hours (models.py: EventAttendance.calculate_accumulated_hours(); templates/event_attendance.html)
- Attendance dashboard: a students × events grid with academic year, semester, year level, and event filters, plus bulk save (routes.py: attendance_dashboard(), save_all_attendance(); templates/attendance_dashboard.html)
- Attendance change history log with time-range and search filters (routes.py: attendance_history(); templates/attendance_history.html)
- CSV export of attendance data (routes.py: export_attendance())

### Minor Features

- SQLite database through Flask-SQLAlchemy, with Flask-Migrate set up (app.py, models.py)
- Per-page stylesheets and La Salette branding (static/css/, static/imgs/)
