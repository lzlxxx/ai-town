"""Focused checks for the v1 NPC emotion system.

Run with:
    python Helloagents-AI-Town/backend/tests/test_emotion_system.py
"""

from __future__ import annotations

import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BACKEND_DIR)

from relationship_manager import RelationshipManager


def make_manager() -> RelationshipManager:
    manager = RelationshipManager.__new__(RelationshipManager)
    manager.affinity_scores = {}
    manager.emotion_states = {}
    manager.emotion_history = {}
    return manager


def test_default_emotion_state_has_values_and_summary() -> None:
    manager = make_manager()

    emotion = manager.get_emotion_state("张三", "player")

    assert set(emotion["values"]) == {"joy", "sadness", "anger", "excitement"}
    assert emotion["dominant"] in {"joy", "sadness", "anger", "excitement", "neutral"}
    assert emotion["label"]
    assert emotion["level"] in {"low", "medium", "high"}
    assert 0 <= emotion["intensity"] <= 100


def test_parse_analysis_includes_emotion_deltas() -> None:
    manager = make_manager()
    response = """
    {"should_change": true, "change_amount": 3, "reason": "受到鼓励",
     "sentiment": "positive",
     "emotion_deltas": {"joy": 10, "sadness": -2, "anger": -4, "excitement": 6}}
    """

    analysis = manager._parse_analysis(response)

    assert analysis["should_change"] is True
    assert analysis["change_amount"] == 3
    assert analysis["emotion_deltas"]["joy"] == 10
    assert analysis["emotion_deltas"]["anger"] == -4


def test_apply_analysis_updates_emotion_and_affinity() -> None:
    manager = make_manager()
    before = manager.get_emotion_state("张三", "player")

    result = manager._apply_analysis(
        "张三",
        "player",
        {
            "should_change": True,
            "change_amount": 3,
            "reason": "积极鼓励",
            "sentiment": "positive",
            "emotion_deltas": {
                "joy": 12,
                "sadness": -2,
                "anger": -5,
                "excitement": 4,
            },
        },
    )

    after = result["emotion"]
    assert result["changed"] is True
    assert result["new_affinity"] > result["old_affinity"]
    assert after["values"]["joy"] > before["values"]["joy"]
    assert after["dominant"] in {"joy", "excitement"}
    assert len(manager.get_emotion_history("张三", "player")) == 1


def test_rule_fallback_classifies_angry_message() -> None:
    manager = make_manager()

    analysis = manager._build_rule_analysis(
        player_message="你这个方案太烂了,真让人讨厌",
        npc_response="我有点不舒服,先不展开了。",
        reason="分析失败",
    )

    assert analysis["should_change"] is True
    assert analysis["change_amount"] < 0
    assert analysis["emotion_deltas"]["anger"] > 0
    assert analysis["emotion_deltas"]["joy"] < 0


def test_emotion_history_is_bounded() -> None:
    manager = make_manager()

    for index in range(20):
        manager._update_emotion_state(
            "李四",
            "player",
            {"joy": index, "sadness": 0, "anger": 0, "excitement": 0},
            "测试",
        )

    assert len(manager.get_emotion_history("李四", "player")) == manager.EMOTION_HISTORY_LIMIT


def main() -> None:
    tests = [
        test_default_emotion_state_has_values_and_summary,
        test_parse_analysis_includes_emotion_deltas,
        test_apply_analysis_updates_emotion_and_affinity,
        test_rule_fallback_classifies_angry_message,
        test_emotion_history_is_bounded,
    ]
    for test in tests:
        test()
    print(f"emotion system checks passed: {len(tests)}")


if __name__ == "__main__":
    main()
