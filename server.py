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
    """Update the stock quantity for a specific inventory item and record an audit log."""
    if item_id <= 0:
        return {"error": "Item ID must be a positive number."}

    if new_quantity < 0:
        return {"error": "Stock quantity cannot be negative."}

    with get_connection() as connection:
        item = connection.execute(
            """
            SELECT *
            FROM inventory_items
            WHERE id = ?;
            """,
            (item_id,),
        ).fetchone()

        if item is None:
            return {"error": f"No inventory item found with ID {item_id}."}

        old_quantity = item["quantity_in_stock"]
        item_name = item["name"]

        connection.execute(
            """
            UPDATE inventory_items
            SET quantity_in_stock = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
            """,
            (new_quantity, item_id),
        )

        create_audit_log(
            connection=connection,
            action="UPDATE_STOCK",
            item_id=item_id,
            item_name=item_name,
            old_value=str(old_quantity),
            new_value=str(new_quantity),
            details=f"Stock quantity changed from {old_quantity} to {new_quantity}.",
        )

        connection.commit()

        updated_item = connection.execute(
            """
            SELECT *
            FROM inventory_items
            WHERE id = ?;
            """,
            (item_id,),
        ).fetchone()

        return {
            "message": "Stock updated successfully and audit log recorded.",
            "updated_item": row_to_dict(updated_item),
            "audit": {
                "action": "UPDATE_STOCK",
                "item_id": item_id,
                "item_name": item_name,
                "old_quantity": old_quantity,
                "new_quantity": new_quantity,
            },
        }


@mcp.tool()
def add_inventory_item(
    name: str,
    category: str,
    quantity_in_stock: int,
    reorder_level: int,
    supplier: str,
    unit_price: float,
    manufacture_date: str,
    expiry_date: str,
) -> dict[str, Any]:
    """Add a new inventory item and record an audit log."""
    name = name.strip()
    category = category.strip()
    supplier = supplier.strip()

    if not name:
        return {"error": "Item name cannot be empty."}

    if not category:
        return {"error": "Category cannot be empty."}

    if not supplier:
        return {"error": "Supplier cannot be empty."}

    if quantity_in_stock < 0:
        return {"error": "Stock quantity cannot be negative."}

    if reorder_level < 0:
        return {"error": "Reorder level cannot be negative."}

    if unit_price < 0:
        return {"error": "Unit price cannot be negative."}

    if manufacture_date > expiry_date:
        return {"error": "Expiry date must be after manufacture date."}

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
                name,
                category,
                quantity_in_stock,
                reorder_level,
                supplier,
                manufacture_date,
                expiry_date,
                unit_price,
            ),
        )

        new_item_id = cursor.lastrowid

        create_audit_log(
            connection=connection,
            action="ADD_ITEM",
            item_id=new_item_id,
            item_name=name,
            old_value=None,
            new_value=str(quantity_in_stock),
            details=f"New inventory item added with initial stock quantity {quantity_in_stock}.",
        )

        connection.commit()

        new_item = connection.execute(
            """
            SELECT *
            FROM inventory_items
            WHERE id = ?;
            """,
            (new_item_id,),
        ).fetchone()

        return {
            "message": "Inventory item added successfully and audit log recorded.",
            "item": row_to_dict(new_item),
            "audit": {
                "action": "ADD_ITEM",
                "item_id": new_item_id,
                "item_name": name,
                "initial_quantity": quantity_in_stock,
            },
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


def create_audit_log(
    connection: sqlite3.Connection,
    action: str,
    item_id: int | None = None,
    item_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    details: str | None = None,
    performed_by: str = "Claude Desktop / MCP Client",
) -> None:
    """Insert an audit log entry for important inventory actions."""
    connection.execute(
        """
        INSERT INTO audit_logs (
            action,
            item_id,
            item_name,
            old_value,
            new_value,
            details,
            performed_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (
            action,
            item_id,
            item_name,
            old_value,
            new_value,
            details,
            performed_by,
        ),
    )

@mcp.tool()
def get_audit_logs(limit: int = 10) -> list[dict[str, Any]]:
    """Return the latest audit log entries."""
    if limit <= 0:
        limit = 10

    if limit > 100:
        limit = 100

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM audit_logs
            ORDER BY created_at DESC, id DESC
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()

        return [row_to_dict(row) for row in rows]


@mcp.tool()
def get_audit_logs_for_item(item_id: int) -> list[dict[str, Any]]:
    """Return audit logs for a specific inventory item."""
    if item_id <= 0:
        return [{"error": "Item ID must be a positive number."}]

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM audit_logs
            WHERE item_id = ?
            ORDER BY created_at DESC, id DESC;
            """,
            (item_id,),
        ).fetchall()

        return [row_to_dict(row) for row in rows]


@mcp.tool()
def get_database_path() -> dict[str, str]:
    """Return the absolute SQLite database path used by this MCP server."""
    return {
        "database_path": str(DB_PATH),
        "server_path": str(Path(__file__).resolve()),
    }



if __name__ == "__main__":
    mcp.run()
