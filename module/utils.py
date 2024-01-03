import sqlite3

import sqlite_vss


def create_vss_connection(db_file: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_file, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.enable_load_extension(True)
    sqlite_vss.load(connection)
    connection.enable_load_extension(False)
    return connection
