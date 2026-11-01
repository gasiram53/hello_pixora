"""Shared parameterized query helpers."""

from database.db_connection import cursor


def fetch_one(sql, params=()):
    with cursor(dictionary=True) as db_cursor:
        db_cursor.execute(sql, params)
        return db_cursor.fetchone()


def fetch_all(sql, params=()):
    with cursor(dictionary=True) as db_cursor:
        db_cursor.execute(sql, params)
        return db_cursor.fetchall()


def execute(sql, params=()):
    with cursor() as db_cursor:
        db_cursor.execute(sql, params)
        return db_cursor.lastrowid
