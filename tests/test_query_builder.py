"""
Tests for the query builder module.
"""

import unittest

from llamadb3.error_handler import ValidationError
from llamadb3.query_builder import JoinType, OrderDirection, QueryBuilder, SQLDialect


class TestQueryBuilder(unittest.TestCase):
    """Test cases for the QueryBuilder class."""

    def test_select_all(self):
        """Test a basic SELECT * query."""
        query = QueryBuilder().select().from_table("users")
        sql, params = query.build()

        self.assertEqual(sql, 'SELECT * FROM "users"')
        self.assertEqual(params, [])

    def test_select_columns(self):
        """Test SELECT with specific columns."""
        query = QueryBuilder().select("id", "name", "email").from_table("users")
        sql, params = query.build()

        self.assertEqual(sql, 'SELECT "id", "name", "email" FROM "users"')
        self.assertEqual(params, [])

    def test_select_where(self):
        """Test SELECT with WHERE clause."""
        query = (
            QueryBuilder().select("id", "name").from_table("users").where("age > ?", 30)
        )
        sql, params = query.build()

        self.assertEqual(sql, 'SELECT "id", "name" FROM "users" WHERE (age > ?)')
        self.assertEqual(params, [30])

    def test_select_where_multiple(self):
        """Test SELECT with multiple WHERE conditions."""
        query = (
            QueryBuilder()
            .select("id", "name")
            .from_table("users")
            .where("age > ?", 30)
            .where("status = ?", "active")
        )
        sql, params = query.build()

        self.assertEqual(
            sql, 'SELECT "id", "name" FROM "users" WHERE (age > ?) AND (status = ?)'
        )
        self.assertEqual(params, [30, "active"])

    def test_where_in(self):
        """Test WHERE IN condition."""
        query = (
            QueryBuilder()
            .select("id", "name")
            .from_table("users")
            .where_in("id", [1, 2, 3])
        )
        sql, params = query.build()

        self.assertEqual(
            sql, 'SELECT "id", "name" FROM "users" WHERE ("id" IN (?, ?, ?))'
        )
        self.assertEqual(params, [1, 2, 3])

    def test_where_in_empty(self):
        """Test WHERE IN with empty values list."""
        query = (
            QueryBuilder().select("id", "name").from_table("users").where_in("id", [])
        )
        sql, params = query.build()

        self.assertEqual(sql, 'SELECT "id", "name" FROM "users" WHERE (1 = 0)')
        self.assertEqual(params, [])

    def test_join(self):
        """Test JOIN clause."""
        query = (
            QueryBuilder()
            .select("u.id", "u.name", "o.amount")
            .from_table("users u")
            .join("orders o", "o.user_id = u.id")
        )
        sql, params = query.build()

        self.assertEqual(
            sql,
            'SELECT "u"."id", "u"."name", "o"."amount" FROM "users u" INNER JOIN "orders o" ON o.user_id = u.id',
        )
        self.assertEqual(params, [])

    def test_left_join(self):
        """Test LEFT JOIN clause."""
        query = (
            QueryBuilder()
            .select("u.id", "u.name", "o.amount")
            .from_table("users u")
            .left_join("orders o", "o.user_id = u.id")
        )
        sql, params = query.build()

        self.assertEqual(
            sql,
            'SELECT "u"."id", "u"."name", "o"."amount" FROM "users u" LEFT JOIN "orders o" ON o.user_id = u.id',
        )
        self.assertEqual(params, [])

    def test_group_by(self):
        """Test GROUP BY clause."""
        query = (
            QueryBuilder()
            .select("user_id", "COUNT(*) as count")
            .from_table("orders")
            .group_by("user_id")
        )
        sql, params = query.build()

        self.assertEqual(
            sql, 'SELECT "user_id", COUNT(*) as count FROM "orders" GROUP BY "user_id"'
        )
        self.assertEqual(params, [])

    def test_order_by(self):
        """Test ORDER BY clause."""
        query = QueryBuilder().select("id", "name").from_table("users").order_by("name")
        sql, params = query.build()

        self.assertEqual(sql, 'SELECT "id", "name" FROM "users" ORDER BY "name" ASC')
        self.assertEqual(params, [])

    def test_order_by_desc(self):
        """Test ORDER BY DESC clause."""
        query = (
            QueryBuilder()
            .select("id", "name")
            .from_table("users")
            .order_by_desc("name")
        )
        sql, params = query.build()

        self.assertEqual(sql, 'SELECT "id", "name" FROM "users" ORDER BY "name" DESC')
        self.assertEqual(params, [])

    def test_limit_offset(self):
        """Test LIMIT and OFFSET clauses."""
        query = (
            QueryBuilder()
            .select("id", "name")
            .from_table("users")
            .order_by("id")
            .limit(10)
            .offset(5)
        )
        sql, params = query.build()

        self.assertEqual(
            sql, 'SELECT "id", "name" FROM "users" ORDER BY "id" ASC LIMIT 10 OFFSET 5'
        )
        self.assertEqual(params, [])

    def test_insert(self):
        """Test INSERT query."""
        query = (
            QueryBuilder()
            .insert("users")
            .columns("name", "email", "age")
            .values(("John Doe", "john@example.com", 30))
        )
        sql, params = query.build()

        self.assertEqual(
            sql, 'INSERT INTO "users" ("name", "email", "age") VALUES (?, ?, ?)'
        )
        self.assertEqual(params, ["John Doe", "john@example.com", 30])

    def test_insert_multiple(self):
        """Test INSERT with multiple rows."""
        query = (
            QueryBuilder()
            .insert("users")
            .columns("name", "email")
            .values(
                ("John Doe", "john@example.com"), ("Jane Smith", "jane@example.com")
            )
        )
        sql, params = query.build()

        self.assertEqual(
            sql, 'INSERT INTO "users" ("name", "email") VALUES (?, ?), (?, ?)'
        )
        self.assertEqual(
            params, ["John Doe", "john@example.com", "Jane Smith", "jane@example.com"]
        )

    def test_update(self):
        """Test UPDATE query."""
        query = (
            QueryBuilder()
            .update("users")
            .set("name", "John Smith")
            .set("updated_at", "2023-06-01")
            .where("id = ?", 1)
        )
        sql, params = query.build()

        self.assertEqual(
            sql, 'UPDATE "users" SET "name" = ?, "updated_at" = ? WHERE (id = ?)'
        )
        self.assertEqual(params, ["John Smith", "2023-06-01", 1])

    def test_update_set_all(self):
        """Test UPDATE with set_all method."""
        query = (
            QueryBuilder()
            .update("users")
            .set_all(
                {
                    "name": "John Smith",
                    "email": "john.smith@example.com",
                    "updated_at": "2023-06-01",
                }
            )
            .where("id = ?", 1)
        )
        sql, params = query.build()

        # We need to check parts separately because the order of dictionary items can vary
        self.assertTrue(sql.startswith('UPDATE "users" SET '))
        self.assertTrue('"name" = ?' in sql)
        self.assertTrue('"email" = ?' in sql)
        self.assertTrue('"updated_at" = ?' in sql)
        self.assertTrue(sql.endswith(" WHERE (id = ?)"))

        # Check that all parameters are present
        self.assertEqual(len(params), 4)
        self.assertIn("John Smith", params)
        self.assertIn("john.smith@example.com", params)
        self.assertIn("2023-06-01", params)
        self.assertEqual(params[-1], 1)  # The WHERE parameter should be last

    def test_delete(self):
        """Test DELETE query."""
        query = QueryBuilder().delete().from_table("users").where("id = ?", 1)
        sql, params = query.build()

        self.assertEqual(sql, 'DELETE FROM "users" WHERE (id = ?)')
        self.assertEqual(params, [1])

    def test_mysql_dialect(self):
        """Test MySQL dialect for identifier quoting."""
        query = (
            QueryBuilder(dialect=SQLDialect.MYSQL)
            .select("id", "name")
            .from_table("users")
        )
        sql, params = query.build()

        self.assertEqual(sql, "SELECT `id`, `name` FROM `users`")
        self.assertEqual(params, [])

    def test_postgresql_dialect(self):
        """Test PostgreSQL dialect for parameters and RETURNING clause."""
        query = (
            QueryBuilder(dialect=SQLDialect.POSTGRESQL)
            .insert("users")
            .columns("name", "email")
            .values(("John Doe", "john@example.com"))
            .returning("id", "name")
        )
        sql, params = query.build()

        self.assertEqual(
            sql,
            'INSERT INTO "users" ("name", "email") VALUES ($1, $2) RETURNING "id", "name"',
        )
        self.assertEqual(params, ["John Doe", "john@example.com"])

    def test_validation_errors(self):
        """Test validation errors for invalid queries."""
        # Test missing table
        with self.assertRaises(ValidationError):
            QueryBuilder().select().build()

        # Test missing query type
        with self.assertRaises(ValidationError):
            QueryBuilder().from_table("users").build()

        # Test negative limit
        with self.assertRaises(ValidationError):
            QueryBuilder().select().from_table("users").limit(-1).build()

        # Test RETURNING with non-PostgreSQL dialect
        with self.assertRaises(ValidationError):
            QueryBuilder(dialect=SQLDialect.SQLITE).insert("users").returning(
                "id"
            ).build()

        # Test INSERT with mismatched column and value counts
        with self.assertRaises(ValidationError):
            QueryBuilder().insert("users").columns("name", "email").values(
                ("John",)
            ).build()


if __name__ == "__main__":
    unittest.main()
