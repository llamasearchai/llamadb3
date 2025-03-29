"""
Error handling module for LlamaDB3.

This module provides standardized error handling for database operations,
with consistent error types and detailed error information.
"""

import logging
import sys
import traceback
from typing import Optional, Dict, Any, Type, Union

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Base exception class for all database-related errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None,
                 error_code: Optional[str] = None, query: Optional[str] = None,
                 params: Optional[Any] = None):
        """
        Initialize a database error.
        
        Args:
            message: Error message describing the error
            original_error: The original exception that caused this error
            error_code: A code identifying the error type
            query: The SQL query that caused the error (if applicable)
            params: The parameters that were used with the query
        """
        self.message = message
        self.original_error = original_error
        self.error_code = error_code
        self.query = query
        self.params = params
        self.traceback = traceback.format_exc() if original_error else None
        
        # Construct detail message
        details = []
        if error_code:
            details.append(f"Error code: {error_code}")
        if original_error:
            details.append(f"Original error: {str(original_error)}")
        if query:
            # Truncate query if too long
            query_str = query if len(query) < 500 else query[:500] + "..."
            details.append(f"Query: {query_str}")
            
        detail_str = " | ".join(details) if details else ""
        super().__init__(f"{message}{' (' + detail_str + ')' if detail_str else ''}")


class ConnectionError(DatabaseError):
    """Exception raised for database connection errors."""
    pass


class QueryError(DatabaseError):
    """Exception raised for errors in SQL queries."""
    pass


class TransactionError(DatabaseError):
    """Exception raised for transaction-related errors."""
    pass


class PoolError(DatabaseError):
    """Exception raised for connection pool errors."""
    pass


class ValidationError(DatabaseError):
    """Exception raised for data validation errors."""
    pass


# Error mapping for driver-specific errors
ERROR_MAPPINGS = {
    "sqlite3": {
        "OperationalError": {
            "default": QueryError,
            "database is locked": TransactionError,
            "unable to open database file": ConnectionError,
            "no such table": QueryError,
        },
        "IntegrityError": ValidationError,
        "ProgrammingError": QueryError,
        "NotSupportedError": QueryError,
        "default": DatabaseError,
    },
    "pymysql": {
        "OperationalError": {
            "default": QueryError,
            "Can't connect": ConnectionError,
            "Lost connection": ConnectionError,
            "Too many connections": PoolError,
        },
        "IntegrityError": ValidationError,
        "ProgrammingError": QueryError,
        "NotSupportedError": QueryError,
        "default": DatabaseError,
    },
    "psycopg2": {
        "OperationalError": {
            "default": QueryError,
            "connection": ConnectionError,
            "terminating connection": ConnectionError,
            "server closed": ConnectionError,
        },
        "IntegrityError": ValidationError,
        "ProgrammingError": QueryError,
        "NotSupportedError": QueryError,
        "default": DatabaseError,
    },
    "default": {
        "default": DatabaseError,
    }
}


def handle_error(error: Exception, message: str, query: Optional[str] = None,
                params: Optional[Any] = None) -> DatabaseError:
    """
    Handle a database error and convert it to an appropriate DatabaseError subclass.
    
    Args:
        error: The original exception
        message: A message describing the error context
        query: The SQL query that caused the error (if applicable)
        params: The parameters that were used with the query
        
    Returns:
        A DatabaseError instance or subclass with detailed error information
        
    Example:
        try:
            cursor.execute(query, params)
        except Exception as e:
            raise handle_error(e, "Failed to execute query", query, params)
    """
    # Log the error
    logger.error(f"{message}: {error}", exc_info=True)
    
    # Get error info
    error_type = error.__class__.__name__
    error_message = str(error)
    error_module = error.__class__.__module__.split('.')[0] if error.__class__.__module__ else "unknown"
    
    # Determine the error class to use
    error_class = DatabaseError
    error_code = None
    
    # Map the error to an appropriate error class
    if error_module in ERROR_MAPPINGS:
        module_mappings = ERROR_MAPPINGS[error_module]
    else:
        module_mappings = ERROR_MAPPINGS["default"]
    
    if error_type in module_mappings:
        type_mapping = module_mappings[error_type]
        
        if isinstance(type_mapping, dict):
            # Check for specific error message patterns
            for pattern, cls in type_mapping.items():
                if pattern != "default" and pattern.lower() in error_message.lower():
                    error_class = cls
                    error_code = f"{error_module}.{error_type}.{pattern}"
                    break
            
            # Use default for this error type if no pattern matched
            if error_class is DatabaseError and "default" in type_mapping:
                error_class = type_mapping["default"]
                error_code = f"{error_module}.{error_type}"
        else:
            # Direct class mapping
            error_class = type_mapping
            error_code = f"{error_module}.{error_type}"
    elif "default" in module_mappings:
        error_class = module_mappings["default"]
        error_code = f"{error_module}.{error_type}"
    
    # Create and return the error instance
    return error_class(
        message=message,
        original_error=error,
        error_code=error_code,
        query=query,
        params=params
    )


def safe_execute(func, error_message: str, default_return: Any = None,
                log_level: str = "error") -> Any:
    """
    Execute a function safely, handling any exceptions.
    
    Args:
        func: The function to execute
        error_message: Message to log if an error occurs
        default_return: Value to return if an error occurs
        log_level: Logging level for errors ("error", "warning", "info", "debug")
        
    Returns:
        The function result or default_return if an error occurs
        
    Example:
        result = safe_execute(
            lambda: connection.execute(query, params),
            "Failed to execute query",
            default_return=None
        )
    """
    try:
        return func()
    except Exception as e:
        # Get the logger method based on log_level
        log_func = getattr(logger, log_level.lower(), logger.error)
        log_func(f"{error_message}: {str(e)}", exc_info=True)
        return default_return 