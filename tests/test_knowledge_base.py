"""Tests for knowledge base module."""

import pytest
import tempfile
import json
from pathlib import Path

from opsilot.knowledge_base.loader import KnowledgeBase, Runbook


class TestRunbook:
    """Tests for Runbook dataclass."""

    def test_from_dict_valid(self):
        data = {
            "runbook_id": "test-001",
            "title": "Test Runbook",
            "category": "test",
            "content": "Test content",
            "tags": ["tag1", "tag2"],
        }
        rb = Runbook.from_dict(data)
        assert rb.runbook_id == "test-001"
        assert rb.title == "Test Runbook"
        assert rb.category == "test"
        assert rb.content == "Test content"
        assert rb.tags == ["tag1", "tag2"]

    def test_from_dict_minimal(self):
        data = {
            "runbook_id": "test-001",
            "title": "Test Runbook",
            "category": "test",
            "content": "Test content",
        }
        rb = Runbook.from_dict(data)
        assert rb.tags == []

    def test_from_dict_missing_field(self):
        data = {
            "runbook_id": "test-001",
            "title": "Test Runbook",
            # Missing category and content
        }
        with pytest.raises(ValueError, match="Missing required fields"):
            Runbook.from_dict(data)

    def test_to_dict(self):
        rb = Runbook(
            runbook_id="test-001",
            title="Test Runbook",
            category="test",
            content="Test content",
            tags=["tag1"],
        )
        data = rb.to_dict()
        assert data["runbook_id"] == "test-001"
        assert data["title"] == "Test Runbook"
        assert data["category"] == "test"
        assert data["content"] == "Test content"
        assert data["tags"] == ["tag1"]


class TestKnowledgeBase:
    """Tests for KnowledgeBase."""

    @pytest.fixture
    def sample_runbooks(self):
        return [
            Runbook("kb-001", "Printer Issues", "hardware", "Printer content", ["printer"]),
            Runbook("kb-002", "VPN Setup", "network", "VPN content", ["vpn", "network"]),
            Runbook("kb-003", "MFA Reset", "security", "MFA content", ["mfa", "security"]),
            Runbook("kb-004", "DHCP Config", "network", "DHCP content", ["dhcp"]),
        ]

    @pytest.fixture
    def kb(self, sample_runbooks):
        return KnowledgeBase(sample_runbooks)

    def test_init(self, kb):
        assert len(kb) == 4

    def test_from_json_file(self, sample_runbooks):
        data = [rb.to_dict() for rb in sample_runbooks]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name
        try:
            kb = KnowledgeBase.from_json_file(temp_path)
            assert len(kb) == 4
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_from_json_file_invalid_root(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"not": "a list"}, f)
            temp_path = f.name
        try:
            with pytest.raises(ValueError, match="JSON root must be a list"):
                KnowledgeBase.from_json_file(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_contains(self, kb):
        assert "kb-001" in kb
        assert "kb-999" not in kb

    def test_get(self, kb):
        rb = kb.get("kb-001")
        assert rb is not None
        assert rb.runbook_id == "kb-001"
        assert kb.get("kb-999") is None

    def test_by_category(self, kb):
        by_cat = kb.by_category
        assert "hardware" in by_cat
        assert "network" in by_cat
        assert "security" in by_cat
        assert len(by_cat["network"]) == 2

    def test_categories(self, kb):
        cats = kb.categories
        assert "hardware" in cats
        assert "network" in cats
        assert "security" in cats
        assert len(cats) == 3

    def test_runbooks_property(self, kb):
        runbooks = kb.runbooks
        assert len(runbooks) == 4
        assert all(isinstance(rb, Runbook) for rb in runbooks)

    def test_iteration(self, kb):
        ids = [rb.runbook_id for rb in kb]
        assert "kb-001" in ids
        assert "kb-004" in ids