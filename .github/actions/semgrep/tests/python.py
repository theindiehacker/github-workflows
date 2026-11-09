# Semgrep の自作ルールの検体。検知させたい書き方を意図して書くため、ruff の指摘は行ごとに noqa で外す。
# S608 は CI の --select S でだけ有効になり、既定の ruff check はその noqa を不要 (RUF100) とするため、RUF100 も並べる
import contextlib
import html
import os
import zipfile
from pathlib import Path
from string import Template as StringTemplate

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, Template
from jinja2.sandbox import SandboxedEnvironment
from markdown_it import MarkdownIt
from starlette.middleware import Middleware
from templating import shared_env

app = FastAPI()
ORIGINS = ["*"]
TRUSTED_ORIGINS = ["https://app.example"]
LATER_ORIGINS = ["*"]
LATER_ORIGINS = ["https://app.example"]
WIDER_ORIGINS = ["https://app.example"]
WIDER_ORIGINS = ["*", "https://app.example"]

# ruleid: python-cors-credentials-any-origin
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True)

app.add_middleware(
    CORSMiddleware,
    # ruleid: python-cors-credentials-any-origin
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ruleid: python-cors-credentials-any-origin
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origin_regex=".*")

app.add_middleware(
    CORSMiddleware,
    # ruleid: python-cors-credentials-any-origin
    allow_origin_regex=r"^https://.*$",
    allow_credentials=True,
)

middleware = [
    Middleware(
        CORSMiddleware,
        # ruleid: python-cors-credentials-any-origin
        allow_origins=["https://app.example", "*"],
        allow_credentials=True,
    )
]

# ruleid: python-cors-credentials-any-origin
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_credentials=True)

# ok: python-cors-credentials-any-origin
app.add_middleware(
    CORSMiddleware, allow_origins=TRUSTED_ORIGINS, allow_credentials=True
)

# ruleid: python-cors-credentials-any-origin
app.add_middleware(CORSMiddleware, allow_origins=("*",), allow_credentials=True)

# ok: python-cors-credentials-any-origin
app.add_middleware(CORSMiddleware, allow_origins=LATER_ORIGINS, allow_credentials=True)

# ruleid: python-cors-credentials-any-origin
app.add_middleware(CORSMiddleware, allow_origins=WIDER_ORIGINS, allow_credentials=True)

# ok: python-cors-credentials-any-origin
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# ok: python-cors-credentials-any-origin
app.add_middleware(
    CORSMiddleware, allow_origins=["https://app.example"], allow_credentials=True
)

# ok: python-cors-credentials-any-origin
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.example\.com",
    allow_credentials=True,
)


