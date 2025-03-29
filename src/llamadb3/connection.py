"""
Database connection management module for LlamaDB3.

This module provides classes for managing database connections and connection pools.
"""

import time
import logging
import threading
import queue
from typing import Dict, Any, Optional, List, Callable, Union
from contextlib import contextmanager

from llamadb3.error_handler import handle_error, DatabaseError

logger = logging.getLogger(__name__)

class Connection:
    """A database connection that provides a consistent interface across various database backends."""
    
    def __init__(self, connection_params: Dict[str, Any]):
        """
        Initialize a database connection.
        
        Args:
            connection_params: Dictionary containing connection parameters.
                Must include 'driver' key specifying the database backend.
        
        Raises:
            DatabaseError: If connection fails or driver is not supported.
        """
        self.connection_params = connection_params
        self.driver = connection_params.get('driver', 'sqlite')
        self.conn = None
        self.is_connected = False
        self.last_used = time.time()
        self._connect()
    
    def _connect(self) -> None:
        """
        Establish the database connection based on the specified driver.
        
        Raises:
            DatabaseError: If connection fails or driver is not supported.
        """
        try:
            if self.driver == 'sqlite':
                import sqlite3
                self.conn = sqlite3.connect(
                    self.connection_params.get('database', ':memory:'),
                    isolation_level=self.connection_params.get('isolation_level', None),
                    timeout=self.connection_params.get('timeout', 5.0)
                )
            elif self.driver == 'mysql':
                import pymysql
                self.conn = pymysql.connect(
                    host=self.connection_params.get('host', 'localhost'),
                    user=self.connection_params.get('user', 'root'),
                    password=self.connection_params.get('password', ''),
                    database=self.connection_params.get('database', ''),
                    port=self.connection_params.get('port', 3306),
                    charset=self.connection_params.get('charset', 'utf8mb4')
                )
            elif self.driver == 'postgresql':
                import psycopg2
                self.conn = psycopg2.connect(
                    host=self.connection_params.get('host', 'localhost'),
                    user=self.connection_params.get('user', 'postgres'),
                    password=self.connection_params.get('password', ''),
                    dbname=self.connection_params.get('database', ''),
                    port=self.connection_params.get('port', 5432)
                )
            else:
                raise DatabaseError(f"Unsupported database driver: {self.driver}")
            
            self.is_connected = True
            self.last_used = time.time()
            logger.info(f"Connected to {self.driver} database")
        except ImportError as e:
            raise DatabaseError(f"Driver module not installed for {self.driver}: {str(e)}")
        except Exception as e:
            raise handle_error(e, f"Failed to connect to {self.driver} database")
    
    def reconnect(self) -> None:
        """
        Reconnect to the database if the connection is closed.
        
        Raises:
            DatabaseError: If reconnection fails.
        """
        if not self.is_connected:
            self._connect()
    
    def close(self) -> None:
        """Close the database connection."""
        if self.is_connected and self.conn:
            try:
                self.conn.close()
                self.is_connected = False
                logger.debug("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {str(e)}")
    
    def execute(self, query: str, params: Any = None) -> Any:
        """
        Execute a SQL query with the given parameters.
        
        Args:
            query: SQL query string
            params: Query parameters (dict, tuple, or list)
            
        Returns:
            Cursor object or equivalent for the database driver
            
        Raises:
            DatabaseError: If query execution fails
        """
        self.last_used = time.time()
        if not self.is_connected:
            self.reconnect()
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params or ())
            return cursor
        except Exception as e:
            raise handle_error(e, f"Query execution failed: {query}")
    
    def execute_many(self, query: str, params_list: List[Any]) -> Any:
        """
        Execute a SQL query multiple times with different parameters.
        
        Args:
            query: SQL query string
            params_list: List of parameter sets
            
        Returns:
            Cursor object or equivalent for the database driver
            
        Raises:
            DatabaseError: If query execution fails
        """
        self.last_used = time.time()
        if not self.is_connected:
            self.reconnect()
            
        try:
            cursor = self.conn.cursor()
            cursor.executemany(query, params_list)
            return cursor
        except Exception as e:
            raise handle_error(e, f"Batch query execution failed: {query}")
    
    def commit(self) -> None:
        """
        Commit the current transaction.
        
        Raises:
            DatabaseError: If commit fails
        """
        if self.is_connected:
            try:
                self.conn.commit()
            except Exception as e:
                raise handle_error(e, "Transaction commit failed")
    
    def rollback(self) -> None:
        """
        Rollback the current transaction.
        
        Raises:
            DatabaseError: If rollback fails
        """
        if self.is_connected:
            try:
                self.conn.rollback()
            except Exception as e:
                raise handle_error(e, "Transaction rollback failed")
                
    @contextmanager
    def transaction(self):
        """
        Context manager for handling transactions.
        
        Yields:
            The connection object
            
        Raises:
            DatabaseError: If transaction operations fail
        """
        try:
            yield self
            self.commit()
        except Exception as e:
            self.rollback()
            raise handle_error(e, "Transaction failed")


