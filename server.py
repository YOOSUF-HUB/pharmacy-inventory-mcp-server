from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from database import get_connection, init_database, row_to_dict

mcp = FastMCP("Pharmacy Inventory MCP - SQLite")

# Create the SQLite database automatically when the server starts.
init_database()


def enrich_item(item: dict[str, Any]) -> dict[str, Any]:
    """Add useful calculated fields before returning an item to the AI client."""
    item["needs_reorder"] = item["quantity_in_stock"] <= item["reorder_level"]
    item["stock_gap"] = max(item["reorder_level"] - item["quantity_in_stock"], 0)
    return item


@mcp.tool()
def get_lowest_stock_item() -> dict[str, Any]:
    """Return the single inventory item with the lowest current stock quantity."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM inventory_items
            ORDER BY quantity_in_stock ASC, name ASC
            LIMIT 1;
            """
        ).fetchone()

    if row is None:
        return {"message": "Inventory is empty."}

    return enrich_item(row_to_dict(row))


@mcp.tool()
def get_low_stock_items(limit: int = 5) -> list[dict[str, Any]]:
    """Return inventory items sorted from lowest stock to highest stock."""
    safe_limit = max(1, min(limit, 50))

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM inventory_items
            ORDER BY quantity_in_stock ASC, name ASC
            LIMIT ?;
            """,
            (safe_limit,),
        ).fetchall()

    return [enrich_item(row_to_dict(row)) for row in rows]


@mcp.tool()
def get_items_below_reorder_level() -> list[dict[str, Any]]:
    """Return all inventory items where current stock is less than or equal to the reorder level."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM inventory_items
            WHERE quantity_in_stock <= reorder_level
            ORDER BY (reorder_level - quantity_in_stock) DESC, quantity_in_stock ASC;
            """
        ).fetchall()

    return [enrich_item(row_to_dict(row)) for row in rows]


@mcp.tool()
def search_inventory_item(search_text: str) -> list[dict[str, Any]]:
    """Search inventory items by name, category, or supplier."""
    keyword = search_text.strip()
    if not keyword:
        return []

    like_pattern = f"%{keyword}%"

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM inventory_items
            WHERE name LIKE ? OR category LIKE ? OR supplier LIKE ?
            ORDER BY name ASC;
            """,
            (like_pattern, like_pattern, like_pattern),
        ).fetchall()

    return [enrich_item(row_to_dict(row)) for row in rows]


@mcp.tool()
def get_near_expiry_items(days: int = 30) -> list[dict[str, Any]]:
    """Return items that will expire within the next given number of days."""
    safe_days = max(1, min(days, 365))

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM inventory_items
            WHERE expiry_date IS NOT NULL
              AND date(expiry_date) >= date('now')
              AND date(expiry_date) <= date('now', '+' || ? || ' days')
            ORDER BY date(expiry_date) ASC;
            """,
            (safe_days,),
        ).fetchall()

    return [enrich_item(row_to_dict(row)) for row in rows]


@mcp.tool()
def get_expired_items() -> list[dict[str, Any]]:
    """Return inventory items that are already expired."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM inventory_items
            WHERE expiry_date IS NOT NULL
              AND date(expiry_date) < date('now')
            ORDER BY date(expiry_date) ASC;
            """
        ).fetchall()

    return [enrich_item(row_to_dict(row)) for row in rows]


@mcp.tool()
def update_stock(item_id: int, new_quantity: int) -> dict[str, Any]:
    """Update the stock quantity for one inventory item by item ID."""
    if item_id <= 0:
        return {"status": "error", "message": "item_id must be greater than 0."}

    if new_quantity < 0:
        return {"status": "error", "message": "new_quantity cannot be negative."}

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM inventory_items WHERE id = ?;",
            (item_id,),
        ).fetchone()

        if row is None:
            return {"status": "error", "message": f"No item found with id {item_id}."}

        connection.execute(
            """
            UPDATE inventory_items
            SET quantity_in_stock = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
            """,
            (new_quantity, item_id),
        )
        connection.commit()

        updated_row = connection.execute(
            "SELECT * FROM inventory_items WHERE id = ?;",
            (item_id,),
        ).fetchone()

    return {
        "status": "success",
        "message": "Stock updated successfully.",
        "item": enrich_item(row_to_dict(updated_row)),
    }


@mcp.tool()
def add_inventory_item(
    name: str,
    category: str,
    quantity_in_stock: int,
    reorder_level: int,
    supplier: str,
    unit_price: float,
    manufacture_date: str = "",
    expiry_date: str = "",
) -> dict[str, Any]:
    """Add a new item to the inventory database."""
    clean_name = name.strip()
    clean_category = category.strip()
    clean_supplier = supplier.strip()
    clean_manufacture_date = manufacture_date.strip() or None
    clean_expiry_date = expiry_date.strip() or None

    if not clean_name or not clean_category or not clean_supplier:
        return {"status": "error", "message": "name, category, and supplier are required."}

    if quantity_in_stock < 0 or reorder_level < 0 or unit_price < 0:
        return {"status": "error", "message": "quantity, reorder level, and unit price cannot be negative."}

    with get_connection() as connection:
        cursor = connection.execute(
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
            (
                clean_name,
                clean_category,
                quantity_in_stock,
                reorder_level,
                clean_supplier,
                clean_manufacture_date,
                clean_expiry_date,
                unit_price,
            ),
        )
        connection.commit()

        new_id = cursor.lastrowid
        row = connection.execute(
            "SELECT * FROM inventory_items WHERE id = ?;",
            (new_id,),
        ).fetchone()

    return {
        "status": "success",
        "message": "Inventory item added successfully.",
        "item": enrich_item(row_to_dict(row)),
    }


@mcp.tool()
def get_inventory_summary() -> dict[str, Any]:
    """Return high-level inventory counts and stock value summary."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total_items,
                SUM(CASE WHEN quantity_in_stock <= reorder_level THEN 1 ELSE 0 END) AS reorder_items,
                SUM(quantity_in_stock) AS total_units,
                ROUND(SUM(quantity_in_stock * unit_price), 2) AS estimated_stock_value
            FROM inventory_items;
            """
        ).fetchone()

    return row_to_dict(row)


if __name__ == "__main__":
    mcp.run()
