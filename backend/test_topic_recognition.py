import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.services import llm_router

client = TestClient(app)


class TestTopicRecognition(unittest.TestCase):
    def test_greeting_only_returns_new_conversation(self):
        messages = [{"role": "user", "content": "hi"}]
        title = llm_router.generate_conversation_title(messages)
        self.assertEqual(title, "New Conversation")

        messages2 = [{"role": "user", "content": "Hello! Good morning"}]
        title2 = llm_router.generate_conversation_title(messages2)
        self.assertEqual(title2, "New Conversation")

    def test_topic_generation_with_llm(self):
        messages = [
            {"role": "user", "content": "How can I configure sqlite-vec in FastAPI for local RAG?"},
            {"role": "assistant", "content": "You can load sqlite-vec extension and create virtual tables."},
        ]
        with patch.object(llm_router, "_generate", return_value="FastAPI sqlite-vec Setup"):
            title = llm_router.generate_conversation_title(messages)
            self.assertEqual(title, "FastAPI sqlite-vec Setup")

    def test_title_endpoint(self):
        with patch("app.api.v1.chat.generate_conversation_title", return_value="Database Architecture"):
            resp = client.post("/api/v1/chat/test_topic_conv/title")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("title", data)
            self.assertEqual(data["title"], "Database Architecture")


if __name__ == "__main__":
    unittest.main()
