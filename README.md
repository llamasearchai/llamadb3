# LlamaDB3 🦙💾

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
<!-- Add PyPI version, build status, coverage badges -->

**Consistent & Fluent Database Access for Python**

`LlamaDB3` is a Python library designed to provide a consistent, intuitive, and fluent interface for interacting with various SQL databases. It aims to simplify common database operations, including connection management, query building, and error handling, allowing developers to focus on application logic rather than database-specific boilerplate.

## Key Features ✨

*   **Multi-Engine Support**: Works seamlessly with SQLite, MySQL, and PostgreSQL using a unified API.
*   **Connection Pooling**: Efficiently manages database connections for improved performance and resource utilization.
*   **Fluent Query Builder**: Construct complex SQL queries programmatically using a clean, chainable interface.
*   **Robust Error Handling**: Provides standardized exception types for better error management.
*   **Type Hinted**: Fully type-hinted codebase for enhanced developer experience and static analysis.
*   **Transaction Management**: Simple context manager for handling database transactions.
*   **Lightweight**: Minimal dependencies, focusing on core database interaction.

## Architecture Concept 🏛️

```mermaid
graph TD
    A[Your Application] --> B(LlamaDB3 API);
    B --> C{Connection Manager / Pool};
    B --> D[Fluent Query Builder];
    C --> E[DB Driver (sqlite3)];
    C --> F[DB Driver (mysql.connector)];
    C --> G[DB Driver (psycopg2)];
    D -- SQL + Params --> C;
    E --> H[(SQLite)];
    F --> I[(MySQL)];
    G --> J[(PostgreSQL)];

    style B fill:#eef,stroke:#333,stroke-width:2px
    style D fill:#efe,stroke:#333,stroke-width:1px
```
*Diagram showing the application using the LlamaDB3 API, which includes a Connection Manager/Pool and a Query Builder. The Connection Manager interacts with underlying database drivers (like sqlite3, mysql.connector, psycopg2) to communicate with the actual databases.*

## Installation 💻

```bash
# Install the core library
pip install llamadb3

# Install with support for specific databases:
pip install llamadb3[mysql]   # For MySQL support (requires mysql-connector-python)
pip install llamadb3[postgres] # For PostgreSQL support (requires psycopg2-binary)
# SQLite support is built-in
```

## Quick Start 🚀

```python
from llamadb3 import Connection, ConnectionPool
from llamadb3.query_builder import QueryBuilder

# 1. Single Connection (SQLite)
print("--- Single Connection Example (SQLite) ---")
conn = Connection({
    'driver': 'sqlite',
    'database': ':memory:' # In-memory database
})

# Execute directly
conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")
conn.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("Alice", 30))
conn.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("Bob", 25))

cursor = conn.execute("SELECT * FROM users WHERE age > ?", (20,))
print("Users older than 20:", cursor.fetchall())
conn.close()

# 2. Query Builder
print("\n--- Query Builder Example ---")
conn = Connection({'driver': 'sqlite', 'database': ':memory:'})
conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)")

query = (QueryBuilder()
    .insert("products")
    .columns("name", "price")
    .values(("Laptop", 1200.50), ("Keyboard", 75.00))
)
sql, params = query.build()
conn.execute(sql, params)

query = (QueryBuilder()
    .select("name", "price")
    .from_table("products")
    .where("price < ?", 100.0)
)
sql, params = query.build()
cursor = conn.execute(sql, params)
print("Products under $100:", cursor.fetchall())
conn.close()

# 3. Connection Pool (Example assumes MySQL is running)
# print("\n--- Connection Pool Example (MySQL) ---")
# try:
#     pool = ConnectionPool({
#         'driver': 'mysql',
#         'host': 'localhost',
#         'user': 'testuser',
#         'password': 'password',
#         'database': 'testdb'
#     }, min_connections=1, max_connections=5)
# 
#     with pool.connection() as conn:
#         cursor = conn.execute("SELECT %s AS message", ("Hello from Pool!",))
#         print(cursor.fetchone())
# 
#     pool.close()
# except Exception as e:
#     print(f"MySQL Pool Example Failed (MySQL running? Credentials correct?): {e}")

# 4. Transactions
print("\n--- Transaction Example ---")
conn = Connection({'driver': 'sqlite', 'database': ':memory:'})
conn.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance REAL)")
conn.execute("INSERT INTO accounts (id, balance) VALUES (?, ?), (?, ?)", (1, 1000.0, 2, 500.0))

try:
    with conn.transaction():
        conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (100.0, 1))
        # Simulate an error: conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (1000.0, 2)) # This would fail balance constraint potentially
        conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (100.0, 2))
        print("Transaction successful (within context)")
except Exception as e:
    print(f"Transaction failed and rolled back: {e}")

cursor = conn.execute("SELECT * FROM accounts")
print("Account balances after transaction attempt:", cursor.fetchall())
conn.close()

```

## Documentation 📚

*   Explore Python docstrings using `help()`.
*   Check the `docs/` directory for more detailed guides (if available).

## Testing 🧪

```bash
# Ensure testing dependencies are installed (e.g., pytest)
pip install pytest

# Run tests (adjust command as needed)
pytest
```

## Contributing 🤝

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License 📄

Licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support & Community 💬

*   **Issues**: [GitHub Issues](https://llamasearch.ai *(Update link)*
*   **Discord**: [Community Discord](https://discord.gg/llamasearch) *(Update link)*

---

*Part of the LlamaSearchAI Ecosystem - Simplified Database Interaction in Python.* 
# Updated in commit 1 - 2025-04-04 17:15:51

# Updated in commit 9 - 2025-04-04 17:15:52

# Updated in commit 17 - 2025-04-04 17:15:53

# Updated in commit 25 - 2025-04-04 17:15:54

# Updated in commit 1 - 2025-04-05 14:29:37

# Updated in commit 9 - 2025-04-05 14:29:37

# Updated in commit 17 - 2025-04-05 14:29:37

# Updated in commit 25 - 2025-04-05 14:29:37

# Updated in commit 1 - 2025-04-05 15:15:52
