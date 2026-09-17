"""SQLite transactions that deterministically release Windows file handles."""
import sqlite3

class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()

def connect(*args, **kwargs):
    kwargs.setdefault("factory", ClosingConnection)
    return sqlite3.connect(*args, **kwargs)