class ConnectionPool:
    """
    A pool of database connections that can be reused.
    
    This reduces the overhead of creating new connections for each operation.
    """
    
    def __init__(self, 
                 connection_params: Dict[str, Any], 
                 min_connections: int = 1,
                 max_connections: int = 10,
                 timeout: float = 30.0,
                 idle_timeout: float = 300.0):
        """
        Initialize a connection pool.
        
        Args:
            connection_params: Dictionary containing connection parameters
            min_connections: Minimum number of connections to keep open
            max_connections: Maximum number of connections allowed
            timeout: Timeout in seconds when waiting for an available connection
            idle_timeout: Time in seconds after which idle connections are closed
            
        Raises:
            DatabaseError: If initial connections cannot be established
        """
        self.connection_params = connection_params
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.timeout = timeout
        self.idle_timeout = idle_timeout
        
        self.pool = queue.Queue(maxsize=max_connections)
        self.active_connections = 0
        self.lock = threading.RLock()
        self._maintenance_timer = None
        
        # Initialize minimum connections
        self._initialize_pool()
        self._start_maintenance_timer()
    
    def _initialize_pool(self) -> None:
        """
        Initialize the connection pool with minimum connections.
        
        Raises:
            DatabaseError: If connections cannot be established
        """
        for _ in range(self.min_connections):
            try:
                conn = Connection(self.connection_params)
                self.pool.put(conn)
                self.active_connections += 1
            except Exception as e:
                raise handle_error(e, "Failed to initialize connection pool")
    
    def _start_maintenance_timer(self) -> None:
        """Start timer for periodic pool maintenance."""
        self._maintenance_timer = threading.Timer(60.0, self._maintenance)
        self._maintenance_timer.daemon = True
        self._maintenance_timer.start()
    
    def _maintenance(self) -> None:
        """
        Perform pool maintenance - remove stale connections and ensure min_connections.
        """
        try:
            with self.lock:
                # Count connections and collect stale ones
                current_time = time.time()
                temp_queue = queue.Queue()
                stale_connections = []
                active_count = 0
                
                # Check each connection
                while not self.pool.empty():
                    conn = self.pool.get(block=False)
                    if current_time - conn.last_used > self.idle_timeout and active_count > self.min_connections:
                        stale_connections.append(conn)
                    else:
                        temp_queue.put(conn)
                        active_count += 1
                
                # Restore good connections
                while not temp_queue.empty():
                    self.pool.put(temp_queue.get(block=False))
                
                # Close stale connections
                for conn in stale_connections:
                    conn.close()
                    self.active_connections -= 1
                
                # Ensure minimum connections
                while active_count < self.min_connections:
                    try:
                        conn = Connection(self.connection_params)
                        self.pool.put(conn)
                        self.active_connections += 1
                        active_count += 1
                    except Exception as e:
                        logger.error(f"Failed to add connection during maintenance: {str(e)}")
                        break
        
        except Exception as e:
            logger.error(f"Error during pool maintenance: {str(e)}")
        
        finally:
            # Reschedule maintenance
            self._start_maintenance_timer()
    
    def get_connection(self) -> Connection:
        """
        Get a connection from the pool or create a new one if needed.
        
        Returns:
            A database connection
            
        Raises:
            DatabaseError: If a connection cannot be obtained
        """
        try:
            # Try to get an existing connection from the pool
            conn = self.pool.get(block=True, timeout=self.timeout)
            
            # Test if connection is still valid
            if not conn.is_connected:
                try:
                    conn.reconnect()
                except Exception:
                    # If reconnection fails, create a new connection
                    conn = Connection(self.connection_params)
            
            return conn
        
        except queue.Empty:
            # If pool is empty, create a new connection if below max_connections
            with self.lock:
                if self.active_connections < self.max_connections:
                    conn = Connection(self.connection_params)
                    self.active_connections += 1
                    return conn
                else:
                    raise DatabaseError("Connection pool exhausted, max_connections reached")
        
        except Exception as e:
            raise handle_error(e, "Failed to get database connection from pool")
    
    def return_connection(self, conn: Connection) -> None:
        """
        Return a connection to the pool.
        
        Args:
            conn: The connection to return
        """
        if conn and conn.is_connected:
            try:
                self.pool.put(conn, block=False)
            except queue.Full:
                # If pool is full, close this connection
                conn.close()
                with self.lock:
                    self.active_connections -= 1
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        with self.lock:
            while not self.pool.empty():
                try:
                    conn = self.pool.get(block=False)
                    conn.close()
                    self.active_connections -= 1
                except (queue.Empty, Exception) as e:
                    logger.warning(f"Error closing connection: {str(e)}")
            
            if self._maintenance_timer:
                self._maintenance_timer.cancel()
    
    @contextmanager
    def connection(self) -> Connection:
        """
        Context manager for handling connections from the pool.
        
        Yields:
            A database connection
            
        Raises:
            DatabaseError: If a connection cannot be obtained
        """
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        finally:
            if conn:
                self.return_connection(conn)
    
    @contextmanager
    def transaction(self):
        """
        Context manager for handling transactions with pooled connections.
        
        Yields:
            A database connection
            
        Raises:
            DatabaseError: If transaction operations fail
        """
        conn = None
        try:
            conn = self.get_connection()
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise handle_error(e, "Transaction failed")
        finally:
            if conn:
                self.return_connection(conn) 