"""Catalyst Data Store backend — replaces SQLAlchemy/PostgreSQL.

Tables (created in Catalyst console, Project-Rainfall):
    Users, Workshops, Registrations, Certificates

Auth: ApplicationDefaultCredential — on AppSail the platform injects the
app credentials into the environment, so initialize_app() needs no args.

All public helpers are async (blocking SDK calls run in a thread) so the
FastAPI routers keep their `await` style unchanged.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from zcatalyst_sdk import initialize_app

# ---------------------------------------------------------------------------
# Table names (case-sensitive — must match the console exactly)
# ---------------------------------------------------------------------------
T_USERS = "Users"
T_WORKSHOPS = "Workshops"
T_REGS = "Registrations"
T_CERTS = "Certificates"

_app = None
_tables: dict[str, Any] = {}


def _catalyst_app():
    global _app
    if _app is None:
        _app = initialize_app()  # credentials from AppSail environment
    return _app


def _table(name: str):
    if name not in _tables:
        _tables[name] = _catalyst_app().datastore().table(name)
    return _tables[name]


def _zcql():
    return _catalyst_app().zcql()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _q(value: str) -> str:
    """Escape a string for use inside a ZCQL single-quoted literal."""
    return str(value).replace("'", "''")


def _to_bool(value: Any) -> bool:
    """Data Store booleans may come back as 'true'/'false' strings."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("true", "1", "yes")


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _unwrap(rows: list, table_name: str) -> list[dict]:
    """ZCQL wraps each row as {TableName: {...}} — flatten it."""
    out = []
    for r in rows:
        if isinstance(r, dict) and table_name in r and isinstance(r[table_name], dict):
            out.append(r[table_name])
        elif hasattr(r, "to_dict"):
            out.append(r.to_dict())
        elif isinstance(r, dict):
            out.append(r)
    return out


async def _zcql_all(query: str, table_name: str) -> list[dict]:
    zcql = _zcql()
    rows = await asyncio.to_thread(zcql.execute_query, query)
    return _unwrap(rows or [], table_name)


async def _zcql_one(query: str, table_name: str) -> Optional[dict]:
    rows = await _zcql_all(query, table_name)
    return rows[0] if rows else None


async def _insert(table_name: str, row: dict) -> dict:
    tbl = _table(table_name)
    inserted = await asyncio.to_thread(tbl.insert_row, row)
    data = inserted.to_dict() if hasattr(inserted, "to_dict") else dict(inserted)
    return data


async def _update(table_name: str, rowid: int, values: dict) -> dict:
    tbl = _table(table_name)
    payload = {"ROWID": str(rowid), **values}
    updated = await asyncio.to_thread(tbl.update_row, payload)
    data = updated.to_dict() if hasattr(updated, "to_dict") else dict(updated)
    return data


async def _delete(table_name: str, rowid: int) -> None:
    tbl = _table(table_name)
    await asyncio.to_thread(tbl.delete_row, rowid)


async def _get_by_rowid(table_name: str, rowid: int) -> Optional[dict]:
    tbl = _table(table_name)
    try:
        row = await asyncio.to_thread(tbl.get_row, rowid)
    except Exception:
        return None
    if row is None:
        return None
    data = row.to_dict() if hasattr(row, "to_dict") else dict(row)
    return data


# ---------------------------------------------------------------------------
# Entity dataclasses (attribute names match the old SQLAlchemy models so the
# Pydantic response schemas with from_attributes=True keep working)
# ---------------------------------------------------------------------------
@dataclass
class User:
    id: int
    email: str
    name: str
    password_hash: str
    role: str = "student"
    is_active: bool = True
    created_at: str = ""


@dataclass
class Workshop:
    id: int
    title: str
    slug: str
    description: Optional[str] = None
    category: str = "Cybersecurity"
    date: str = ""
    time: str = ""
    duration: str = ""
    mode: str = "Online"
    price: int = 0
    instructor: str = ""
    syllabus: Optional[str] = None
    max_seats: int = 100
    status: str = "upcoming"
    created_at: str = ""


@dataclass
class Registration:
    id: int
    reg_id: str = ""
    user_id: int = 0
    workshop_id: int = 0
    status: str = "registered"
    registered_at: str = ""


@dataclass
class Certificate:
    id: int
    cert_id: str = ""
    registration_id: int = 0
    user_id: int = 0
    workshop_id: int = 0
    template: str = "navy_gold"
    qr_data: Optional[str] = None
    revoked: bool = False
    issued_at: str = ""


# ---------------------------------------------------------------------------
# Row -> entity converters
# ---------------------------------------------------------------------------
def _user_from_row(r: dict) -> User:
    return User(
        id=_to_int(r.get("ROWID")),
        email=r.get("Email", ""),
        name=r.get("Name", ""),
        password_hash=r.get("PasswordHash", ""),
        role=r.get("Role", "student") or "student",
        is_active=_to_bool(r.get("IsActive", True)),
        created_at=str(r.get("CREATEDTIME", "")),
    )


