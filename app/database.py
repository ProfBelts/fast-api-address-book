"""SQLite storage using the standard library sqlite3 module."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing

DB_PATH = "addresses.db"


def connect() -> sqlite3.Connection:
    # Autocommit: every route runs a single statement, so no explicit transactions are needed.
    # check_same_thread=False: FastAPI may open and use the connection in different threads.
    connection = sqlite3.connect(DB_PATH, isolation_level=None, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with closing(connect()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL
            )
            """
        )


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per request, closed afterwards."""
    with closing(connect()) as connection:
        yield connection
