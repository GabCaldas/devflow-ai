import tempfile
import unittest
from pathlib import Path

from app.rag.index import format_context, load_chunks, retrieve_for_diff


class CodeRagTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "payments.py").write_text(
            "def authorize_payment(card, amount):\n"
            "    return gateway.authorize(card, amount)\n\n"
            "def refund_payment(transaction_id):\n"
            "    return gateway.refund(transaction_id)\n",
            encoding="utf-8",
        )
        (self.root / "src" / "logging.py").write_text(
            "def write_log(message):\n    print(message)\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_retrieves_relevant_file(self) -> None:
        diff = (
            "diff --git a/src/payments.py b/src/payments.py\n"
            "--- a/src/payments.py\n+++ b/src/payments.py\n"
            "+def refund_payment(transaction_id):\n"
            "+    return gateway.refund(transaction_id)\n"
        )
        results = retrieve_for_diff(self.root, diff, top_k=1)
        self.assertEqual(results[0].path, "src/payments.py")
        self.assertGreater(results[0].score, 0)

    def test_ignores_dependency_directories(self) -> None:
        dependency = self.root / "node_modules" / "package"
        dependency.mkdir(parents=True)
        (dependency / "index.js").write_text("function refundPayment() {}", encoding="utf-8")
        paths = {chunk.path for chunk in load_chunks(self.root)}
        self.assertNotIn("node_modules/package/index.js", paths)

    def test_context_respects_character_budget(self) -> None:
        results = retrieve_for_diff(self.root, "authorize payment gateway", top_k=2)
        for budget in (120, 200, 300):
            self.assertLessEqual(len(format_context(results, max_chars=budget)), budget)


if __name__ == "__main__":
    unittest.main()
