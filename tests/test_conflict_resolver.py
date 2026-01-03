"""
Tests for ConflictResolver module.

Verifies:
- Conflict detection works correctly
- Majority vote resolution works
- Escalation happens for ties
- Statistics are accurate
"""

import pytest
from core.conflict_resolver import (
    ConflictResolver, 
    ConflictResolutionStrategy,
    ConflictReport,
    ResolutionResult
)


class TestConflictDetection:
    """Tests for conflict detection functionality."""
    
    @pytest.fixture
    def resolver(self):
        return ConflictResolver(ConflictResolutionStrategy.MAJORITY_VOTE)
    
    def test_no_conflicts_unanimous(self, resolver):
        """Test that unanimous outputs produce no conflicts."""
        outputs = [
            {"pure": ["add"], "impure": ["append_item"]},
            {"pure": ["add"], "impure": ["append_item"]},
        ]
        
        conflicts = resolver.detect_conflicts(outputs, ["pure", "impure"])
        
        assert len(conflicts) == 0
    
    def test_detects_conflict(self, resolver):
        """Test that conflicts are detected."""
        outputs = [
            {"pure": ["add"], "impure": ["append_item"]},
            {"pure": ["add", "append_item"], "impure": []},  # Conflict on append_item
        ]
        
        conflicts = resolver.detect_conflicts(outputs, ["pure", "impure"])
        
        assert len(conflicts) == 1
        assert conflicts[0].item == "append_item"
    
    def test_conflict_votes_counted(self, resolver):
        """Test that votes are counted correctly."""
        outputs = [
            {"pure": [], "impure": ["item"]},
            {"pure": [], "impure": ["item"]},
            {"pure": ["item"], "impure": []},
        ]
        
        conflicts = resolver.detect_conflicts(outputs, ["pure", "impure"])
        
        assert len(conflicts) == 1
        assert conflicts[0].votes["impure"] == 2
        assert conflicts[0].votes["pure"] == 1
    
    def test_multiple_conflicts_detected(self, resolver):
        """Test detection of multiple conflicts."""
        outputs = [
            {"pure": ["a", "b"], "impure": ["c"]},
            {"pure": ["a"], "impure": ["b", "c"]},  # Conflict on 'b'
        ]
        
        conflicts = resolver.detect_conflicts(outputs, ["pure", "impure"])
        
        assert len(conflicts) == 1
        assert conflicts[0].item == "b"


class TestMajorityVoteResolution:
    """Tests for majority vote resolution strategy."""
    
    @pytest.fixture
    def resolver(self):
        return ConflictResolver(ConflictResolutionStrategy.MAJORITY_VOTE)
    
    def test_majority_resolves_to_winner(self, resolver):
        """Test that majority vote picks the winner."""
        outputs = [
            {"pure": [], "impure": ["item"]},
            {"pure": [], "impure": ["item"]},
            {"pure": ["item"], "impure": []},
        ]
        
        result = resolver.resolve(outputs, ["pure", "impure"])
        
        # 2 votes for impure vs 1 for pure -> impure wins
        assert "item" in result.merged_output["impure"]
        assert "item" not in result.merged_output["pure"]
    
    def test_tie_escalates(self, resolver):
        """Test that ties require human review."""
        outputs = [
            {"pure": ["item"], "impure": []},
            {"pure": [], "impure": ["item"]},
        ]
        
        result = resolver.resolve(outputs, ["pure", "impure"])
        
        assert result.has_unresolved_conflicts
        assert "item" in result.items_requiring_review
    
    def test_non_conflicted_items_preserved(self, resolver):
        """Test that non-conflicted items are in output."""
        outputs = [
            {"pure": ["add"], "impure": ["append_item"]},
            {"pure": ["add"], "impure": ["append_item"]},
        ]
        
        result = resolver.resolve(outputs, ["pure", "impure"])
        
        assert "add" in result.merged_output["pure"]
        assert "append_item" in result.merged_output["impure"]


class TestEscalationStrategy:
    """Tests for escalation strategy."""
    
    @pytest.fixture
    def resolver(self):
        return ConflictResolver(ConflictResolutionStrategy.ESCALATE)
    
    def test_all_conflicts_escalate(self, resolver):
        """Test that all conflicts are escalated regardless of votes."""
        outputs = [
            {"pure": [], "impure": ["item"]},
            {"pure": [], "impure": ["item"]},
            {"pure": ["item"], "impure": []},
        ]
        
        result = resolver.resolve(outputs, ["pure", "impure"])
        
        # Even with 2-1 majority, should escalate
        assert "item" in result.items_requiring_review


class TestResolutionResult:
    """Tests for ResolutionResult functionality."""
    
    def test_empty_outputs(self):
        """Test handling of empty outputs list."""
        resolver = ConflictResolver()
        result = resolver.resolve([], ["pure", "impure"])
        
        assert result.merged_output == {"pure": [], "impure": []}
        assert len(result.conflicts) == 0
        assert not result.has_unresolved_conflicts
    
    def test_statistics(self):
        """Test that statistics are calculated correctly."""
        resolver = ConflictResolver()
        outputs = [
            {"pure": ["a", "b"], "impure": ["c"]},
            {"pure": ["a"], "impure": ["b", "c"]},  # Conflict on 'b'
        ]
        
        result = resolver.resolve(outputs, ["pure", "impure"])
        
        assert result.resolution_stats["total_items"] == 3  # a, b, c
        assert result.resolution_stats["conflicts"] == 1   # just 'b'
    
    def test_to_dict(self):
        """Test serialization to dict."""
        resolver = ConflictResolver()
        outputs = [
            {"pure": ["add"], "impure": []},
            {"pure": ["add"], "impure": []},
        ]
        
        result = resolver.resolve(outputs, ["pure", "impure"])
        d = result.to_dict()
        
        assert "merged_output" in d
        assert "conflicts" in d
        assert "items_requiring_review" in d
        assert "resolution_stats" in d


class TestConflictReport:
    """Tests for ConflictReport dataclass."""
    
    def test_to_dict(self):
        """Test ConflictReport serialization."""
        report = ConflictReport(
            item="test_item",
            votes={"pure": 1, "impure": 2},
            resolution="impure",
            confidence=0.67,
            requires_human_review=False,
            justification="Majority vote"
        )
        
        d = report.to_dict()
        
        assert d["item"] == "test_item"
        assert d["votes"] == {"pure": 1, "impure": 2}
        assert d["resolution"] == "impure"
        assert d["confidence"] == 0.67


class TestSingleConflictResolution:
    """Tests for resolving individual conflicts."""
    
    def test_with_human_override(self):
        """Test that human override takes precedence."""
        resolver = ConflictResolver()
        
        report = resolver.resolve_single_conflict(
            item="test",
            worker_votes={"w1": "pure", "w2": "impure"},
            human_override="pure"
        )
        
        assert report.resolution == "pure"
        assert report.confidence == 1.0
        assert not report.requires_human_review
    
    def test_without_human_override_majority(self):
        """Test majority vote without override."""
        resolver = ConflictResolver()
        
        report = resolver.resolve_single_conflict(
            item="test",
            worker_votes={"w1": "pure", "w2": "pure", "w3": "impure"}
        )
        
        assert report.resolution == "pure"
        assert report.confidence == pytest.approx(2/3)
    
    def test_without_human_override_tie(self):
        """Test tie without override escalates."""
        resolver = ConflictResolver()
        
        report = resolver.resolve_single_conflict(
            item="test",
            worker_votes={"w1": "pure", "w2": "impure"}
        )
        
        assert report.resolution == "escalate"
        assert report.requires_human_review
