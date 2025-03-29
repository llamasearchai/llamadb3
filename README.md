# LlamaDB3

Database management and query optimization library for Python

## Features

- **Consistent Interface**: Work with multiple database engines (SQLite, MySQL, PostgreSQL) using a single, consistent API
- **Connection Pooling**: Efficiently manage database connections with connection pooling to improve performance
- **Fluent Query Builder**: Build SQL queries using a chainable API that makes query construction clean and intuitive
- **Error Handling**: Standardized error handling with detailed error information and appropriate error types
- **Type Hints**: Comprehensive type annotations for better IDE support and code completion

## Installation

```bash
pip install llamadb3
```

## Quick Start

```python
from llamadb3 import Connection, ConnectionPool
from llamadb3.query_builder import QueryBuilder, SQLDialect

# Create a connection to SQLite database
conn = Connection({
    'driver': 'sqlite',
    'database': 'my_database.db'
})

# Execute a simple query
cursor = conn.execute("SELECT * FROM users WHERE age > ?", (30,))
results = cursor.fetchall()

# Or use the query builder
query = (QueryBuilder()
    .select("id", "name", "email")
    .from_table("users")
    .where("age > ?", 30)
    .order_by("name")
    .limit(10)
)

# Get the SQL and parameters
sql, params = query.build()
cursor = conn.execute(sql, params)
results = cursor.fetchall()

# Use a connection pool for better performance
pool = ConnectionPool({
    'driver': 'mysql',
    'host': 'localhost',
    'user': 'root',
    'password': 'password',
    'database': 'my_database'
}, min_connections=5, max_connections=20)

# Use with context manager for automatic connection handling
with pool.connection() as conn:
    cursor = conn.execute("SELECT * FROM products WHERE price < ?", (100,))
    products = cursor.fetchall()

# Transaction support
with pool.transaction() as conn:
    conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (100, 1))
    conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (100, 2))
    # Transaction automatically commits if no errors, or rolls back on exception
```

## Advanced Query Building

```python
from llamadb3.query_builder import QueryBuilder, SQLDialect, JoinType, OrderDirection

# SELECT with JOIN, WHERE, and GROUP BY
query = (QueryBuilder(dialect=SQLDialect.POSTGRESQL)
    .select("u.id", "u.name", "COUNT(o.id) as order_count")
    .from_table("users u")
    .left_join("orders o", "o.user_id = u.id")
    .where("u.status = ?", "active")
    .where("o.created_at > ?", "2023-01-01")
    .group_by("u.id", "u.name")
    .having("COUNT(o.id) > ?", 5)
    .order_by("order_count", OrderDirection.DESC)
    .limit(10)
)

# INSERT
query = (QueryBuilder()
    .insert("users")
    .columns("name", "email", "created_at")
    .values(
        ("John Doe", "john@example.com", "2023-06-01"),
        ("Jane Smith", "jane@example.com", "2023-06-02")
    )
)

# UPDATE
query = (QueryBuilder()
    .update("products")
    .set("price", 19.99)
    .set("updated_at", "2023-06-15")
    .where("category_id = ?", 5)
    .where("price < ?", 15.0)
)

# DELETE
query = (QueryBuilder()
    .delete()
    .from_table("order_items")
    .where("order_id = ?", 1001)
)
```

## Error Handling

```python
from llamadb3 import Connection
from llamadb3.error_handler import DatabaseError, QueryError, ConnectionError

try:
    conn = Connection({
        'driver': 'postgresql',
        'host': 'localhost',
        'user': 'postgres',
        'password': 'password',
        'database': 'my_db'
    })
    
    conn.execute("SELECT * FROM non_existent_table")
except QueryError as e:
    print(f"Query error: {e}")
    # Specific error handling for query errors
except ConnectionError as e:
    print(f"Connection error: {e}")
    # Handle connection issues
except DatabaseError as e:
    print(f"Database error: {e}")
    print(f"Original error: {e.original_error}")
    print(f"Error code: {e.error_code}")
    print(f"Query: {e.query}")
    # General database error handling
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 