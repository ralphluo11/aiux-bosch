from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4


class ProjectNotFoundError(KeyError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class ResearchProjectRepository:
    """Small SQLite repository for the v0.5 validation release."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    research_goal TEXT NOT NULL,
                    research_questions_json TEXT NOT NULL,
                    target_users TEXT NOT NULL DEFAULT '',
                    project_notes TEXT NOT NULL DEFAULT '',
                    language TEXT NOT NULL DEFAULT 'zh-CN',
                    status TEXT NOT NULL DEFAULT 'draft',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS transcripts (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    participant_id TEXT NOT NULL,
                    segment TEXT NOT NULL DEFAULT '',
                    file_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(project_id, participant_id)
                );

                CREATE TABLE IF NOT EXISTS analysis_runs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    agent_mode TEXT NOT NULL,
                    model TEXT,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS questionnaire_runs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    agent_mode TEXT NOT NULL,
                    model TEXT,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'draft',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(project_id, kind)
                );

                CREATE TABLE IF NOT EXISTS project_chat_messages (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    source_ids_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_transcripts_project
                    ON transcripts(project_id);
                CREATE INDEX IF NOT EXISTS idx_runs_project
                    ON analysis_runs(project_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_questionnaire_runs_project
                    ON questionnaire_runs(project_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_project_chat_messages_project
                    ON project_chat_messages(project_id, created_at DESC);
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(projects)")}
            if "project_notes" not in columns:
                connection.execute("ALTER TABLE projects ADD COLUMN project_notes TEXT NOT NULL DEFAULT ''")

    def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = payload.get("name")
        goal = payload.get("research_goal")
        questions = payload.get("research_questions")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("project_name_is_required")
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("research_goal_is_required")
        if not isinstance(questions, list) or not questions:
            raise ValueError("research_questions_must_be_a_non_empty_array")
        clean_questions = [
            item.strip() for item in questions if isinstance(item, str) and item.strip()
        ]
        if len(clean_questions) != len(questions):
            raise ValueError("research_questions_must_contain_non_empty_strings")
        project_id = _id("project")
        timestamp = _now()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO projects (
                    id, name, research_goal, research_questions_json,
                    target_users, project_notes, language, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)
                """,
                (
                    project_id,
                    name.strip(),
                    goal.strip(),
                    json.dumps(clean_questions, ensure_ascii=False),
                    str(payload.get("target_users", "")).strip(),
                    str(payload.get("project_notes", "")).strip(),
                    str(payload.get("language", "zh-CN")).strip() or "zh-CN",
                    timestamp,
                    timestamp,
                ),
            )
        return self.get_project(project_id)

    def list_projects(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT p.*,
                       COUNT(DISTINCT t.id) AS transcript_count,
                       COUNT(DISTINCT a.id) AS analysis_count
                FROM projects p
                LEFT JOIN transcripts t ON t.project_id = p.id
                LEFT JOIN analysis_runs a ON a.project_id = p.id
                GROUP BY p.id
                ORDER BY p.updated_at DESC
                """
            ).fetchall()
        return [self._project_row(row) for row in rows]

    def update_project(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_project(project_id)
        name = str(payload.get("name", "")).strip()
        goal = str(payload.get("research_goal", "")).strip()
        questions = payload.get("research_questions")
        if not name:
            raise ValueError("project_name_is_required")
        if not goal:
            raise ValueError("research_goal_is_required")
        if not isinstance(questions, list) or not questions:
            raise ValueError("research_questions_must_be_a_non_empty_array")
        clean_questions = [item.strip() for item in questions if isinstance(item, str) and item.strip()]
        if len(clean_questions) != len(questions):
            raise ValueError("research_questions_must_contain_non_empty_strings")
        with self._lock, self._connect() as connection:
            connection.execute(
                """UPDATE projects SET name = ?, research_goal = ?, research_questions_json = ?,
                   target_users = ?, project_notes = ?, language = ?, updated_at = ? WHERE id = ?""",
                (name, goal, json.dumps(clean_questions, ensure_ascii=False),
                 str(payload.get("target_users", "")).strip(),
                 str(payload.get("project_notes", "")).strip(),
                 str(payload.get("language", "zh-CN")).strip() or "zh-CN", _now(), project_id),
            )
        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        return {"deleted": True, "project_id": project_id, "name": project["name"]}

    def get_project(self, project_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            if row is None:
                raise ProjectNotFoundError(project_id)
            transcripts = connection.execute(
                """
                SELECT id, participant_id, segment, file_name, content, created_at
                FROM transcripts WHERE project_id = ? ORDER BY created_at, participant_id
                """,
                (project_id,),
            ).fetchall()
            latest = connection.execute(
                """
                SELECT id, agent_mode, model, result_json, created_at
                FROM analysis_runs WHERE project_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (project_id,),
            ).fetchone()
            latest_questionnaire = connection.execute(
                """
                SELECT id, agent_mode, model, result_json, created_at
                FROM questionnaire_runs WHERE project_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (project_id,),
            ).fetchone()
            artifacts = connection.execute(
                "SELECT * FROM artifacts WHERE project_id = ? ORDER BY updated_at DESC",
                (project_id,),
            ).fetchall()
            chat_messages = connection.execute(
                """SELECT id, role, content, source_ids_json, created_at
                   FROM project_chat_messages WHERE project_id = ?
                   ORDER BY created_at DESC, rowid DESC LIMIT 100""",
                (project_id,),
            ).fetchall()
        result = self._project_row(row)
        result["transcripts"] = [dict(item) for item in transcripts]
        result["transcript_count"] = len(transcripts)
        result["latest_analysis"] = self._analysis_row(latest) if latest else None
        result["latest_questionnaire"] = (
            self._questionnaire_row(latest_questionnaire)
            if latest_questionnaire else None
        )
        result["artifacts"] = [dict(item) for item in artifacts]
        result["chat_messages"] = [
            {
                **dict(item),
                "source_ids": json.loads(item["source_ids_json"]),
            }
            for item in reversed(chat_messages)
        ]
        return result

    def save_chat_exchange(
        self,
        project_id: str,
        *,
        question: str,
        answer: str,
        source_ids: list[str],
    ) -> None:
        self._require_project(project_id)
        timestamp = _now()
        with self._lock, self._connect() as connection:
            connection.executemany(
                """INSERT INTO project_chat_messages
                   (id, project_id, role, content, source_ids_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    (_id("chat"), project_id, "user", question, "[]", timestamp),
                    (_id("chat"), project_id, "assistant", answer, json.dumps(source_ids, ensure_ascii=False), timestamp),
                ],
            )
            connection.execute(
                "UPDATE projects SET updated_at = ? WHERE id = ?",
                (timestamp, project_id),
            )

    def save_artifact(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_project(project_id)
        kind = str(payload.get("kind", "")).strip()
        title = str(payload.get("title", "")).strip()
        content = str(payload.get("content", ""))
        status = str(payload.get("status", "draft")).strip() or "draft"
        if not kind or not title:
            raise ValueError("artifact_kind_and_title_are_required")
        timestamp = _now()
        with self._lock, self._connect() as connection:
            existing = connection.execute(
                "SELECT id, created_at FROM artifacts WHERE project_id = ? AND kind = ?",
                (project_id, kind),
            ).fetchone()
            artifact_id = existing["id"] if existing else _id("artifact")
            created_at = existing["created_at"] if existing else timestamp
            connection.execute(
                """INSERT INTO artifacts (id, project_id, kind, title, content, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(project_id, kind) DO UPDATE SET title=excluded.title,
                   content=excluded.content, status=excluded.status, updated_at=excluded.updated_at""",
                (artifact_id, project_id, kind, title, content, status, created_at, timestamp),
            )
            connection.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (timestamp, project_id))
        return dict(self._connect().execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone())

    def add_transcript(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_project(project_id)
        participant_id = payload.get("participant_id")
        content = payload.get("content")
        file_name = payload.get("file_name")
        if not isinstance(participant_id, str) or not participant_id.strip():
            raise ValueError("participant_id_is_required")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("transcript_text_is_required")
        if len(content) > 200_000:
            raise ValueError("single_source_limit_is_200000_characters")
        if not isinstance(file_name, str) or not file_name.strip():
            file_name = f"{participant_id.strip()}.txt"
        transcript_id = _id("transcript")
        timestamp = _now()
        try:
            with self._lock, self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO transcripts (
                        id, project_id, participant_id, segment,
                        file_name, content, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        transcript_id,
                        project_id,
                        participant_id.strip(),
                        str(payload.get("segment", "")).strip(),
                        file_name.strip(),
                        content.strip(),
                        timestamp,
                    ),
                )
                connection.execute(
                    "UPDATE projects SET updated_at = ? WHERE id = ?",
                    (timestamp, project_id),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("participant_id_already_exists_in_project") from exc
        return {
            "id": transcript_id,
            "project_id": project_id,
            "participant_id": participant_id.strip(),
            "segment": str(payload.get("segment", "")).strip(),
            "file_name": file_name.strip(),
            "content": content.strip(),
            "created_at": timestamp,
        }

    def update_transcript_segment(self, project_id: str, transcript_id: str, segment: str) -> dict[str, Any]:
        if segment not in {"project_context", "research_result", "unclassified"}:
            raise ValueError("invalid_source_category")
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "UPDATE transcripts SET segment = ? WHERE id = ? AND project_id = ?",
                (segment, transcript_id, project_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("source_not_found")
            connection.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (_now(), project_id))
        return self.get_project(project_id)

    def delete_transcript(self, project_id: str, transcript_id: str) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM transcripts WHERE id = ? AND project_id = ?",
                (transcript_id, project_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("source_not_found")
            connection.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (_now(), project_id))
        return {"deleted": True, "source_id": transcript_id}

    def save_analysis(self, project_id: str, result: dict[str, Any]) -> dict[str, Any]:
        self._require_project(project_id)
        run_id = _id("run")
        timestamp = _now()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO analysis_runs (
                    id, project_id, agent_mode, model, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    project_id,
                    str(result.get("agent_mode", "unknown")),
                    result.get("model"),
                    json.dumps(result, ensure_ascii=False),
                    timestamp,
                ),
            )
            connection.execute(
                "UPDATE projects SET status = 'analyzed', updated_at = ? WHERE id = ?",
                (timestamp, project_id),
            )
        return {
            "id": run_id,
            "project_id": project_id,
            "created_at": timestamp,
            **result,
        }

    def save_questionnaire(
        self, project_id: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        self._require_project(project_id)
        run_id = _id("questionnaire_run")
        timestamp = _now()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO questionnaire_runs (
                    id, project_id, agent_mode, model, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    project_id,
                    str(result.get("agent_mode", "unknown")),
                    result.get("model"),
                    json.dumps(result, ensure_ascii=False),
                    timestamp,
                ),
            )
            connection.execute(
                "UPDATE projects SET updated_at = ? WHERE id = ?",
                (timestamp, project_id),
            )
        return {
            "id": run_id,
            "project_id": project_id,
            "created_at": timestamp,
            **result,
        }

    def _require_project(self, project_id: str) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        if row is None:
            raise ProjectNotFoundError(project_id)

    @staticmethod
    def _project_row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["research_questions"] = json.loads(result.pop("research_questions_json"))
        return result

    @staticmethod
    def _analysis_row(row: sqlite3.Row) -> dict[str, Any]:
        result = json.loads(row["result_json"])
        return {
            "id": row["id"],
            "agent_mode": row["agent_mode"],
            "model": row["model"],
            "created_at": row["created_at"],
            **result,
        }

    @staticmethod
    def _questionnaire_row(row: sqlite3.Row) -> dict[str, Any]:
        result = json.loads(row["result_json"])
        return {
            "id": row["id"],
            "agent_mode": row["agent_mode"],
            "model": row["model"],
            "created_at": row["created_at"],
            **result,
        }
