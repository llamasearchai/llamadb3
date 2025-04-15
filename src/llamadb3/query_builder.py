"""
Query Builder module for LlamaDB3.

This module provides a fluent interface for building SQL queries in a
database-agnostic way, with support for various SQL dialects.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from llamadb3.error_handler import ValidationError, handle_error

logger = logging.getLogger(__name__)


class SQLDialect(Enum):
    """Enum representing SQL dialect variants."""

    SQLITE = "sqlite"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"


class JoinType(Enum):
    """Enum representing SQL join types."""

    INNER = "INNER JOIN"
    LEFT = "LEFT JOIN"
    RIGHT = "RIGHT JOIN"
    FULL = "FULL JOIN"
    CROSS = "CROSS JOIN"


class OrderDirection(Enum):
    """Enum representing SQL order directions."""

    ASC = "ASC"
    DESC = "DESC"


class QueryBuilder:
    """
    A fluent query builder for constructing SQL queries in a database-agnostic way.

    This class provides a chainable interface for building SELECT, INSERT, UPDATE,
    and DELETE queries, with support for WHERE clauses, JOINs, ORDER BY, GROUP BY, and more.
    """

    def __init__(self, dialect: Union[str, SQLDialect] = SQLDialect.SQLITE):
        """
        Initialize a query builder.

        Args:
            dialect: The SQL dialect to use, either as a string or SQLDialect enum
        """
        # Set the SQL dialect
        if isinstance(dialect, str):
            self.dialect = SQLDialect(dialect.lower())
        else:
            self.dialect = dialect

        # Query components
        self.query_type = None
        self.table = None
        self.columns = []
        self.values = []
        self.joins = []
        self.where_conditions = []
        self.where_params = []
        self.group_by_columns = []
        self.having_conditions = []
        self.having_params = []
        self.order_by_columns = []
        self.limit_value = None
        self.offset_value = None
        self.returning_columns = []
        self.update_values = {}

        # Query flags
        self.distinct_flag = False

        # Parameter counter for PostgreSQL style parameters
        self._param_count = 0

    def _get_param_placeholder(self) -> str:
        """
        Get a parameter placeholder based on the current dialect.

        Returns:
            A parameter placeholder string
        """
        if self.dialect == SQLDialect.POSTGRESQL:
            self._param_count += 1
            return f"${self._param_count}"
        else:
            return "?"

    def _format_identifier(self, identifier: str) -> str:
        """
        Format an identifier (table or column name) according to the dialect.

        Args:
            identifier: The identifier to format

        Returns:
            The formatted identifier
        """
        # Handle table.column format
        if "." in identifier:
            parts = identifier.split(".")
            return ".".join([self._format_identifier(part) for part in parts])

        # Format based on dialect
        if self.dialect == SQLDialect.SQLITE:
            return f'"{identifier}"'
        elif self.dialect == SQLDialect.MYSQL:
            return f"`{identifier}`"
        elif self.dialect == SQLDialect.POSTGRESQL:
            return f'"{identifier}"'
        else:
            return identifier

    def _reset(self) -> None:
        """Reset all query components."""
        self.query_type = None
        self.table = None
        self.columns = []
        self.values = []
        self.joins = []
        self.where_conditions = []
        self.where_params = []
        self.group_by_columns = []
        self.having_conditions = []
        self.having_params = []
        self.order_by_columns = []
        self.limit_value = None
        self.offset_value = None
        self.returning_columns = []
        self.update_values = {}
        self.distinct_flag = False
        self._param_count = 0

    def select(self, *columns) -> "QueryBuilder":
        """
        Begin a SELECT query.

        Args:
            columns: The columns to select, use ["*"] for all columns

        Returns:
            The query builder instance for chaining
        """
        self._reset()
        self.query_type = "SELECT"
        if columns:
            self.columns = list(columns)
        else:
            self.columns = ["*"]
        return self

    def distinct(self) -> "QueryBuilder":
        """
        Add a DISTINCT qualifier to a SELECT query.

        Returns:
            The query builder instance for chaining
        """
        self.distinct_flag = True
        return self

    def from_table(self, table: str) -> "QueryBuilder":
        """
        Specify the table for a query.

        Args:
            table: The table name

        Returns:
            The query builder instance for chaining
        """
        self.table = table
        return self

    def join(
        self, table: str, condition: str, join_type: JoinType = JoinType.INNER
    ) -> "QueryBuilder":
        """
        Add a JOIN clause to the query.

        Args:
            table: The table to join
            condition: The join condition
            join_type: The type of join (INNER, LEFT, RIGHT, FULL, CROSS)

        Returns:
            The query builder instance for chaining
        """
        self.joins.append({"table": table, "condition": condition, "type": join_type})
        return self

    def left_join(self, table: str, condition: str) -> "QueryBuilder":
        """
        Add a LEFT JOIN clause to the query.

        Args:
            table: The table to join
            condition: The join condition

        Returns:
            The query builder instance for chaining
        """
        return self.join(table, condition, JoinType.LEFT)

    def right_join(self, table: str, condition: str) -> "QueryBuilder":
        """
        Add a RIGHT JOIN clause to the query.

        Args:
            table: The table to join
            condition: The join condition

        Returns:
            The query builder instance for chaining
        """
        return self.join(table, condition, JoinType.RIGHT)

    def inner_join(self, table: str, condition: str) -> "QueryBuilder":
        """
        Add an INNER JOIN clause to the query.

        Args:
            table: The table to join
            condition: The join condition

        Returns:
            The query builder instance for chaining
        """
        return self.join(table, condition, JoinType.INNER)

    def where(self, condition: str, *params) -> "QueryBuilder":
        """
        Add a WHERE condition to the query.

        Args:
            condition: The condition string with placeholders
            params: Parameter values for the condition

        Returns:
            The query builder instance for chaining
        """
        self.where_conditions.append(condition)
        self.where_params.extend(params)
        return self

    def where_in(self, column: str, values: List[Any]) -> "QueryBuilder":
        """
        Add a WHERE IN condition to the query.

        Args:
            column: The column name
            values: List of values to match against

        Returns:
            The query builder instance for chaining
        """
        if not values:
            # If no values provided, add a condition that will always be false
            return self.where("1 = 0")

        placeholders = ", ".join([self._get_param_placeholder() for _ in values])
        condition = f"{self._format_identifier(column)} IN ({placeholders})"
        self.where_conditions.append(condition)
        self.where_params.extend(values)
        return self

    def where_not_in(self, column: str, values: List[Any]) -> "QueryBuilder":
        """
        Add a WHERE NOT IN condition to the query.

        Args:
            column: The column name
            values: List of values to exclude

        Returns:
            The query builder instance for chaining
        """
        if not values:
            # If no values provided, add a condition that will always be true
            return self.where("1 = 1")

        placeholders = ", ".join([self._get_param_placeholder() for _ in values])
        condition = f"{self._format_identifier(column)} NOT IN ({placeholders})"
        self.where_conditions.append(condition)
        self.where_params.extend(values)
        return self

    def where_between(self, column: str, start: Any, end: Any) -> "QueryBuilder":
        """
        Add a WHERE BETWEEN condition to the query.

        Args:
            column: The column name
            start: The start value
            end: The end value

        Returns:
            The query builder instance for chaining
        """
        condition = f"{self._format_identifier(column)} BETWEEN {self._get_param_placeholder()} AND {self._get_param_placeholder()}"
        self.where_conditions.append(condition)
        self.where_params.extend([start, end])
        return self

    def where_null(self, column: str) -> "QueryBuilder":
        """
        Add a WHERE IS NULL condition to the query.

        Args:
            column: The column name

        Returns:
            The query builder instance for chaining
        """
        condition = f"{self._format_identifier(column)} IS NULL"
        self.where_conditions.append(condition)
        return self

    def where_not_null(self, column: str) -> "QueryBuilder":
        """
        Add a WHERE IS NOT NULL condition to the query.

        Args:
            column: The column name

        Returns:
            The query builder instance for chaining
        """
        condition = f"{self._format_identifier(column)} IS NOT NULL"
        self.where_conditions.append(condition)
        return self

    def group_by(self, *columns) -> "QueryBuilder":
        """
        Add a GROUP BY clause to the query.

        Args:
            columns: Column names to group by

        Returns:
            The query builder instance for chaining
        """
        self.group_by_columns.extend(columns)
        return self

    def having(self, condition: str, *params) -> "QueryBuilder":
        """
        Add a HAVING condition to the query.

        Args:
            condition: The condition string with placeholders
            params: Parameter values for the condition

        Returns:
            The query builder instance for chaining
        """
        self.having_conditions.append(condition)
        self.having_params.extend(params)
        return self

    def order_by(
        self, column: str, direction: OrderDirection = OrderDirection.ASC
    ) -> "QueryBuilder":
        """
        Add an ORDER BY clause to the query.

        Args:
            column: The column to order by
            direction: The sort direction (ASC or DESC)

        Returns:
            The query builder instance for chaining
        """
        self.order_by_columns.append({"column": column, "direction": direction})
        return self

    def order_by_desc(self, column: str) -> "QueryBuilder":
        """
        Add an ORDER BY DESC clause to the query.

        Args:
            column: The column to order by descending

        Returns:
            The query builder instance for chaining
        """
        return self.order_by(column, OrderDirection.DESC)

    def limit(self, limit: int) -> "QueryBuilder":
        """
        Add a LIMIT clause to the query.

        Args:
            limit: Maximum number of rows to return

        Returns:
            The query builder instance for chaining
        """
        if not isinstance(limit, int) or limit < 0:
            raise ValidationError(f"Limit must be a non-negative integer, got {limit}")
        self.limit_value = limit
        return self

    def offset(self, offset: int) -> "QueryBuilder":
        """
        Add an OFFSET clause to the query.

        Args:
            offset: Number of rows to skip

        Returns:
            The query builder instance for chaining
        """
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError(
                f"Offset must be a non-negative integer, got {offset}"
            )
        self.offset_value = offset
        return self

    def insert(self, table: str) -> "QueryBuilder":
        """
        Begin an INSERT query.

        Args:
            table: The table to insert into

        Returns:
            The query builder instance for chaining
        """
        self._reset()
        self.query_type = "INSERT"
        self.table = table
        return self

    def columns(self, *columns) -> "QueryBuilder":
        """
        Specify columns for an INSERT query.

        Args:
            columns: Column names to insert into

        Returns:
            The query builder instance for chaining
        """
        self.columns = list(columns)
        return self

    def values(self, *rows) -> "QueryBuilder":
        """
        Add values for an INSERT query.

        Args:
            rows: One or more rows of values to insert

        Returns:
            The query builder instance for chaining
        """
        for row in rows:
            if self.columns and len(row) != len(self.columns):
                raise ValidationError(
                    f"Value count ({len(row)}) does not match column count ({len(self.columns)})"
                )
            self.values.append(row)
        return self

    def update(self, table: str) -> "QueryBuilder":
        """
        Begin an UPDATE query.

        Args:
            table: The table to update

        Returns:
            The query builder instance for chaining
        """
        self._reset()
        self.query_type = "UPDATE"
        self.table = table
        return self

    def set(self, column: str, value: Any) -> "QueryBuilder":
        """
        Add a column-value pair to set in an UPDATE query.

        Args:
            column: The column name
            value: The value to set

        Returns:
            The query builder instance for chaining
        """
        self.update_values[column] = value
        return self

    def set_all(self, values: Dict[str, Any]) -> "QueryBuilder":
        """
        Set multiple column-value pairs in an UPDATE query.

        Args:
            values: Dictionary of column-value pairs

        Returns:
            The query builder instance for chaining
        """
        self.update_values.update(values)
        return self

    def delete(self) -> "QueryBuilder":
        """
        Begin a DELETE query.

        Returns:
            The query builder instance for chaining
        """
        self._reset()
        self.query_type = "DELETE"
        return self

    def returning(self, *columns) -> "QueryBuilder":
        """
        Add a RETURNING clause to an INSERT, UPDATE, or DELETE query.
        Supported only in PostgreSQL.

        Args:
            columns: Column names to return

        Returns:
            The query builder instance for chaining

        Raises:
            ValidationError: If the dialect does not support RETURNING
        """
        if self.dialect != SQLDialect.POSTGRESQL:
            raise ValidationError(
                f"RETURNING clause is only supported in PostgreSQL, not {self.dialect.value}"
            )

        self.returning_columns = list(columns) if columns else ["*"]
        return self

    def build(self) -> Tuple[str, List[Any]]:
        """
        Build the SQL query string and parameters.

        Returns:
            A tuple of (query_string, parameter_list)

        Raises:
            ValidationError: If the query is invalid or incomplete
        """
        if not self.query_type:
            raise ValidationError("Query type not specified")

        if not self.table and self.query_type != "DELETE":
            raise ValidationError("Table not specified")

        query_parts = []
        params = []

        # Build the appropriate query based on type
        if self.query_type == "SELECT":
            # SELECT clause
            select_clause = "SELECT"
            if self.distinct_flag:
                select_clause += " DISTINCT"

            if not self.columns:
                column_str = "*"
            else:
                column_str = ", ".join(
                    self._format_identifier(col) if isinstance(col, str) else col
                    for col in self.columns
                )

            query_parts.append(f"{select_clause} {column_str}")

            # FROM clause
            query_parts.append(f"FROM {self._format_identifier(self.table)}")

            # JOIN clauses
            for join in self.joins:
                query_parts.append(
                    f"{join['type'].value} {self._format_identifier(join['table'])} ON {join['condition']}"
                )

        elif self.query_type == "INSERT":
            # INSERT INTO clause
            query_parts.append(f"INSERT INTO {self._format_identifier(self.table)}")

            # Columns clause
            if self.columns:
                column_str = ", ".join(
                    self._format_identifier(col) for col in self.columns
                )
                query_parts.append(f"({column_str})")

            # VALUES clause
            if self.values:
                values_parts = []
                for row in self.values:
                    placeholders = ", ".join(self._get_param_placeholder() for _ in row)
                    values_parts.append(f"({placeholders})")
                    params.extend(row)

                query_parts.append(f"VALUES {', '.join(values_parts)}")

        elif self.query_type == "UPDATE":
            # UPDATE clause
            query_parts.append(f"UPDATE {self._format_identifier(self.table)}")

            # SET clause
            if not self.update_values:
                raise ValidationError("No values specified for UPDATE query")

            set_parts = []
            for column, value in self.update_values.items():
                set_parts.append(
                    f"{self._format_identifier(column)} = {self._get_param_placeholder()}"
                )
                params.append(value)

            query_parts.append(f"SET {', '.join(set_parts)}")

        elif self.query_type == "DELETE":
            # DELETE FROM clause
            if not self.table:
                raise ValidationError("Table not specified for DELETE query")

            query_parts.append(f"DELETE FROM {self._format_identifier(self.table)}")

        # WHERE clause (applies to SELECT, UPDATE, DELETE)
        if self.where_conditions:
            where_clause = " AND ".join(
                f"({condition})" for condition in self.where_conditions
            )
            query_parts.append(f"WHERE {where_clause}")
            params.extend(self.where_params)

        # GROUP BY clause (applies to SELECT)
        if self.group_by_columns and self.query_type == "SELECT":
            group_by_str = ", ".join(
                self._format_identifier(col) for col in self.group_by_columns
            )
            query_parts.append(f"GROUP BY {group_by_str}")

        # HAVING clause (applies to SELECT with GROUP BY)
        if (
            self.having_conditions
            and self.group_by_columns
            and self.query_type == "SELECT"
        ):
            having_clause = " AND ".join(
                f"({condition})" for condition in self.having_conditions
            )
            query_parts.append(f"HAVING {having_clause}")
            params.extend(self.having_params)

        # ORDER BY clause (applies to SELECT)
        if self.order_by_columns and self.query_type == "SELECT":
            order_by_parts = []
            for order in self.order_by_columns:
                order_by_parts.append(
                    f"{self._format_identifier(order['column'])} {order['direction'].value}"
                )
            query_parts.append(f"ORDER BY {', '.join(order_by_parts)}")

        # LIMIT and OFFSET clauses (applies to SELECT)
        if self.query_type == "SELECT":
            if self.limit_value is not None:
                query_parts.append(f"LIMIT {self.limit_value}")

            if self.offset_value is not None:
                query_parts.append(f"OFFSET {self.offset_value}")

        # RETURNING clause (applies to INSERT, UPDATE, DELETE in PostgreSQL)
        if self.returning_columns and self.dialect == SQLDialect.POSTGRESQL:
            returning_str = ", ".join(
                self._format_identifier(col) if isinstance(col, str) else col
                for col in self.returning_columns
            )
            query_parts.append(f"RETURNING {returning_str}")

        # Build the final query
        query = " ".join(query_parts)
        return query, params

    def get_sql(self) -> str:
        """
        Get the SQL query string with parameter placeholders.

        Returns:
            The SQL query string
        """
        query, _ = self.build()
        return query

    def get_params(self) -> List[Any]:
        """
        Get the parameters for the SQL query.

        Returns:
            The list of parameters
        """
        _, params = self.build()
        return params

    def __str__(self) -> str:
        """
        Get a string representation of the query.

        Returns:
            The SQL query string
        """
        try:
            return self.get_sql()
        except Exception as e:
            return f"Invalid query: {str(e)}"
