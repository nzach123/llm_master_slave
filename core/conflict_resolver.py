"""
Conflict Resolver Module.

Detects and resolves conflicts when multiple workers produce
conflicting outputs. This addresses ISSUE-001: No Conflict Resolution Policy.

Key features:
- Detects items classified differently by different workers
- Applies majority vote for clear majorities
- Escalates ties for human review
- Logs all conflicts with justifications
"""

import logging
from typing import Dict, Any, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class ConflictResolutionStrategy(str, Enum):
    """Available strategies for resolving conflicts."""
    MAJORITY_VOTE = "majority_vote"
    FIRST_RESPONDER = "first_responder"
    ESCALATE = "escalate"
    UNANIMOUS_ONLY = "unanimous_only"


@dataclass
class ConflictReport:
    """
    Report of a single conflict between workers.
    
    Attributes:
        item: The item that has conflicting classifications
        votes: Mapping of classification -> vote count
        resolution: The resolved classification (or "escalate")
        confidence: Confidence score (0.0 - 1.0)
        requires_human_review: Whether this needs human attention
        justification: Explanation of the resolution
    """
    item: str
    votes: Dict[str, int]
    resolution: str
    confidence: float
    requires_human_review: bool
    justification: str = ""
    
    def to_dict(self) -> dict:
        return {
            "item": self.item,
            "votes": self.votes,
            "resolution": self.resolution,
            "confidence": self.confidence,
            "requires_human_review": self.requires_human_review,
            "justification": self.justification
        }


@dataclass 
class ResolutionResult:
    """
    Result of conflict resolution process.
    
    Attributes:
        merged_output: The merged output with conflicts resolved
        conflicts: List of all conflicts detected and how they were resolved
        items_requiring_review: Items that need human review
        resolution_stats: Statistics about the resolution process
    """
    merged_output: Dict[str, List[str]]
    conflicts: List[ConflictReport]
    items_requiring_review: List[str]
    resolution_stats: Dict[str, int]
    
    @property
    def has_unresolved_conflicts(self) -> bool:
        return len(self.items_requiring_review) > 0
    
    def to_dict(self) -> dict:
        return {
            "merged_output": self.merged_output,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "items_requiring_review": self.items_requiring_review,
            "resolution_stats": self.resolution_stats
        }


