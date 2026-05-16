"""Pool de conexiones psycopg3."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import DB_DSN

pool = ConnectionPool(
    conninfo=DB_DSN,
    min_size=2,
    max_size=10,
    open=False,
    kwargs={"row_factory": dict_row},
)


def open_pool() -> None:
    pool.open()


def close_pool() -> None:
    pool.close()


@contextmanager
def get_conn() -> Iterator[Any]:
    with pool.connection() as conn:
        yield conn


def fetch_all(sql: str, params: tuple | dict | None = None) -> list[dict]:
    with pool.connection() as conn:
        # Si no hay params, no pasamos nada para evitar que psycopg
        # interprete '%' literales en el SQL como placeholders
        cur = conn.execute(sql, params) if params else conn.execute(sql)
        return cur.fetchall()


def fetch_one(sql: str, params: tuple | dict | None = None) -> dict | None:
    with pool.connection() as conn:
        cur = conn.execute(sql, params) if params else conn.execute(sql)
        return cur.fetchone()
