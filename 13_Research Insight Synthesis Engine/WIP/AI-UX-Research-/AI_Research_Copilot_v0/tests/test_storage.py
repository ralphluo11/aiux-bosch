import tempfile
import unittest
from pathlib import Path

from ai_ux_core.storage import ResearchProjectRepository


class ResearchProjectRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = ResearchProjectRepository(
            Path(self.temp_dir.name) / "research.db"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_project_transcripts_and_analysis_survive_repository_restart(self):
        project = self.repository.create_project(
            {
                "name": "Study",
                "research_goal": "理解体验",
                "research_questions": ["发生了什么？"],
            }
        )
        self.repository.add_transcript(
            project["id"],
            {
                "participant_id": "P01",
                "file_name": "P01.txt",
                "content": "这是原始访谈。",
            },
        )
        self.repository.save_analysis(
            project["id"],
            {
                "agent_mode": "offline_preview",
                "model": None,
                "executive_summary": "Preview",
                "evidence": [],
                "findings": [],
                "insights": [],
                "gaps": [],
                "limitations": [],
            },
        )

        reopened = ResearchProjectRepository(self.repository.database_path)
        saved = reopened.get_project(project["id"])
        self.assertEqual(saved["transcript_count"], 1)
        self.assertEqual(saved["transcripts"][0]["participant_id"], "P01")
        self.assertEqual(saved["latest_analysis"]["executive_summary"], "Preview")

    def test_duplicate_participant_is_rejected(self):
        project = self.repository.create_project(
            {
                "name": "Study",
                "research_goal": "Goal",
                "research_questions": ["Question"],
            }
        )
        payload = {
            "participant_id": "P01",
            "file_name": "P01.txt",
            "content": "Transcript",
        }
        self.repository.add_transcript(project["id"], payload)
        with self.assertRaisesRegex(ValueError, "already_exists"):
            self.repository.add_transcript(project["id"], payload)


if __name__ == "__main__":
    unittest.main()
