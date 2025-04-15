"""
Basic Usage Example for LlamaDB3

This example demonstrates the core functionality of LlamaDB3:
- Creating a database connection
- Executing direct SQL queries
- Using the query builder
- Working with connection pools
- Handling transactions
"""

import logging
import os
from typing import Any, Dict, List

from llamadb3 import Connection, ConnectionPool
from llamadb3.error_handler import DatabaseError, handle_error
from llamadb3.query_builder import QueryBuilder, SQLDialect

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create a temporary database for the example
DB_FILE = "example.db"


def setup_database() -> None:
    """Create a sample database schema and insert test data."""
    connection_params = {"driver": "sqlite", "database": DB_FILE}

    try:
        conn = Connection(connection_params)

        # Create users table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                age INTEGER,
                created_at TEXT
            )
        """
        )

        # Create orders table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """
        )

        # Insert sample users if the table is empty
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            users = [
                ("John Doe", "john@example.com", 35, "2023-01-01"),
                ("Jane Smith", "jane@example.com", 28, "2023-01-15"),
                ("Bob Johnson", "bob@example.com", 42, "2023-02-10"),
                ("Alice Brown", "alice@example.com", 31, "2023-03-05"),
                ("Charlie Wilson", "charlie@example.com", 25, "2023-04-20"),
            ]

            conn.execute_many(
                "INSERT INTO users (name, email, age, created_at) VALUES (?, ?, ?, ?)",
                users,
            )

            # Insert sample orders
            orders = [
                (1, 150.00, "completed", "2023-02-15"),
                (1, 75.50, "completed", "2023-03-10"),
                (2, 220.00, "completed", "2023-02-20"),
                (3, 35.99, "pending", "2023-04-25"),
                (4, 125.75, "completed", "2023-04-12"),
                (5, 89.99, "cancelled", "2023-05-01"),
                (2, 44.50, "pending", "2023-05-10"),
            ]

            conn.execute_many(
                "INSERT INTO orders (user_id, amount, status, created_at) VALUES (?, ?, ?, ?)",
                orders,
            )

            conn.commit()
            logger.info("Database initialized with sample data")
        else:
            logger.info("Database already contains data")

        conn.close()

    except DatabaseError as e:
        logger.error(f"Database setup error: {e}")
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        raise


def example_direct_queries() -> None:
    """Example of executing direct SQL queries."""
    logger.info("\n=== Direct Query Examples ===")

    try:
        # Create a connection
        conn = Connection({"driver": "sqlite", "database": DB_FILE})

        # Simple SELECT query
        logger.info("Executing simple SELECT query...")
        cursor = conn.execute("SELECT * FROM users")
        users = cursor.fetchall()
        logger.info(f"Found {len(users)} users")
        for user in users:
            logger.info(f"User: {user}")

        # Query with parameters
        logger.info("\nExecuting parameterized query...")
        cursor = conn.execute("SELECT * FROM users WHERE age > ?", (30,))
        users = cursor.fetchall()
        logger.info(f"Found {len(users)} users over 30")
        for user in users:
            logger.info(f"User: {user}")

        # JOIN query
        logger.info("\nExecuting JOIN query...")
        cursor = conn.execute(
            """
            SELECT u.name, COUNT(o.id) as order_count, SUM(o.amount) as total_spent
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            GROUP BY u.id
            ORDER BY total_spent DESC
        """
        )

        user_stats = cursor.fetchall()
        logger.info("User order statistics:")
        for user_stat in user_stats:
            logger.info(f"User: {user_stat}")

        conn.close()

    except DatabaseError as e:
        logger.error(f"Error during direct query examples: {e}")


