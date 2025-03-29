"""
LlamaDB3: Database management and query optimization package.

This package provides a consistent interface for database operations,
connection pooling, standardized query building, and robust error handling.
"""

__version__ = "0.1.0"

from llamadb3.connection import Connection, ConnectionPool
from llamadb3.query_builder import QueryBuilder
from llamadb3.error_handler import handle_error, DatabaseError

__all__ = [
    "Connection",
    "ConnectionPool",
    "QueryBuilder",
    "handle_error",
    "DatabaseError",
] 