class ConflictResolver:
    """
    Detects and resolves conflicts in multi-worker outputs.
    
    When multiple workers classify the same items, conflicts can occur
    (e.g., Worker 1 says "pure", Worker 2 says "impure"). This class
    detects these conflicts and applies a resolution strategy.
    
    Usage:
        resolver = ConflictResolver(ConflictResolutionStrategy.MAJORITY_VOTE)
        
        worker_outputs = [
            {"pure": ["add"], "impure": ["append_item"]},
            {"pure": ["add", "append_item"], "impure": []},
        ]
        
        result = resolver.resolve(worker_outputs, ["pure", "impure"])
        
        if result.has_unresolved_conflicts:
            escalate_to_human(result.items_requiring_review)
    """
    
    def __init__(
        self, 
        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.MAJORITY_VOTE,
        require_justification: bool = True
    ):
        self.strategy = strategy
        self.require_justification = require_justification
        self.logger = logging.getLogger(__name__)
    
    def detect_conflicts(
        self, 
        worker_outputs: List[Dict[str, Any]], 
        classification_keys: List[str]
    ) -> List[ConflictReport]:
        """
        Detect items that appear in conflicting categories across workers.
        
        Args:
            worker_outputs: List of output dicts from workers
            classification_keys: Keys that contain classifications (e.g., ["pure", "impure"])
            
        Returns:
            List of ConflictReport for each conflicted item
        """
        # Build item -> {category -> vote_count} mapping
        item_classifications: Dict[str, Dict[str, int]] = {}
        
        for output in worker_outputs:
            for key in classification_keys:
                items = output.get(key, [])
                if not isinstance(items, list):
                    items = [items] if items else []
                    
                for item in items:
                    if item not in item_classifications:
                        item_classifications[item] = {k: 0 for k in classification_keys}
                    item_classifications[item][key] = item_classifications[item].get(key, 0) + 1
        
        # Find conflicts (items appearing in multiple categories)
        conflicts = []
        
        for item, votes in item_classifications.items():
            # Filter out zero-vote categories
            non_zero_votes = {k: v for k, v in votes.items() if v > 0}
            
            if len(non_zero_votes) > 1:
                # This item has conflicting votes
                total_votes = sum(non_zero_votes.values())
                max_category = max(non_zero_votes, key=non_zero_votes.get)
                max_votes = non_zero_votes[max_category]
                confidence = max_votes / total_votes
                
                # Determine resolution based on strategy
                if self.strategy == ConflictResolutionStrategy.MAJORITY_VOTE:
                    if confidence > 0.5:
                        resolution = max_category
                        requires_review = False
                        justification = f"Majority vote: {max_votes}/{total_votes} ({confidence:.0%})"
                    else:
                        resolution = "escalate"
                        requires_review = True
                        justification = f"No majority: votes split {non_zero_votes}"
                        
                elif self.strategy == ConflictResolutionStrategy.ESCALATE:
                    resolution = "escalate"
                    requires_review = True
                    justification = f"All conflicts escalated per policy. Votes: {non_zero_votes}"
                    
                elif self.strategy == ConflictResolutionStrategy.FIRST_RESPONDER:
                    # Use the first worker's classification
                    first_class = None
                    for key in classification_keys:
                        if worker_outputs[0].get(key) and item in worker_outputs[0][key]:
                            first_class = key
                            break
                    resolution = first_class or "escalate"
                    requires_review = first_class is None
                    justification = f"First responder rule: used Worker 0's classification"
                    
                elif self.strategy == ConflictResolutionStrategy.UNANIMOUS_ONLY:
                    resolution = "escalate"
                    requires_review = True
                    justification = f"Unanimous agreement required. Votes: {non_zero_votes}"
                
                else:
                    resolution = "escalate"
                    requires_review = True
                    justification = "Unknown strategy"
                
                conflicts.append(ConflictReport(
                    item=item,
                    votes=non_zero_votes,
                    resolution=resolution,
                    confidence=confidence,
                    requires_human_review=requires_review,
                    justification=justification
                ))
                
                # Log the conflict
                log_level = logging.WARNING if requires_review else logging.INFO
                self.logger.log(
                    log_level,
                    f"Conflict detected: '{item}' - {non_zero_votes} -> {resolution} ({justification})"
                )
        
        return conflicts
    
    def resolve(
        self, 
        worker_outputs: List[Dict[str, Any]], 
        classification_keys: List[str]
    ) -> ResolutionResult:
        """
        Resolve conflicts and produce merged output.
        
        Args:
            worker_outputs: List of output dicts from workers
            classification_keys: Keys that contain classifications
            
        Returns:
            ResolutionResult with merged output and conflict reports
        """
        if not worker_outputs:
            return ResolutionResult(
                merged_output={k: [] for k in classification_keys},
                conflicts=[],
                items_requiring_review=[],
                resolution_stats={"total_items": 0, "conflicts": 0, "auto_resolved": 0, "escalated": 0}
            )
        
        # Detect all conflicts
        conflicts = self.detect_conflicts(worker_outputs, classification_keys)
        conflict_items = {c.item for c in conflicts}
        
        # Build merged output
        # Start with unanimous items (appear in same category for all workers)
        merged: Dict[str, Set[str]] = {key: set() for key in classification_keys}
        
        # Collect all items and their classifications
        all_items: Dict[str, Set[str]] = {}  # item -> set of categories it appears in
        
        for output in worker_outputs:
            for key in classification_keys:
                items = output.get(key, [])
                if not isinstance(items, list):
                    items = [items] if items else []
                for item in items:
                    if item not in all_items:
                        all_items[item] = set()
                    all_items[item].add(key)
        
        # Process non-conflicted items (appear in only one category)
        for item, categories in all_items.items():
            if item not in conflict_items:
                # No conflict - add to the category
                for cat in categories:
                    merged[cat].add(item)
        
        # Apply conflict resolutions
        items_requiring_review = []
        auto_resolved = 0
        
        for conflict in conflicts:
            if conflict.requires_human_review:
                items_requiring_review.append(conflict.item)
            else:
                merged[conflict.resolution].add(conflict.item)
                auto_resolved += 1
        
        # Build result
        return ResolutionResult(
            merged_output={k: sorted(list(v)) for k, v in merged.items()},
            conflicts=conflicts,
            items_requiring_review=items_requiring_review,
            resolution_stats={
                "total_items": len(all_items),
                "conflicts": len(conflicts),
                "auto_resolved": auto_resolved,
                "escalated": len(items_requiring_review)
            }
        )
    
    def resolve_single_conflict(
        self,
        item: str,
        worker_votes: Dict[str, str],  # worker_id -> classification
        human_override: Optional[str] = None
    ) -> ConflictReport:
        """
        Resolve a single item's conflict with optional human override.
        
        Args:
            item: The conflicted item
            worker_votes: Mapping of worker ID to their classification
            human_override: Optional human-provided resolution
            
        Returns:
            ConflictReport for this item
        """
        # Count votes
        vote_counts: Dict[str, int] = {}
        for classification in worker_votes.values():
            vote_counts[classification] = vote_counts.get(classification, 0) + 1
        
        if human_override:
            return ConflictReport(
                item=item,
                votes=vote_counts,
                resolution=human_override,
                confidence=1.0,
                requires_human_review=False,
                justification=f"Human override applied"
            )
        
        total = sum(vote_counts.values())
        max_class = max(vote_counts, key=vote_counts.get)
        max_votes = vote_counts[max_class]
        confidence = max_votes / total
        
        if confidence > 0.5:
            return ConflictReport(
                item=item,
                votes=vote_counts,
                resolution=max_class,
                confidence=confidence,
                requires_human_review=False,
                justification=f"Majority vote: {max_votes}/{total}"
            )
        else:
            return ConflictReport(
                item=item,
                votes=vote_counts,
                resolution="escalate",
                confidence=confidence,
                requires_human_review=True,
                justification=f"No majority - tie at {confidence:.0%}"
            )
