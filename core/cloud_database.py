import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class CloudDatabaseManager:
    """PostgreSQL database manager for persisting research runs.
    
    Uses psycopg2 connection pooling for production-grade connection management.
    Designed to work with Supabase-provided PostgreSQL instances.
    """

    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError(
                "DATABASE_URL environment variable not set. "
                "Please provide a PostgreSQL connection string."
            )

        self.connection_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=self.database_url,
        )
        logger.info("Database connection pool initialized.")
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Create the research_runs table and ensure all columns exist."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS research_runs (
            id SERIAL PRIMARY KEY,
            query TEXT NOT NULL,
            plan_json JSONB,
            report_json JSONB,
            confidence_score FLOAT,
            iterations INT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """

        # New columns added via ALTER TABLE for forward-compatible migration.
        # These use IF NOT EXISTS patterns so re-running is safe.
        alter_columns = [
            "ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS run_mode VARCHAR(20) DEFAULT 'stateless'",
            "ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS total_subtopics_encountered INT",
            "ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS total_subtopics_added INT",
            "ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS total_subtopics_removed INT",
            "ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS max_active_subtopics INT",
            "ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS structural_complexity_score FLOAT",
            "ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS plan_expansion_ratio FLOAT",
            "ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS prune_ratio FLOAT",
            "ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS convergence_rate FLOAT",
            "ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS structural_volatility_score FLOAT",
        ]

        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(create_table_sql)
                for stmt in alter_columns:
                    cur.execute(stmt)
            conn.commit()
            logger.info("Database schema initialized successfully.")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to initialize schema: {e}")
            raise
        finally:
            self.connection_pool.putconn(conn)

    def save_run(
        self,
        query: str,
        plan_data: Dict[str, Any],
        report_data: Dict[str, Any],
        confidence_score: float,
        iterations: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Save a completed research run with structural metadata and return its ID."""
        meta = metadata or {}

        insert_sql = """
        INSERT INTO research_runs (
            query, plan_json, report_json, confidence_score, iterations,
            run_mode,
            total_subtopics_encountered, total_subtopics_added,
            total_subtopics_removed, max_active_subtopics,
            structural_complexity_score,
            plan_expansion_ratio, prune_ratio,
            convergence_rate, structural_volatility_score
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    insert_sql,
                    (
                        query,
                        json.dumps(plan_data),
                        json.dumps(report_data),
                        confidence_score,
                        iterations,
                        meta.get("run_mode", "stateless"),
                        meta.get("total_subtopics_encountered"),
                        meta.get("total_subtopics_added"),
                        meta.get("total_subtopics_removed"),
                        meta.get("max_active_subtopics"),
                        meta.get("structural_complexity_score"),
                        meta.get("plan_expansion_ratio"),
                        meta.get("prune_ratio"),
                        meta.get("convergence_rate"),
                        meta.get("structural_volatility_score"),
                    ),
                )
                run_id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"Research run saved with id={run_id}")
            return run_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save run: {e}")
            raise
        finally:
            self.connection_pool.putconn(conn)

    def get_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a single research run by ID (full detail)."""
        select_sql = """
        SELECT id, query, plan_json, report_json, confidence_score, iterations,
               run_mode,
               total_subtopics_encountered, total_subtopics_added,
               total_subtopics_removed, max_active_subtopics,
               structural_complexity_score,
               plan_expansion_ratio, prune_ratio,
               convergence_rate, structural_volatility_score,
               created_at
        FROM research_runs
        WHERE id = %s;
        """
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(select_sql, (run_id,))
                row = cur.fetchone()
            if row is None:
                return None
            return self._serialize_row(row)
        except Exception as e:
            logger.error(f"Failed to get run {run_id}: {e}")
            raise
        finally:
            self.connection_pool.putconn(conn)

    def list_runs(self) -> List[Dict[str, Any]]:
        """List all research runs (lightweight — no full report JSON)."""
        select_sql = """
        SELECT id, query, confidence_score, iterations,
               run_mode, structural_complexity_score, created_at
        FROM research_runs
        ORDER BY created_at DESC;
        """
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(select_sql)
                rows = cur.fetchall()
            return [self._serialize_row(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to list runs: {e}")
            raise
        finally:
            self.connection_pool.putconn(conn)

    def close(self) -> None:
        """Close all connections in the pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connection pool closed.")

    @staticmethod
    def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a database row dict to JSON-serializable format."""
        result = dict(row)
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
        return result
