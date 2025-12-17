"""
title: SQL Database Tool
version: 2.0.0
description: SQLite database management for data storage, queries, and analysis.
author: Rinkatecam
author_url: https://github.com/Rinkatecam/AI.Stack
requirements: pydantic

# SYSTEM PROMPT FOR AI
# ====================
# Manage SQLite databases for persistent data storage.
# All databases are stored in the configured database directory.
#
# CAPABILITIES:
#   - Create/delete databases
#   - Create tables, insert, update, delete data
#   - Run SELECT queries
#   - Import/export CSV
#   - Backup and restore
"""

import sqlite3
import os
import csv
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        database_dir: str = Field(
            default="/data/databases",
            description="Directory for database storage"
        )
        max_results: int = Field(
            default=100,
            description="Maximum rows to return"
        )
        backup_dir: str = Field(
            default="/data/databases/backups",
            description="Directory for backups"
        )
        allow_dangerous_operations: bool = Field(
            default=False,
            description="Allow DROP TABLE, DELETE without WHERE"
        )

    def __init__(self):
        self.valves = self.Valves()
        self._ensure_directories()

    def _ensure_directories(self):
        os.makedirs(self.valves.database_dir, exist_ok=True)
        os.makedirs(self.valves.backup_dir, exist_ok=True)

    def _get_db_path(self, db_name: str) -> str:
        if not db_name.endswith('.db'):
            db_name = f"{db_name}.db"
        return os.path.join(self.valves.database_dir, db_name)

    def _connect(self, db_name: str) -> sqlite3.Connection:
        conn = sqlite3.connect(self._get_db_path(db_name))
        conn.row_factory = sqlite3.Row
        return conn

    def list_databases(self) -> str:
        """List all SQLite databases."""
        self._ensure_directories()
        databases = []
        for file in os.listdir(self.valves.database_dir):
            if file.endswith('.db'):
                path = os.path.join(self.valves.database_dir, file)
                size = os.path.getsize(path)
                size_str = f"{size / 1024:.1f} KB" if size >= 1024 else f"{size} B"
                databases.append(f"  - {file} ({size_str})")

        if not databases:
            return "No databases found.\n\nCreate one with: create_database('mydb')"
        return "**Databases:**\n\n" + "\n".join(databases)

    def create_database(self, db_name: str, description: str = "") -> str:
        """Create a new SQLite database."""
        db_path = self._get_db_path(db_name)
        if os.path.exists(db_path):
            return f"Database '{db_name}' already exists"

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE _metadata (key TEXT PRIMARY KEY, value TEXT)")
            cursor.execute("INSERT INTO _metadata VALUES ('created', ?)", (datetime.now().isoformat(),))
            cursor.execute("INSERT INTO _metadata VALUES ('description', ?)", (description,))
            conn.commit()
            conn.close()
            return f"Database '{db_name}' created at {db_path}"
        except Exception as e:
            return f"Error: {e}"

    def list_tables(self, db_name: str) -> str:
        """List all tables in a database."""
        try:
            conn = self._connect(db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cursor.fetchall()

            if not tables:
                conn.close()
                return f"Database '{db_name}' has no tables."

            result = [f"**Tables in '{db_name}':**\n"]
            for table in tables:
                name = table[0]
                if name.startswith('_'):
                    continue
                cursor.execute(f"SELECT COUNT(*) FROM [{name}]")
                count = cursor.fetchone()[0]
                result.append(f"  - {name} ({count} rows)")

            conn.close()
            return "\n".join(result)
        except Exception as e:
            return f"Error: {e}"

    def query(self, db_name: str, sql: str, params: Optional[List] = None) -> str:
        """Execute a SELECT query."""
        if not sql.strip().upper().startswith('SELECT'):
            return "Use query() for SELECT. Use execute() for INSERT/UPDATE/DELETE."

        try:
            conn = self._connect(db_name)
            cursor = conn.cursor()
            cursor.execute(sql, params or [])
            rows = cursor.fetchmany(self.valves.max_results)

            if not rows:
                conn.close()
                return "No results found."

            columns = [d[0] for d in cursor.description]
            result = ["| " + " | ".join(columns) + " |"]
            result.append("|" + "|".join(["---"] * len(columns)) + "|")

            for row in rows:
                values = [str(v) if v is not None else "" for v in row]
                result.append("| " + " | ".join(values) + " |")

            conn.close()
            return "\n".join(result) + f"\n\n{len(rows)} result(s)"
        except Exception as e:
            return f"Error: {e}"

    def execute(self, db_name: str, sql: str, params: Optional[List] = None) -> str:
        """Execute INSERT, UPDATE, DELETE, or DDL statement."""
        sql_upper = sql.strip().upper()

        if not self.valves.allow_dangerous_operations:
            if 'DROP TABLE' in sql_upper or 'DROP DATABASE' in sql_upper:
                return "DROP operations disabled. Enable in settings."
            if 'DELETE FROM' in sql_upper and 'WHERE' not in sql_upper:
                return "DELETE without WHERE disabled. Enable in settings."

        try:
            conn = self._connect(db_name)
            cursor = conn.cursor()
            cursor.execute(sql, params or [])
            affected = cursor.rowcount
            conn.commit()
            conn.close()

            if sql_upper.startswith('INSERT'):
                return f"Inserted {affected} row(s)"
            elif sql_upper.startswith('UPDATE'):
                return f"Updated {affected} row(s)"
            elif sql_upper.startswith('DELETE'):
                return f"Deleted {affected} row(s)"
            return "Statement executed"
        except Exception as e:
            return f"Error: {e}"

    def describe_table(self, db_name: str, table_name: str) -> str:
        """Show table structure."""
        try:
            conn = self._connect(db_name)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info([{table_name}])")
            columns = cursor.fetchall()

            if not columns:
                return f"Table '{table_name}' not found"

            result = [f"**Table: {table_name}**\n"]
            result.append("| Column | Type | Primary Key |")
            result.append("|--------|------|-------------|")

            for col in columns:
                pk = "Yes" if col[5] else ""
                result.append(f"| {col[1]} | {col[2]} | {pk} |")

            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            count = cursor.fetchone()[0]
            result.append(f"\nTotal rows: {count}")

            conn.close()
            return "\n".join(result)
        except Exception as e:
            return f"Error: {e}"

    def export_table(self, db_name: str, table_name: str) -> str:
        """Export table to CSV."""
        try:
            conn = self._connect(db_name)
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM [{table_name}]")
            rows = cursor.fetchall()
            columns = [d[0] for d in cursor.description]

            export_path = os.path.join(self.valves.database_dir, f"{db_name}_{table_name}.csv")

            with open(export_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow(row)

            conn.close()
            return f"Exported {len(rows)} rows to:\n{export_path}"
        except Exception as e:
            return f"Error: {e}"

    def import_csv(self, db_name: str, table_name: str, csv_path: str) -> str:
        """Import CSV into table."""
        if not os.path.exists(csv_path):
            return f"CSV file not found: {csv_path}"

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)
                data = list(reader)

            conn = self._connect(db_name)
            cursor = conn.cursor()

            cols = ", ".join([f"[{h}] TEXT" for h in headers])
            cursor.execute(f"CREATE TABLE IF NOT EXISTS [{table_name}] ({cols})")

            placeholders = ", ".join(["?"] * len(headers))
            cursor.executemany(f"INSERT INTO [{table_name}] VALUES ({placeholders})", data)

            conn.commit()
            conn.close()
            return f"Imported {len(data)} rows into '{table_name}'"
        except Exception as e:
            return f"Error: {e}"

    def backup_database(self, db_name: str) -> str:
        """Create backup of a database."""
        db_path = self._get_db_path(db_name)
        if not os.path.exists(db_path):
            return f"Database '{db_name}' not found"

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.valves.backup_dir, f"{db_name}_{timestamp}.db")

            source = sqlite3.connect(db_path)
            dest = sqlite3.connect(backup_path)
            source.backup(dest)
            source.close()
            dest.close()

            return f"Backup created:\n{backup_path}"
        except Exception as e:
            return f"Error: {e}"
