import os
import zipfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

app = FastAPI()

# ruleid: python-cors-credentials-any-origin
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True)

# ruleid: python-cors-credentials-any-origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ruleid: python-cors-credentials-any-origin
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origin_regex=".*")

# ruleid: python-cors-credentials-any-origin
app.add_middleware(CORSMiddleware, allow_origin_regex=r"^https://.*$", allow_credentials=True)

# ruleid: python-cors-credentials-any-origin
middleware = [Middleware(CORSMiddleware, allow_origins=["https://app.example", "*"], allow_credentials=True)]

# ok: python-cors-credentials-any-origin
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# ok: python-cors-credentials-any-origin
app.add_middleware(CORSMiddleware, allow_origins=["https://app.example"], allow_credentials=True)

# ok: python-cors-credentials-any-origin
app.add_middleware(CORSMiddleware, allow_origin_regex=r"https://.*\.example\.com", allow_credentials=True)


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
    for key in body:
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
