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


STATIC_JS = TEMPLATES.parent / "static" / "js"


def test_pages_get_the_obfuscated_scripts():
    client = app.test_client()
    client.post("/", data={"username": "admin", "password": "admin123"})
    page = client.get("/events").get_data(as_text=True)
    src = re.search(r'src="(/static/js/event_form[^"]*)"', page).group(1)
    assert ".min.js" in src
    code = client.get(src).get_data(as_text=True)
    assert code.startswith("/*! source sha1:")
    # The policy has no 'unsafe-eval': code that built functions from strings would stop.
    assert not re.search(r"\beval\s*\(|new Function|\bFunction\s*\(", code)


def test_every_copy_is_made_from_its_current_source():
    """After changing a script: node scripts/obfuscate.mjs (else the readable one is served)."""
    import hashlib
    for source in STATIC_JS.glob("*.js"):
        if source.name.endswith(".min.js"):
            continue
        digest = hashlib.sha1(source.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        header = (STATIC_JS / source.name.replace(".js", ".min.js")).read_text(encoding="utf-8").splitlines()[0]
        assert f"sha1:{digest}" in header, f"{source.name}: run node scripts/obfuscate.mjs"


def test_a_stale_copy_is_never_served():
    (STATIC_JS / "zz_probe.js").write_text("function probe() { return 1; }\n", encoding="utf-8")
    (STATIC_JS / "zz_probe.min.js").write_text("/*! source sha1:0000 */\nold();\n", encoding="utf-8")
    try:
        with app.test_request_context():
            from app import script_url
            assert "zz_probe.js" in script_url("js/zz_probe.js") and ".min.js" not in script_url("js/zz_probe.js")
    finally:
        (STATIC_JS / "zz_probe.js").unlink(); (STATIC_JS / "zz_probe.min.js").unlink()
