from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .application import (
    InterviewApplication,
    SessionNotFoundError,
    build_demo_application,
)
from .research_agent import ResearchAgentError
from .storage import ProjectNotFoundError


class InterviewRequestHandler(BaseHTTPRequestHandler):
    application: InterviewApplication
    static_dir: Path

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(self.application.runtime_payload())
            return
        if path == "/api/study":
            self._send_json(self.application.study_payload())
            return
        if path == "/api/projects":
            self._send_json(self.application.list_projects())
            return
        if path.startswith("/api/analysis-jobs/"):
            job_id = path.removeprefix("/api/analysis-jobs/").strip("/")
            try:
                self._send_json(self.application.get_analysis_job(job_id))
            except KeyError:
                self._send_error(HTTPStatus.NOT_FOUND, "analysis_job_not_found")
            return
        if path.startswith("/api/projects/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3:
                try:
                    self._send_json(self.application.get_project(parts[2]))
                except ProjectNotFoundError:
                    self._send_error(HTTPStatus.NOT_FOUND, "project_not_found")
                return
        if path.startswith("/api/sessions/") and path.endswith("/evaluation"):
            session_id = (
                path.removeprefix("/api/sessions/")
                .removesuffix("/evaluation")
                .strip("/")
            )
            try:
                self._send_json(self.application.get_evaluation(session_id))
            except SessionNotFoundError:
                self._send_error(HTTPStatus.NOT_FOUND, "session_not_found")
            return
        if path.startswith("/api/sessions/"):
            session_id = path.removeprefix("/api/sessions/").strip("/")
            if not session_id:
                self._send_error(HTTPStatus.NOT_FOUND, "route_not_found")
                return
            try:
                self._send_json(self.application.get_session(session_id))
            except SessionNotFoundError:
                self._send_error(HTTPStatus.NOT_FOUND, "session_not_found")
            return
        if path.startswith("/api/"):
            self._send_error(HTTPStatus.NOT_FOUND, "route_not_found")
            return
        self._serve_static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/projects":
            try:
                self._send_json(
                    self.application.create_project(self._read_json()),
                    status=HTTPStatus.CREATED,
                )
            except ValueError as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        if path.startswith("/api/projects/"):
            parts = path.strip("/").split("/")
            try:
                if len(parts) == 4 and parts[3] == "brief":
                    self._send_json(
                        self.application.update_project(parts[2], self._read_json())
                    )
                    return
                if len(parts) == 5 and parts[3] == "sources":
                    payload = self._read_json()
                    self._send_json(self.application.classify_project_source(parts[2], parts[4], str(payload.get("category", ""))))
                    return
                if len(parts) == 4 and parts[3] == "artifacts":
                    self._send_json(
                        self.application.save_project_artifact(parts[2], self._read_json()),
                        status=HTTPStatus.CREATED,
                    )
                    return
                if len(parts) == 5 and parts[3] == "artifacts" and parts[4] == "revise":
                    self._send_json(
                        self.application.revise_project_artifact(parts[2], self._read_json())
                    )
                    return
                if len(parts) == 4 and parts[3] == "transcripts":
                    self._send_json(
                        self.application.add_project_transcript(
                            parts[2], self._read_json()
                        ),
                        status=HTTPStatus.CREATED,
                    )
                    return
                if len(parts) == 4 and parts[3] == "documents":
                    self._send_json(
                        self.application.add_project_document(
                            parts[2], self._read_json()
                        ),
                        status=HTTPStatus.CREATED,
                    )
                    return
                if len(parts) == 4 and parts[3] == "analyze":
                    self._send_json(self.application.analyze_project(parts[2]))
                    return
                if len(parts) == 4 and parts[3] == "analysis-jobs":
                    self._send_json(
                        self.application.create_analysis_job(parts[2]),
                        status=HTTPStatus.ACCEPTED,
                    )
                    return
                if len(parts) == 4 and parts[3] == "questionnaire":
                    self._send_json(
                        self.application.generate_project_questionnaire(parts[2]),
                        status=HTTPStatus.CREATED,
                    )
                    return
                if len(parts) == 4 and parts[3] == "summary":
                    self._send_json(self.application.summarize_project_context(parts[2]))
                    return
            except ProjectNotFoundError:
                self._send_error(HTTPStatus.NOT_FOUND, "project_not_found")
                return
            except ValueError as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            except ResearchAgentError as exc:
                self._send_error(HTTPStatus.BAD_GATEWAY, str(exc))
                return
        if path == "/api/agent/analyze":
            try:
                self._send_json(self.application.analyze_research(self._read_json()))
            except ValueError as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
            except ResearchAgentError as exc:
                self._send_error(HTTPStatus.BAD_GATEWAY, str(exc))
            return
        if path == "/api/sessions":
            self._send_json(
                self.application.create_session(),
                status=HTTPStatus.CREATED,
            )
            return
        if path.startswith("/api/sessions/") and path.endswith("/answers"):
            session_id = path.removeprefix("/api/sessions/").removesuffix("/answers").strip("/")
            try:
                payload = self._read_json()
                final_transcript = payload.get("final_transcript")
                if not isinstance(final_transcript, str):
                    self._send_error(
                        HTTPStatus.BAD_REQUEST,
                        "final_transcript_must_be_a_string",
                    )
                    return
                result = self.application.submit_answer(
                    session_id=session_id,
                    final_transcript=final_transcript,
                )
                self._send_json(result)
            except SessionNotFoundError:
                self._send_error(HTTPStatus.NOT_FOUND, "session_not_found")
            except ValueError as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        if path.startswith("/api/sessions/") and path.endswith("/reviews"):
            session_id = (
                path.removeprefix("/api/sessions/")
                .removesuffix("/reviews")
                .strip("/")
            )
            try:
                payload = self._read_json()
                action = payload.get("action")
                if not isinstance(action, str):
                    self._send_error(
                        HTTPStatus.BAD_REQUEST,
                        "review_action_must_be_a_string",
                    )
                    return
                result = self.application.review_last_decision(
                    session_id,
                    action=action,
                    edited_question=payload.get("edited_question"),
                    ratings=payload.get("ratings"),
                    notes=payload.get("notes"),
                )
                self._send_json(result)
            except SessionNotFoundError:
                self._send_error(HTTPStatus.NOT_FOUND, "session_not_found")
            except ValueError as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        self._send_error(HTTPStatus.NOT_FOUND, "route_not_found")

    def do_DELETE(self) -> None:
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "projects":
            try:
                self._send_json(self.application.delete_project(parts[2]))
            except ProjectNotFoundError:
                self._send_error(HTTPStatus.NOT_FOUND, "project_not_found")
            return
        if len(parts) == 5 and parts[0] == "api" and parts[1] == "projects" and parts[3] == "sources":
            try:
                self._send_json(self.application.delete_project_source(parts[2], parts[4]))
            except ProjectNotFoundError:
                self._send_error(HTTPStatus.NOT_FOUND, "project_not_found")
            except ValueError as exc:
                self._send_error(HTTPStatus.NOT_FOUND, str(exc))
            return
        self._send_error(HTTPStatus.NOT_FOUND, "route_not_found")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid_content_length") from exc
        if length <= 0:
            return {}
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("invalid_json") from exc
        if not isinstance(payload, dict):
            raise ValueError("json_body_must_be_an_object")
        return payload

    def _serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path == "/" else request_path.lstrip("/")
        candidate = (self.static_dir / relative).resolve()
        static_root = self.static_dir.resolve()
        if static_root not in candidate.parents and candidate != static_root:
            self._send_error(HTTPStatus.NOT_FOUND, "file_not_found")
            return
        if not candidate.is_file():
            self._send_error(HTTPStatus.NOT_FOUND, "file_not_found")
            return

        content_type, _ = mimetypes.guess_type(candidate.name)
        data = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(
        self,
        payload: dict,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_error(self, status: HTTPStatus, code: str) -> None:
        self._send_json({"error": code}, status=status)


def build_server(
    host: str,
    port: int,
    application: InterviewApplication,
    static_dir: str | Path,
) -> ThreadingHTTPServer:
    handler = type(
        "ConfiguredInterviewRequestHandler",
        (InterviewRequestHandler,),
        {
            "application": application,
            "static_dir": Path(static_dir),
        },
    )
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI UX interview prototype.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    application = build_demo_application(project_root)
    server = build_server(
        host=args.host,
        port=args.port,
        application=application,
        static_dir=project_root / "static",
    )
    runtime = application.runtime_payload()
    mode = (
        f"LLM Live · {runtime['model']}"
        if runtime["generation_mode"] == "llm"
        else "Offline Rules · no API key"
    )
    print(f"AI Research Copilot v0.3: http://{args.host}:{args.port}")
    print(f"Generation mode: {mode}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