def _workshop_from_row(r: dict) -> Workshop:
    return Workshop(
        id=_to_int(r.get("ROWID")),
        title=r.get("Title", ""),
        slug=r.get("Slug", ""),
        description=r.get("Description"),
        category=r.get("Category", "Cybersecurity") or "Cybersecurity",
        date=r.get("Date", "") or "",
        time=r.get("Time", "") or "",
        duration=r.get("Duration", "") or "",
        mode=r.get("Mode", "Online") or "Online",
        price=_to_int(r.get("Price")),
        instructor=r.get("Instructor", "") or "",
        syllabus=r.get("Syllabus"),
        max_seats=_to_int(r.get("MaxSeats"), 100),
        status=r.get("Status", "upcoming") or "upcoming",
        created_at=str(r.get("CREATEDTIME", "")),
    )


def _reg_from_row(r: dict) -> Registration:
    return Registration(
        id=_to_int(r.get("ROWID")),
        reg_id=r.get("RegId", "") or "",
        user_id=_to_int(r.get("UserRowId")),
        workshop_id=_to_int(r.get("WorkshopRowId")),
        status=r.get("Status", "registered") or "registered",
        registered_at=str(r.get("CREATEDTIME", "")),
    )


def _cert_from_row(r: dict) -> Certificate:
    return Certificate(
        id=_to_int(r.get("ROWID")),
        cert_id=r.get("CertId", "") or "",
        registration_id=_to_int(r.get("RegistrationRowId")),
        user_id=_to_int(r.get("UserRowId")),
        workshop_id=_to_int(r.get("WorkshopRowId")),
        template=r.get("Template", "navy_gold") or "navy_gold",
        qr_data=r.get("QrData"),
        revoked=_to_bool(r.get("Revoked", False)),
        issued_at=str(r.get("CREATEDTIME", "")),
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
async def get_user_by_email(email: str) -> Optional[User]:
    r = await _zcql_one(f"SELECT * FROM {T_USERS} WHERE Email = '{_q(email.strip().lower())}'", T_USERS)
    return _user_from_row(r) if r else None


async def get_user_by_id(user_id: int) -> Optional[User]:
    r = await _get_by_rowid(T_USERS, user_id)
    return _user_from_row(r) if r else None


async def create_user(email: str, name: str, password_hash: str, role: str = "student") -> User:
    r = await _insert(T_USERS, {
        "Email": email.strip().lower(),
        "Name": name.strip(),
        "PasswordHash": password_hash,
        "Role": role,
        "IsActive": True,
    })
    return _user_from_row(r)


async def update_user(user_id: int, values: dict) -> Optional[User]:
    # Map snake_case field names to Data Store columns
    col_map = {"name": "Name", "password_hash": "PasswordHash", "role": "Role", "is_active": "IsActive"}
    payload = {col_map[k]: v for k, v in values.items() if k in col_map}
    if not payload:
        return await get_user_by_id(user_id)
    r = await _update(T_USERS, user_id, payload)
    return _user_from_row(r) if r else None


# ---------------------------------------------------------------------------
# Workshops
# ---------------------------------------------------------------------------
async def list_workshops() -> list[Workshop]:
    rows = await _zcql_all(f"SELECT * FROM {T_WORKSHOPS} ORDER BY Date", T_WORKSHOPS)
    return [_workshop_from_row(r) for r in rows]


async def get_workshop_by_slug(slug: str) -> Optional[Workshop]:
    r = await _zcql_one(f"SELECT * FROM {T_WORKSHOPS} WHERE Slug = '{_q(slug)}'", T_WORKSHOPS)
    return _workshop_from_row(r) if r else None


async def get_workshop_by_id(workshop_id: int) -> Optional[Workshop]:
    r = await _get_by_rowid(T_WORKSHOPS, workshop_id)
    return _workshop_from_row(r) if r else None


async def create_workshop(data: dict) -> Workshop:
    col_map = {
        "title": "Title", "slug": "Slug", "description": "Description",
        "category": "Category", "date": "Date", "time": "Time",
        "duration": "Duration", "mode": "Mode", "price": "Price",
        "instructor": "Instructor", "syllabus": "Syllabus",
        "max_seats": "MaxSeats", "status": "Status",
    }
    payload = {col_map[k]: v for k, v in data.items() if k in col_map and v is not None}
    r = await _insert(T_WORKSHOPS, payload)
    return _workshop_from_row(r)


async def update_workshop(workshop_id: int, data: dict) -> Optional[Workshop]:
    col_map = {
        "title": "Title", "slug": "Slug", "description": "Description",
        "category": "Category", "date": "Date", "time": "Time",
        "duration": "Duration", "mode": "Mode", "price": "Price",
        "instructor": "Instructor", "syllabus": "Syllabus",
        "max_seats": "MaxSeats", "status": "Status",
    }
    payload = {col_map[k]: v for k, v in data.items() if k in col_map and v is not None}
    if not payload:
        return await get_workshop_by_id(workshop_id)
    r = await _update(T_WORKSHOPS, workshop_id, payload)
    return _workshop_from_row(r) if r else None


async def delete_workshop(workshop_id: int) -> None:
    await _delete(T_WORKSHOPS, workshop_id)


async def count_registrations_for_workshop(workshop_id: int) -> int:
    rows = await _zcql_all(
        f"SELECT COUNT(ROWID) FROM {T_REGS} WHERE WorkshopRowId = {int(workshop_id)}", T_REGS
    )
    # COUNT result comes back under the table key as well
    if rows:
        for v in rows[0].values():
            return _to_int(v)
    return 0


# ---------------------------------------------------------------------------
# Registrations
# ---------------------------------------------------------------------------
async def get_registration_by_id(reg_id: int) -> Optional[Registration]:
    r = await _get_by_rowid(T_REGS, reg_id)
    return _reg_from_row(r) if r else None


async def get_registration_by_user_workshop(user_id: int, workshop_id: int) -> Optional[Registration]:
    r = await _zcql_one(
        f"SELECT * FROM {T_REGS} WHERE UserRowId = {int(user_id)} AND WorkshopRowId = {int(workshop_id)}",
        T_REGS,
    )
    return _reg_from_row(r) if r else None


async def list_registrations_by_user(user_id: int) -> list[Registration]:
    rows = await _zcql_all(
        f"SELECT * FROM {T_REGS} WHERE UserRowId = {int(user_id)} ORDER BY CREATEDTIME DESC", T_REGS
    )
    return [_reg_from_row(r) for r in rows]


async def list_all_registrations() -> list[Registration]:
    rows = await _zcql_all(f"SELECT * FROM {T_REGS} ORDER BY CREATEDTIME DESC", T_REGS)
    return [_reg_from_row(r) for r in rows]


async def create_registration(reg_id: str, user_id: int, workshop_id: int, status: str = "registered") -> Registration:
    r = await _insert(T_REGS, {
        "RegId": reg_id,
        "UserRowId": int(user_id),
        "WorkshopRowId": int(workshop_id),
        "Status": status,
    })
    return _reg_from_row(r)


async def update_registration_status(reg_id: int, status: str) -> Optional[Registration]:
    r = await _update(T_REGS, reg_id, {"Status": status})
    return _reg_from_row(r) if r else None


async def delete_registration(reg_id: int) -> None:
    await _delete(T_REGS, reg_id)


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------
async def get_certificate_by_id(cert_rowid: int) -> Optional[Certificate]:
    r = await _get_by_rowid(T_CERTS, cert_rowid)
    return _cert_from_row(r) if r else None


async def get_certificate_by_cert_id(cert_id: str) -> Optional[Certificate]:
    r = await _zcql_one(f"SELECT * FROM {T_CERTS} WHERE CertId = '{_q(cert_id)}'", T_CERTS)
    return _cert_from_row(r) if r else None


async def get_certificate_by_registration(registration_id: int) -> Optional[Certificate]:
    r = await _zcql_one(
        f"SELECT * FROM {T_CERTS} WHERE RegistrationRowId = {int(registration_id)}", T_CERTS
    )
    return _cert_from_row(r) if r else None


async def list_certificates_by_user(user_id: int) -> list[Certificate]:
    rows = await _zcql_all(
        f"SELECT * FROM {T_CERTS} WHERE UserRowId = {int(user_id)} ORDER BY CREATEDTIME DESC", T_CERTS
    )
    return [_cert_from_row(r) for r in rows]


async def list_all_certificates() -> list[Certificate]:
    rows = await _zcql_all(f"SELECT * FROM {T_CERTS} ORDER BY CREATEDTIME DESC", T_CERTS)
    return [_cert_from_row(r) for r in rows]


async def create_certificate(
    cert_id: str, registration_id: int, user_id: int, workshop_id: int,
    template: str = "navy_gold", qr_data: Optional[str] = None,
) -> Certificate:
    r = await _insert(T_CERTS, {
        "CertId": cert_id,
        "RegistrationRowId": int(registration_id),
        "UserRowId": int(user_id),
        "WorkshopRowId": int(workshop_id),
        "Template": template,
        "QrData": qr_data or "",
        "Revoked": False,
    })
    return _cert_from_row(r)


async def set_certificate_revoked(cert_rowid: int, revoked: bool) -> Optional[Certificate]:
    r = await _update(T_CERTS, cert_rowid, {"Revoked": revoked})
    return _cert_from_row(r) if r else None


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
async def count_workshops_active() -> int:
    rows = await _zcql_all(f"SELECT COUNT(ROWID) FROM {T_WORKSHOPS} WHERE Status != 'draft'", T_WORKSHOPS)
    if rows:
        for v in rows[0].values():
            return _to_int(v)
    return 0


async def count_registrations() -> int:
    rows = await _zcql_all(f"SELECT COUNT(ROWID) FROM {T_REGS}", T_REGS)
    if rows:
        for v in rows[0].values():
            return _to_int(v)
    return 0


async def count_certificates_valid() -> int:
    rows = await _zcql_all(f"SELECT COUNT(ROWID) FROM {T_CERTS} WHERE Revoked = false", T_CERTS)
    if rows:
        for v in rows[0].values():
            return _to_int(v)
    return 0
