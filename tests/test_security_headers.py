"""The security headers securityheaders.com grades, and pages that keep to the policy.
Run: uv run --with pytest pytest tests (uses its own in-memory database)."""
import os
import pathlib
import re

os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("SECRET_KEY", "test")

from app import app  # noqa: E402

TEMPLATES = pathlib.Path(__file__).resolve().parent.parent / "templates"


def protected(response):
    for name, value in {"X-Frame-Options": "SAMEORIGIN", "X-Content-Type-Options": "nosniff",
                        "Referrer-Policy": "strict-origin-when-cross-origin"}.items():
        assert response.headers[name] == value
    assert "camera=()" in response.headers["Permissions-Policy"]
    csp = response.headers["Content-Security-Policy"]
    nonce = re.search(r"script-src 'self' 'nonce-([^']+)'", csp).group(1)
    inline = re.findall(r'<script(?![^>]*\bsrc=)(?![^>]*application/json)([^>]*)>', response.get_data(as_text=True))
    assert inline and all(f'nonce="{nonce}"' in attrs for attrs in inline)


def test_pages_are_protected():
    client = app.test_client()
    login = client.get("/")
    assert "Content-Security-Policy" in login.headers
    client.post("/", data={"username": "admin", "password": "admin123"})
    for page in ("/dashboard", "/students"):
        response = client.get(page)
        assert response.status_code == 200, page
        protected(response)


def test_hsts_only_over_https():
    client = app.test_client()
    assert "Strict-Transport-Security" not in client.get("/").headers
    assert client.get("/", base_url="https://localhost").headers["Strict-Transport-Security"] == "max-age=31536000"


def test_no_template_has_an_inline_event_handler():
    """The policy runs none: onchange="…" would silently do nothing."""
    for template in TEMPLATES.glob("*.html"):
        assert not re.search(r"<[^>]+\son[a-z]+\s*=\s*[\"']", template.read_text(encoding="utf-8")), template.name


def test_scripts_are_served_as_javascript():
    """With nosniff, a script served as text/plain (Python's guess from the Windows registry) doesn't run."""
    client = app.test_client()
    assert client.get("/static/js/event_form.js").mimetype == "text/javascript"
    assert client.get("/static/css/app.css").mimetype == "text/css"
