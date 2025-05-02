import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'toolai.db')

class SQLiteModel:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS command_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    def add_command(self, command: str):
        with self.conn:
            self.conn.execute('INSERT INTO command_history (command) VALUES (?)', (command,))

    def get_history(self, limit=20):
        cur = self.conn.cursor()
        cur.execute('SELECT command, created_at FROM command_history ORDER BY id DESC LIMIT ?', (limit,))
        return cur.fetchall()

    def clear_history(self):
        with self.conn:
            self.conn.execute('DELETE FROM command_history') 