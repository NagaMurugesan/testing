import psycopg2
from psycopg2.extras import RealDictCursor
from mcp.server.fastmcp import FastMCP, Context

# Initialize MCP server
mcp = FastMCP("PostgresServer")

# PostgreSQL connection settings
DB_CONFIG = {
    "user": "postgres",          # replace with your username
    "password": "admin@123", # replace with your password
    "dbname": "postgres",   # replace with your database
    "host": "localhost",
    "port": 5433
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

# ------------------------------
# READ
# ------------------------------
@mcp.tool()
def get_employee_details(ctx: Context, employee_id: int) -> str:
    """Fetch employee details from PostgreSQL by employee_id."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, department, salary FROM employee WHERE id = %s", (employee_id,))
        row = cur.fetchone()
        if row:
            return f"ID: {row['id']}, Name: {row['name']}, Department: {row['department']}, Salary: {row['salary']}"
        else:
            return f"No employee found with ID {employee_id}"
    finally:
        cur.close()
        conn.close()

@mcp.tool()
def list_employees(ctx: Context) -> str:
    """Fetch all employees from the employee table."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, department, salary FROM employee ORDER BY id")
        rows = cur.fetchall()
        if not rows:
            return "No employees found"
        return "\n".join([f"ID: {r['id']}, Name: {r['name']}, Dept: {r['department']}, Salary: {r['salary']}" for r in rows])
    finally:
        cur.close()
        conn.close()

# ------------------------------
# CREATE
# ------------------------------
@mcp.tool()
def add_employee(ctx: Context, name: str, department: str, salary: float) -> str:
    """Insert a new employee record into PostgreSQL."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO employee (name, department, salary) VALUES (%s, %s, %s) RETURNING id", 
                    (name, department, salary))
        new_id = cur.fetchone()["id"]
        conn.commit()
        return f"Employee added with ID {new_id}"
    finally:
        cur.close()
        conn.close()

# ------------------------------
# UPDATE
# ------------------------------
@mcp.tool()
def update_employee(ctx: Context, employee_id: int, name: str = None, department: str = None, salary: float = None) -> str:
    """Update an existing employee record (only provided fields)."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        updates, values = [], []
        if name:
            updates.append("name=%s")
            values.append(name)
        if department:
            updates.append("department=%s")
            values.append(department)
        if salary:
            updates.append("salary=%s")
            values.append(salary)

        if not updates:
            return "No fields provided for update"

        values.append(employee_id)
        query = f"UPDATE employee SET {', '.join(updates)} WHERE id=%s RETURNING id"
        cur.execute(query, tuple(values))
        row = cur.fetchone()
        conn.commit()

        if row:
            return f"Employee {employee_id} updated successfully"
        else:
            return f"No employee found with ID {employee_id}"
    finally:
        cur.close()
        conn.close()

# ------------------------------
# DELETE
# ------------------------------
@mcp.tool()
def delete_employee(ctx: Context, employee_id: int) -> str:
    """Delete an employee record by ID."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM employee WHERE id=%s RETURNING id", (employee_id,))
        row = cur.fetchone()
        conn.commit()
        if row:
            return f"Employee {employee_id} deleted successfully"
        else:
            return f"No employee found with ID {employee_id}"
    finally:
        cur.close()
        conn.close()

# ------------------------------
# Run the MCP server
# ------------------------------
if __name__ == "__main__":
    mcp.run()
