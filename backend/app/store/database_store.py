import json
import logging
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import ValidationError

from .store_base import StateStore
from app.schemas.agentic.investigation import InvestigationState
from app.config import settings

logger = logging.getLogger(__name__)

class DatabaseStateStore(StateStore):
    def __init__(self, db_url: Optional[str] = None) -> None:
        self.db_url = db_url or settings.database_url
        if not self.db_url:
            logger.warning("No DATABASE_URL configured. DatabaseStateStore may fail.")
        # Fallback in-memory store for resilience
        self._fallback: dict = {}

    def _get_connection(self):
        return psycopg2.connect(self.db_url)

    def _ensure_table(self, conn) -> None:
        """Create the agentic_investigation_state table if it doesn't exist."""
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS agentic_investigation_state (
                    investigation_id VARCHAR(255) PRIMARY KEY,
                    state_data JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        conn.commit()

    def save(self, state: InvestigationState) -> None:
        try:
            with self._get_connection() as conn:
                self._ensure_table(conn)
                with conn.cursor() as cur:
                    state_json = state.model_dump_json()
                    cur.execute('''
                        INSERT INTO agentic_investigation_state (investigation_id, state_data, updated_at)
                        VALUES (%s, %s::jsonb, CURRENT_TIMESTAMP)
                        ON CONFLICT (investigation_id) DO UPDATE
                        SET state_data = EXCLUDED.state_data, updated_at = CURRENT_TIMESTAMP
                    ''', (state.investigation_id, state_json))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save state to PostgreSQL, using fallback: {e}")
            self._fallback[state.investigation_id] = state

    def get(self, investigation_id: str) -> Optional[InvestigationState]:
        """
        Get investigation state by investigation_id OR claim_id.
        If investigation_id not found, tries to find by claim_id.
        Returns most recent investigation for that claim.
        """
        try:
            with self._get_connection() as conn:
                self._ensure_table(conn)
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # First try by investigation_id
                    cur.execute('''
                        SELECT state_data FROM agentic_investigation_state
                        WHERE investigation_id = %s
                    ''', (investigation_id,))
                    row = cur.fetchone()
                    
                    # If not found, try by claim_id (query JSONB)
                    if not row:
                        cur.execute('''
                            SELECT state_data FROM agentic_investigation_state
                            WHERE state_data->>'claim_id' = %s
                            ORDER BY updated_at DESC
                            LIMIT 1
                        ''', (investigation_id,))
                        row = cur.fetchone()
                    
                    if row and row['state_data']:
                        try:
                            data = row['state_data']
                            if isinstance(data, str):
                                data = json.loads(data)
                            return InvestigationState(**data)
                        except ValidationError as ve:
                            logger.error(f"Failed to deserialize state {investigation_id}: {ve}")
                            return None
            return self._fallback.get(investigation_id)
        except Exception as e:
            logger.error(f"Failed to get state from PostgreSQL, checking fallback: {e}")
            return self._fallback.get(investigation_id)

    def all_investigations(self) -> list[InvestigationState]:
        results = []
        try:
            with self._get_connection() as conn:
                self._ensure_table(conn)
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT state_data FROM agentic_investigation_state ORDER BY updated_at DESC")
                    rows = cur.fetchall()
                    for row in rows:
                        data = row['state_data']
                        if isinstance(data, str):
                            data = json.loads(data)
                        try:
                            results.append(InvestigationState(**data))
                        except ValidationError:
                            pass
        except Exception as e:
            logger.error(f"Failed to fetch all states from PostgreSQL: {e}")
            results = list(self._fallback.values())
        return results