def example_query_builder() -> None:
    """Example of using the QueryBuilder to construct queries."""
    logger.info("\n=== Query Builder Examples ===")

    try:
        # Create a connection
        conn = Connection({"driver": "sqlite", "database": DB_FILE})

        # Simple SELECT query
        logger.info("Building simple SELECT query...")
        query = (
            QueryBuilder(dialect=SQLDialect.SQLITE)
            .select("id", "name", "email", "age")
            .from_table("users")
            .order_by("name")
        )

        logger.info(f"Generated SQL: {query.get_sql()}")
        sql, params = query.build()
        cursor = conn.execute(sql, params)
        users = cursor.fetchall()
        logger.info(f"Found {len(users)} users")

        # WHERE query
        logger.info("\nBuilding query with WHERE conditions...")
        query = (
            QueryBuilder()
            .select("*")
            .from_table("users")
            .where("age > ?", 30)
            .order_by("age", "DESC")
        )

        logger.info(f"Generated SQL: {query.get_sql()}")
        sql, params = query.build()
        cursor = conn.execute(sql, params)
        users = cursor.fetchall()
        logger.info(f"Found {len(users)} users over 30")

        # JOIN query with GROUP BY
        logger.info("\nBuilding complex JOIN query with GROUP BY...")
        query = (
            QueryBuilder()
            .select(
                "u.id",
                "u.name",
                "COUNT(o.id) as order_count",
                "SUM(o.amount) as total_spent",
            )
            .from_table("users u")
            .left_join("orders o", "u.id = o.user_id")
            .group_by("u.id", "u.name")
            .having("COUNT(o.id) > ?", 0)
            .order_by("total_spent", "DESC")
        )

        logger.info(f"Generated SQL: {query.get_sql()}")
        sql, params = query.build()
        cursor = conn.execute(sql, params)
        user_stats = cursor.fetchall()
        logger.info("User order statistics:")
        for user_stat in user_stats:
            logger.info(f"Stats: {user_stat}")

        # INSERT query
        logger.info("\nBuilding INSERT query...")
        query = (
            QueryBuilder()
            .insert("users")
            .columns("name", "email", "age", "created_at")
            .values(("David Miller", "david@example.com", 38, "2023-06-01"))
        )

        logger.info(f"Generated SQL: {query.get_sql()}")
        sql, params = query.build()
        cursor = conn.execute(sql, params)
        conn.commit()
        logger.info(f"Inserted {cursor.rowcount} user")

        # UPDATE query
        logger.info("\nBuilding UPDATE query...")
        query = (
            QueryBuilder()
            .update("users")
            .set("age", 39)
            .where("email = ?", "david@example.com")
        )

        logger.info(f"Generated SQL: {query.get_sql()}")
        sql, params = query.build()
        cursor = conn.execute(sql, params)
        conn.commit()
        logger.info(f"Updated {cursor.rowcount} user")

        conn.close()

    except DatabaseError as e:
        logger.error(f"Error during query builder examples: {e}")


def example_connection_pool() -> None:
    """Example of using the ConnectionPool."""
    logger.info("\n=== Connection Pool Examples ===")

    try:
        # Create a connection pool
        pool = ConnectionPool(
            {"driver": "sqlite", "database": DB_FILE},
            min_connections=2,
            max_connections=5,
        )

        # Use the pool with context manager
        logger.info("Using connection pool with context manager...")
        with pool.connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            logger.info(f"User count: {count}")

        # Multiple concurrent operations
        logger.info("\nPerforming multiple operations with connection pool...")
        operations = [
            "SELECT * FROM users WHERE id = 1",
            "SELECT * FROM users WHERE id = 2",
            "SELECT * FROM users WHERE id = 3",
            "SELECT * FROM orders WHERE user_id = 1",
            "SELECT * FROM orders WHERE status = 'pending'",
        ]

        results = []
        for operation in operations:
            with pool.connection() as conn:
                cursor = conn.execute(operation)
                results.append(cursor.fetchall())

        logger.info(f"Completed {len(operations)} operations")

        # Transaction example
        logger.info("\nUsing transaction with connection pool...")
        with pool.transaction() as conn:
            # Update a user's age
            conn.execute("UPDATE users SET age = age + 1 WHERE id = 1")

            # Get the updated user
            cursor = conn.execute("SELECT name, age FROM users WHERE id = 1")
            user = cursor.fetchone()
            logger.info(f"Updated user: {user}")

            # Transaction automatically commits at the end of the block

        # Cleanup the pool
        logger.info("Closing connection pool...")
        pool.close_all()

    except DatabaseError as e:
        logger.error(f"Error during connection pool examples: {e}")


def cleanup() -> None:
    """Clean up resources after the example."""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        logger.info(f"Removed example database file: {DB_FILE}")


if __name__ == "__main__":
    try:
        # Setup
        setup_database()

        # Run examples
        example_direct_queries()
        example_query_builder()
        example_connection_pool()

    except Exception as e:
        logger.exception(f"Example failed: {e}")

    finally:
        cleanup()
