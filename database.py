from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "inventory.db"


SEED_ITEMS: list[tuple[str, str, int, int, str, str, str, float]] = [
    ("Paracetamol 500mg", "Tablet", 120, 50, "HealthPlus Distributors", "2025-01-10", "2027-01-10", 4.50),
    ("Amoxicillin 250mg", "Capsule", 18, 30, "MediLine Suppliers", "2025-03-01", "2026-03-01", 12.00),
    ("Cetirizine 10mg", "Tablet", 8, 25, "Nova Pharma", "2025-06-15", "2026-01-15", 6.75),
    ("Salbutamol Inhaler", "Inhaler", 14, 15, "RespiraCare", "2025-04-12", "2026-04-12", 950.00),
    ("Vitamin C 1000mg", "Tablet", 75, 20, "Wellness Lanka", "2025-08-05", "2027-08-05", 9.25),
    ("Metformin 500mg", "Tablet", 22, 40, "GlucoseCare Pharma", "2025-05-20", "2026-05-20", 8.50),
    ("Omeprazole 20mg", "Capsule", 35, 30, "GastroMed Suppliers", "2025-07-01", "2027-07-01", 10.50),
]


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection and return rows as dictionary-like objects."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a sqlite3.Row object into a normal Python dictionary."""
    return dict(row)


def init_database() -> None:
    """Create the inventory table and insert seed rows if the table is empty."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                quantity_in_stock INTEGER NOT NULL CHECK(quantity_in_stock >= 0),
                reorder_level INTEGER NOT NULL CHECK(reorder_level >= 0),
                supplier TEXT NOT NULL,
                manufacture_date TEXT,
                expiry_date TEXT,
                unit_price REAL NOT NULL CHECK(unit_price >= 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        count = connection.execute("SELECT COUNT(*) FROM inventory_items").fetchone()[0]
        if count == 0:
            connection.executemany(
                """
                INSERT INTO inventory_items (
                    name,
                    category,
                    quantity_in_stock,
                    reorder_level,
                    supplier,
                    manufacture_date,
                    expiry_date,
                    unit_price
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                SEED_ITEMS,
            )

        connection.commit()