def unzip(archive: Path, dest: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            # ruleid: python-zip-slip
            (dest / name).write_bytes(zf.read(name))


def unzip_infolist(archive: Path, dest: str) -> None:
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            path = os.path.join(dest, info.filename)
            # ruleid: python-zip-slip
            with open(path, "wb") as f:
                f.write(zf.read(info))


def unzip_all(archive: Path, dest: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        # ok: python-zip-slip
        zf.extractall(dest)


def unzip_checked(archive: Path, dest: Path) -> None:
    base = dest.resolve()
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            path = (base / name).resolve()
            if not path.is_relative_to(base):
                raise ValueError(name)
            # ok: python-zip-slip
            path.write_bytes(zf.read(name))


def unzip_flat(archive: Path, dest: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            # ok: python-zip-slip
            (dest / Path(name).name).write_bytes(zf.read(name))


ALLOWED = {"name", "bio"}
DEFAULTS = {"theme": "light"}


def update(user, body: dict) -> None:
    for key, value in body.items():
        # ruleid: python-mass-assignment
        setattr(user, key, value)


def update_keys(user, body: dict) -> None:
    # 検知させたい書き方なので、ruff の指摘 (.items() を使う) は外す
    for key in body:  # noqa: PLC0206
        # ruleid: python-mass-assignment
        setattr(user, key, body[key])


def update_model(user, body) -> None:
    for key, value in body.model_dump(exclude_unset=True).items():
        # ok: python-mass-assignment
        setattr(user, key, value)


def update_allowed(user, body: dict) -> None:
    for key, value in body.items():
        if key in ALLOWED:
            # ok: python-mass-assignment
            setattr(user, key, value)


def update_skip(user, body: dict) -> None:
    for key, value in body.items():
        if key not in ALLOWED:
            continue
        # ok: python-mass-assignment
        setattr(user, key, value)


def apply_defaults(settings) -> None:
    for key, value in DEFAULTS.items():
        # ok: python-mass-assignment
        setattr(settings, key, value)


env = Environment(autoescape=True)
sandbox = SandboxedEnvironment(autoescape=True)


def search_page(q: str) -> HTMLResponse:
    # ruleid: python-html-response-xss
    return HTMLResponse(f"<p>{q}</p>")


def search_page_concat(q: str) -> HTMLResponse:
    body = "<p>" + q + "</p>"
    # ruleid: python-html-response-xss
    return HTMLResponse(content=body)


async def search_page_request(request: Request) -> HTMLResponse:
    q = request.query_params.get("q", "")
    # ruleid: python-html-response-xss
    return HTMLResponse("<p>{}</p>".format(q))  # noqa: UP032


def search_page_escaped(q: str) -> HTMLResponse:
    # ok: python-html-response-xss
    return HTMLResponse(f"<p>{html.escape(q)}</p>")


def search_page_template(q: str) -> HTMLResponse:
    # ok: python-html-response-xss
    return HTMLResponse(env.get_template("search.html").render(q=q))


def search_page_bare_template(q: str) -> HTMLResponse:
    # ruleid: python-html-response-xss
    return HTMLResponse(Template("<p>{{ q }}</p>").render(q=q))


def fixed_page() -> HTMLResponse:
    # ok: python-html-response-xss
    return HTMLResponse("<p>fixed</p>")


def render_greeting(greeting: str, name: str) -> str:
    # ruleid: python-jinja2-ssti
    return Template(greeting).render(name=name)


def render_custom(source: str) -> str:
    # ruleid: python-jinja2-ssti
    return env.from_string(source).render()


def render_value(name: str) -> str:
    # ok: python-jinja2-ssti
    return env.from_string("Hello {{ name }}").render(name=name)


def render_sandboxed(source: str) -> str:
    # ok: python-jinja2-ssti
    return sandbox.from_string(source).render()


def render_string_template(source: str) -> str:
    # ok: python-jinja2-ssti
    return StringTemplate(source).substitute(name="x")


def find_user(conn, name: str):
    # ruleid: python-sqlalchemy-exec-driver-sql
    return conn.exec_driver_sql(f"SELECT * FROM users WHERE name = '{name}'")  # noqa: S608, RUF100


def find_user_percent(conn, name: str):
    sql = "SELECT * FROM users WHERE name = '%s'" % name  # noqa: UP031, S608, RUF100
    # ruleid: python-sqlalchemy-exec-driver-sql
    return conn.exec_driver_sql(sql)


def find_user_bound(conn, name: str):
    # ok: python-sqlalchemy-exec-driver-sql
    return conn.exec_driver_sql(
        "SELECT * FROM users WHERE name = %(name)s", {"name": name}
    )


def ping(conn):
    # ok: python-sqlalchemy-exec-driver-sql
    return conn.exec_driver_sql("SELECT 1")


def unzip_lexical_check(archive: Path, dest: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            # is_relative_to は文字列で比べるだけで、../ を畳まない
            target = dest / name
            if not target.is_relative_to(dest):
                raise ValueError(name)
            # ruleid: python-zip-slip
            target.write_bytes(zf.read(name))


def unzip_resolved_check(archive: Path, dest: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            target = dest / name
            if not target.resolve().is_relative_to(dest.resolve()):
                raise ValueError(name)
            # ok: python-zip-slip
            target.write_bytes(zf.read(name))


plain_env = Environment()  # noqa: S701, RUF100
md = MarkdownIt()
templates = Jinja2Templates(directory="templates")


def search_page_plain_env(name: str) -> HTMLResponse:
    # ruleid: python-html-response-xss
    return HTMLResponse(plain_env.from_string("<p>{{ n }}</p>").render(n=name))


def search_page_markdown(text: str) -> HTMLResponse:
    # ruleid: python-html-response-xss
    return HTMLResponse(md.render(text))


def search_page_templates(q: str) -> HTMLResponse:
    # ok: python-html-response-xss
    return HTMLResponse(templates.get_template("search.html").render(q=q))


def update_columns(user, payload: dict) -> None:
    for key, value in payload.items():
        if key in user.__table__.columns:
            # ruleid: python-mass-assignment
            setattr(user, key, value)


def update_present(user, payload: dict) -> None:
    for key, value in payload.items():
        if key in payload:
            # ruleid: python-mass-assignment
            setattr(user, key, value)


def update_literal(user, payload: dict) -> None:
    for key, value in payload.items():
        if key in {"name", "bio"}:
            # ok: python-mass-assignment
            setattr(user, key, value)


def find_user_augmented(conn, uid: str):
    sql = "SELECT * FROM users WHERE id = "
    sql += uid
    # ruleid: python-sqlalchemy-exec-driver-sql
    return conn.exec_driver_sql(sql)


def find_users(conn, active: bool):
    sql = "SELECT * FROM users"
    if active:
        sql += " WHERE active"
    # ok: python-sqlalchemy-exec-driver-sql
    return conn.exec_driver_sql(sql)


def unzip_check_ignored(archive: Path, dest: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            target = dest / name
            if target.resolve().is_relative_to(dest.resolve()):
                print("inside")
            # ruleid: python-zip-slip
            target.write_bytes(zf.read(name))


def unzip_check_unused(archive: Path, dest: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            target = dest / name
            inside = target.resolve().is_relative_to(dest.resolve())
            print(inside)
            # ruleid: python-zip-slip
            target.write_bytes(zf.read(name))


def unzip_relative_to(archive: Path, dest: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            target = dest / name
            # 置き場の外なら ValueError で止まる
            target.resolve().relative_to(dest.resolve())
            # ok: python-zip-slip
            target.write_bytes(zf.read(name))


def unzip_relative_to_swallowed(archive: Path, dest: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            target = dest / name
            try:
                target.resolve().relative_to(dest.resolve())
            except ValueError:
                print("outside")
            # ruleid: python-zip-slip
            target.write_bytes(zf.read(name))


def search_page_two_steps(q: str) -> HTMLResponse:
    tmpl = env.get_template("search.html")
    # ok: python-html-response-xss
    return HTMLResponse(tmpl.render(q=q))


def search_page_shared_env(q: str) -> HTMLResponse:
    # ok: python-html-response-xss
    return HTMLResponse(shared_env.get_template("search.html").render(q=q))


def search_page_app_state(request: Request, q: str) -> HTMLResponse:
    templates = request.app.state.templates
    # ok: python-html-response-xss
    return HTMLResponse(templates.get_template("search.html").render(q=q))


def search_page_plain_two_steps(q: str) -> HTMLResponse:
    tmpl = plain_env.get_template("search.html")
    # ruleid: python-html-response-xss
    return HTMLResponse(tmpl.render(q=q))


def update_local_allowed(user, payload: dict) -> None:
    allowed = {"name", "bio"}
    for key, value in payload.items():
        if key in allowed:
            # ok: python-mass-assignment
            setattr(user, key, value)


def update_nested(user, payload: dict) -> None:
    for key, value in payload.items():
        if key in ALLOWED:  # noqa: SIM102
            if key in payload:
                # ok: python-mass-assignment
                setattr(user, key, value)


def update_comprehension(user, payload: dict) -> None:
    allowed = {c.name for c in user.__table__.columns}
    for key, value in payload.items():
        if key in allowed:
            # ruleid: python-mass-assignment
            setattr(user, key, value)


WHERE_ACTIVE = " WHERE active"


def find_users_constant(conn, active: bool):
    sql = "SELECT * FROM users"
    if active:
        sql += WHERE_ACTIVE
    # ok: python-sqlalchemy-exec-driver-sql
    return conn.exec_driver_sql(sql)


def find_users_join(conn, active: bool, admin: bool):
    clauses = []
    if active:
        clauses.append("active")
    if admin:
        clauses.append("admin")
    sql = "SELECT * FROM users WHERE "
    sql += " AND ".join(clauses)
    # ok: python-sqlalchemy-exec-driver-sql
    return conn.exec_driver_sql(sql)


def unzip_relative_to_suppressed(archive: Path, dest: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            target = dest / name
            with contextlib.suppress(ValueError):
                target.resolve().relative_to(dest.resolve())
            # ruleid: python-zip-slip
            target.write_bytes(zf.read(name))


def update_value_check(user, payload: dict) -> None:
    for key, value in payload.items():
        # 値を確かめても、キーは絞れていない
        if value in {"on", "off"}:
            # ruleid: python-mass-assignment
            setattr(user, key, value)
