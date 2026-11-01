from contextlib import contextmanager

import mysql.connector
from flask import current_app, g
from mysql.connector import Error


def get_db():
    if "db" not in g:
        try:
            g.db = mysql.connector.connect(
                host=current_app.config["MYSQL_HOST"],
                port=current_app.config["MYSQL_PORT"],
                user=current_app.config["MYSQL_USER"],
                password=current_app.config["MYSQL_PASSWORD"],
                database=current_app.config["MYSQL_DATABASE"],
                autocommit=False,
            )
        except Error as exc:
            current_app.logger.exception("Could not connect to MySQL.")
            raise RuntimeError("Database connection failed.") from exc
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None and connection.is_connected():
        connection.close()


@contextmanager
def cursor(dictionary=False):
    connection = get_db()
    db_cursor = connection.cursor(dictionary=dictionary)
    try:
        yield db_cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        db_cursor.close()
