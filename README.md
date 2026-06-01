# Pharmacy Inventory MCP Server — SQLite + Claude Desktop

A beginner-friendly **Model Context Protocol (MCP)** server that connects an AI assistant to a pharmacy inventory database.

This project upgrades the first JSON-based MCP demo into a real **SQLite-backed inventory assistant**. It allows an AI client such as **Claude Desktop** to call predefined tools for stock checking, reorder analysis, expiry checks, item search, stock updates, and inventory summary generation.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Tools Exposed to the AI Client](#tools-exposed-to-the-ai-client)
- [Setup Instructions](#setup-instructions)
- [Run with MCP Inspector](#run-with-mcp-inspector)
- [Connect to Claude Desktop](#connect-to-claude-desktop)
- [Prompt Examples](#prompt-examples)
- [View the SQLite Database Manually](#view-the-sqlite-database-manually)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)
- [Future Improvements](#future-improvements)

---

## Overview

This project demonstrates how an AI assistant can safely perform inventory-related actions through an MCP server.

Instead of giving the AI direct database access, the MCP server exposes a controlled set of tools. The AI client can discover those tools, request approval from the user, call the relevant tool, and return the result in natural language.

### Example user prompt

```text
Show me the lowest stock medicine.
```

The AI client can call:

```text
get_lowest_stock_item
```

The MCP server then queries the SQLite database and returns the matching inventory record.

---

## Architecture

```text
Claude Desktop / MCP Inspector
          |
          | MCP tool call
          v
Pharmacy Inventory MCP Server
          |
          | SQL query
          v
SQLite Database
inventory.db
          |
          v
inventory_items table
```

### Old version

```text
MCP tool -> inventory.json
```

### New version

```text
MCP tool -> SQLite database -> inventory_items table
```

---

## Features

- SQLite database integration
- Automatic database and table creation
- Seed inventory data inserted on first run
- MCP tools for stock, expiry, reorder, search, and summary operations
- Claude Desktop integration
- MCP Inspector support for local testing
- Simple structure suitable for beginners and portfolio use
- No external database server required

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python |
| Protocol | Model Context Protocol |
| MCP Framework | FastMCP / MCP Python SDK |
| Database | SQLite |
| AI Client | Claude Desktop |
| Testing Tool | MCP Inspector |

---

## Project Structure

```text
pharmacy-mcp-server-sqlite/
│
├── server.py              # Main MCP server and tool definitions
├── requirements.txt       # Python dependencies
├── inventory.db           # SQLite database file, auto-created after first run
├── README.md              # Project documentation
└── pharmacy_mcp/          # Python virtual environment, created locally
```

> Note: `pharmacy_mcp/` and `inventory.db` are generated locally. They do not need to be committed to Git.

---

## Tools Exposed to the AI Client

### 1. `get_lowest_stock_item()`

Returns the inventory item with the lowest available stock.

Example prompt:

```text
Show me the lowest stock item.
```

---

### 2. `get_low_stock_items(limit=5)`

Returns a limited number of inventory items sorted by stock quantity in ascending order.

Example prompt:

```text
Show me the 5 lowest stock medicines.
```

---

### 3. `get_items_below_reorder_level()`

Returns all items where current stock is below or equal to the reorder level.

Example prompt:

```text
Which items need reordering?
```

---

### 4. `search_inventory_item(search_text)`

Searches inventory items by name, category, or supplier.

Example input:

```json
{
  "search_text": "tablet"
}
```

Example prompt:

```text
Search for tablet items in the inventory.
```

---

### 5. `get_near_expiry_items(days=30)`

Returns items that will expire within the given number of days.

Example input:

```json
{
  "days": 30
}
```

Example prompt:

```text
Which medicines will expire within the next 30 days?
```

---

### 6. `get_expired_items()`

Returns items that are already expired.

Example prompt:

```text
Show me all expired medicines.
```

---

### 7. `update_stock(item_id, new_quantity)`

Updates the stock quantity of a specific inventory item.

Example input:

```json
{
  "item_id": 3,
  "new_quantity": 40
}
```

Example prompt:

```text
Update item ID 3 stock quantity to 40.
```

---

### 8. `add_inventory_item(...)`

Adds a new item to the inventory database.

Example input:

```json
{
  "name": "Ibuprofen 400mg",
  "category": "Tablet",
  "quantity_in_stock": 60,
  "reorder_level": 25,
  "supplier": "PainRelief Distributors",
  "unit_price": 7.5,
  "manufacture_date": "2025-09-01",
  "expiry_date": "2027-09-01"
}
```

Example prompt:

```text
Add Ibuprofen 400mg as a new tablet item with 60 units in stock.
```

---

### 9. `get_inventory_summary()`

Returns a high-level summary of inventory status.

Example prompt:

```text
Give me an inventory summary.
```

---

## Setup Instructions

### 1. Open the project folder

```bash
cd pharmacy-mcp-server-sqlite
```

### 2. Create a Python virtual environment

```bash
python3 -m venv pharmacy_mcp
```

### 3. Activate the virtual environment

```bash
source pharmacy_mcp/bin/activate
```

Your terminal prompt should show something like:

```text
(pharmacy_mcp) yoosufahamed@Yoosufs-MacBook-Air pharmacy-mcp-server-sqlite %
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Run with MCP Inspector

MCP Inspector is useful for testing MCP tools before connecting to an AI client.

```bash
mcp dev server.py
```

This should open MCP Inspector in your browser.

If Inspector tries to use `uv` and fails, manually set the connection fields:

```text
Transport Type: STDIO
Command: python
Arguments: server.py
```

Then click **Connect**.

---

## Test Tools in MCP Inspector

### Get lowest stock item

Tool:

```text
get_lowest_stock_item
```

---

### Search inventory

Tool:

```text
search_inventory_item
```

Input:

```json
{
  "search_text": "tablet"
}
```

---

### Update stock

Tool:

```text
update_stock
```

Input:

```json
{
  "item_id": 3,
  "new_quantity": 40
}
```

---

### Add item

Tool:

```text
add_inventory_item
```

Input:

```json
{
  "name": "Ibuprofen 400mg",
  "category": "Tablet",
  "quantity_in_stock": 60,
  "reorder_level": 25,
  "supplier": "PainRelief Distributors",
  "unit_price": 7.5,
  "manufacture_date": "2025-09-01",
  "expiry_date": "2027-09-01"
}
```

---

## Connect to Claude Desktop

Claude Desktop can run local MCP servers through a configuration file.

### 1. Get your Python path

Inside the activated virtual environment, run:

```bash
which python
```

Example output:

```text
/Users/name/Desktop/Projects/pharmacy_mcp_sever Project/pharmacy-mcp-server-sqlite/pharmacy_mcp/bin/python
```

### 2. Get your project path

Run:

```bash
pwd
```

Example output:

```text
/Users/name/Desktop/Projects/pharmacy_mcp_sever Project/pharmacy-mcp-server-sqlite
```

Your `server.py` path will be:

```text
/Users/name/Desktop/Projects/pharmacy_mcp_sever Project/pharmacy-mcp-server-sqlite/server.py
```

---

### 3. Open Claude Desktop config

On macOS:

```bash
open -a TextEdit "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

If the file does not exist:

```bash
mkdir -p "$HOME/Library/Application Support/Claude"
touch "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
open -a TextEdit "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

---

### 4. Add MCP server configuration

If your config file already has a `preferences` object, add `mcpServers` as another top-level key.

Example:

```json
{
  "preferences": {
    "quickEntryShortcut": "double-tap-option",
    "sidebarMode": "chat"
  },
  "mcpServers": {
    "pharmacy-inventory": {
      "command": "/Users/name/Desktop/Projects/pharmacy_mcp_sever Project/pharmacy-mcp-server-sqlite/pharmacy_mcp/bin/python",
      "args": [
        "/Users/name/Desktop/Projects/pharmacy_mcp_sever Project/pharmacy-mcp-server-sqlite/server.py"
      ]
    }
  }
}
```

Replace the `command` value with your actual `which python` output.

Replace the `args` value with your actual `server.py` path.

---

### 5. Restart Claude Desktop

Fully quit Claude Desktop:

```text
Command + Q
```

Then reopen Claude Desktop.

Claude should now detect the `pharmacy-inventory` MCP server and its tools.

---

## Prompt Examples

After Claude Desktop is connected, try these prompts.

### Stock checking

```text
Use the pharmacy inventory tool and show me the lowest stock item.
```

```text
Show me the 5 lowest stock medicines.
```

```text
Which inventory items are below reorder level?
```

---

### Expiry checking

```text
Which medicines are already expired?
```

```text
Which medicines will expire within the next 30 days?
```

---

### Search

```text
Search the inventory for tablet items.
```

```text
Find all items supplied by HealthCare Suppliers.
```

---

### Stock update

```text
Update item ID 3 stock quantity to 40.
```

---

### Add new item

```text
Add a new medicine called Ibuprofen 400mg. Category is Tablet, quantity is 60, reorder level is 25, supplier is PainRelief Distributors, unit price is 7.5, manufacture date is 2025-09-01, and expiry date is 2027-09-01.
```

---

### Summary

```text
Give me a full inventory summary and tell me what needs attention.
```

---

## View the SQLite Database Manually

You can inspect the database using the SQLite CLI.

```bash
sqlite3 inventory.db
```

Show tables:

```sql
.tables
```

View inventory records:

```sql
SELECT id, name, quantity_in_stock, reorder_level FROM inventory_items;
```

Exit SQLite:

```sql
.quit
```

You can also use a GUI tool such as **DB Browser for SQLite** to inspect `inventory.db` visually.

---

## Troubleshooting

### Problem: `spawn uv ENOENT`

Cause:

MCP Inspector is trying to run `uv`, but `uv` is not installed.

Fix:

In MCP Inspector, manually set:

```text
Transport Type: STDIO
Command: python
Arguments: server.py
```

---

### Problem: `No module named mcp`

Cause:

Claude Desktop is using the wrong Python interpreter.

Fix:

Use the Python path from the activated virtual environment:

```bash
source pharmacy_mcp/bin/activate
which python
```

Paste that output into the Claude config `command` field.

---

### Problem: Claude does not show the MCP tools

Possible causes:

- Claude Desktop was not fully restarted
- JSON config has invalid syntax
- Wrong Python path
- Wrong `server.py` path
- MCP server crashed during startup

Fix:

1. Validate the config file format.
2. Confirm the Python path with `which python`.
3. Confirm the project path with `pwd`.
4. Fully quit Claude Desktop.
5. Reopen Claude Desktop.

---

### Problem: JSON config breaks after editing

Use one outer JSON object only.

Correct structure:

```json
{
  "preferences": {
    "sidebarMode": "chat"
  },
  "mcpServers": {
    "pharmacy-inventory": {
      "command": "/path/to/python",
      "args": [
        "/path/to/server.py"
      ]
    }
  }
}
```

---

## Security Notes

This project is for learning and local testing.

For production systems:

- Do not expose raw SQL execution tools
- Validate all user inputs
- Add authentication and authorization
- Use read-only tools where possible
- Log write actions such as stock updates
- Ask for user confirmation before destructive actions
- Avoid exposing sensitive customer, prescription, or staff data
- Restrict database access by role and permission level

The safe design principle is:

```text
The AI decides which tool to request.
The MCP server controls what is actually allowed.
```

---

## Future Improvements

- Replace SQLite with PostgreSQL or MySQL
- Connect to Django ORM
- Connect to MongoDB
- Add role-based access control
- Add audit logging for stock updates
- Add supplier reorder report generation
- Add PDF/CSV report generation
- Add dashboard API integration
- Add read-only and write-enabled tool separation
- Add unit tests for each MCP tool
- Add Docker support
- Deploy as a remote MCP server

---

## Demo Workflow

1. User prompts Claude Desktop
2. Claude calls MCP tool
3. MCP server queries/updates SQLite
4. Audit log records the action
5. Claude explains the result

---