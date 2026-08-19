import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import seedance_adapter as adapter


class AdapterTests(unittest.TestCase):
    def test_build_content_uses_data_url_and_motion_flags(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "frame.png"
            image.write_bytes(b"png")
            content = adapter.build_content("评分条依次展开", image, "16:9", 5)
        self.assertEqual(content[0]["text"], "评分条依次展开 --ratio 16:9 --dur 5")
        encoded = content[1]["image_url"]["url"]
        self.assertTrue(encoded.startswith("data:image/png;base64,"))
        self.assertEqual(base64.b64decode(encoded.split(",", 1)[1]), b"png")

    def test_find_video_url(self):
        self.assertEqual(
            adapter.find_video_url({"content": {"video_url": "https://example.test/result.mp4"}}),
            "https://example.test/result.mp4",
        )

    def test_wait_for_task_reaches_success(self):
        config = adapter.Config(api_key="test", poll_seconds=0, timeout_seconds=10)
        responses = [
            {"id": "cgt-1", "status": "queued"},
            {"id": "cgt-1", "status": "succeeded", "content": {"video_url": "https://x/video.mp4"}},
        ]
        with patch.object(adapter, "get_task", side_effect=responses):
            result = adapter.wait_for_task(config, "cgt-1", sleep=lambda _: None)
        self.assertEqual(result["status"], "succeeded")


if __name__ == "__main__":
    unittest.main()
