#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agents = _load("agents", "agents.py")
docs_check = _load("docs_check", "docs-check.py")


class AgentsTest(unittest.TestCase):
    def setUp(self):
        self.reg = agents.load()

    def test_copilot_is_an_owner_and_reviewer_only_agents_are_not(self):
        self.assertEqual(agents.owners(self.reg), ["claude", "codex", "copilot"])

    def test_vendors_cover_every_copilot_family(self):
        for model, vendor in {"mai-code-2-flash": "microsoft", "gpt-5.6-luna": "openai",
                              "gpt-5.3-codex": "openai", "claude-haiku-5.5": "anthropic",
                              "gemini-4-hydrogen": "google", "grok-4.7": "xai", "kimi-k3": "moonshot"}.items():
            self.assertEqual(agents.model_vendor(self.reg, model), vendor)

    def test_same_vendor_never_reviews_whatever_the_version(self):
        for reviewer, model in (("gemini", "gemini-4-hydrogen"), ("gemini", "gemini-3.8-flash"),
                                ("claude", "claude-sonnet-5"), ("codex", "gpt-6.1-terra"), ("kimi", "kimi-k3")):
            with self.subTest(reviewer=reviewer, model=model), self.assertRaises(agents.IdentityError):
                agents.check(self.reg, reviewer, "copilot", (), (model,))

    def test_other_vendor_may_review(self):
        agents.check(self.reg, "claude", "copilot", (), ("gpt-6-luna", "mai-code-2"))
        agents.check(self.reg, "gemini", "claude")
        agents.check(self.reg, "claude", "codex")

    def test_owner_channel_rule_still_holds(self):
        for reviewer, owner in (("claude", "claude"), ("codex", "codex")):
            with self.subTest(owner=owner), self.assertRaises(agents.IdentityError):
                agents.check(self.reg, reviewer, owner)

    def test_copilot_reviews_only_through_a_model_of_another_vendor(self):
        agents.check(self.reg, "copilot", "claude", reviewer_model="gpt-6-luna")
        for model in ("claude-haiku-5.5", None):
            with self.subTest(model=model), self.assertRaises(agents.IdentityError):
                agents.check(self.reg, "copilot", "claude", reviewer_model=model)
        with self.assertRaises(agents.IdentityError):
            agents.check(self.reg, "copilot", "copilot", reviewer_model="gpt-6-luna")

    def test_cli_exit_codes(self):
        self.assertEqual(agents.main(["agents.py", "check", "claude", "--owner", "codex"]), 0)
        self.assertEqual(agents.main(["agents.py", "check", "claude", "--owner", "copilot"]), 64)
        self.assertEqual(agents.main(["agents.py", "check", "claude", "--owner"]), 64)


class ArtifactIdentityTest(unittest.TestCase):
    def test_markdown_and_json_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "claude-2026-11-20-topic-r01.md"
            md.write_text("# Claude review\n\nOwner: copilot\nAuthor models: gpt-6.1-terra, mai-code-2-flash\n"
                          "Task: T7\n\nBody mentioning Owner: claude later is ignored.\n")
            self.assertEqual(docs_check.artifact_identity(md),
                             ("claude", "copilot", [], ["gpt-6.1-terra", "mai-code-2-flash"], None))
            js = Path(tmp) / "gemini-2026-11-20-topic-r02.json"
            js.write_text(json.dumps({"response": "x", "reviewer_metadata": {
                "owner": "copilot", "authors": [], "author_models": ["gemini-4-hydrogen"]}}))
            reviewer, owner, authors, models, rmodel = docs_check.artifact_identity(js)
            with self.assertRaises(agents.IdentityError):
                agents.check(agents.load(), reviewer, owner, authors, models, rmodel)

    def test_legacy_artifact_without_identity_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "claude-2026-10-01-old.md"
            md.write_text("# Claude review\n\nWrapper revision: abc\n\nBody\n")
            reviewer, owner, authors, models, rmodel = docs_check.artifact_identity(md)
            agents.check(agents.load(), reviewer, owner, authors, models, rmodel)

    def test_copilot_artifact_vendor_comes_from_the_selected_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "copilot-2026-11-21-topic.md"
            md.write_text("# Copilot review\n\nOwner: copilot\nAuthor models: gpt-6-luna\n"
                          "Selected model: claude-sonnet-5.5\nReviewer vendor: anthropic\n\nBody\n")
            ident = docs_check.artifact_identity(md)
            self.assertEqual(ident, ("copilot", "copilot", [], ["gpt-6-luna"], "claude-sonnet-5.5"))
            agents.check(agents.load(), *ident)
            md2 = Path(tmp) / "copilot-2026-11-21-other.md"
            md2.write_text("# Copilot review\n\nOwner: copilot\nAuthor models: gpt-6-luna\n"
                           "Selected model: gpt-6.1-terra\n\nBody\n")
            with self.assertRaises(agents.IdentityError):
                agents.check(agents.load(), *docs_check.artifact_identity(md2))
            md3 = Path(tmp) / "copilot-2026-11-21-none.md"
            md3.write_text("# Copilot review\n\nOwner: claude\n\nBody\n")
            with self.assertRaises(agents.IdentityError):  # no model: vendor unknown
                agents.check(agents.load(), *docs_check.artifact_identity(md3))


if __name__ == "__main__":
    unittest.main()
