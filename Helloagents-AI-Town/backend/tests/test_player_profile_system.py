"""Focused checks for the v1 player profile system.

Run with:
    python Helloagents-AI-Town/backend/tests/test_player_profile_system.py
"""

from __future__ import annotations

from datetime import datetime
import os
import sys
import tempfile


BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BACKEND_DIR)

from player_profile_manager import PlayerProfileManager
from agents import NPCAgentManager


def make_manager(tmp_dir: str) -> PlayerProfileManager:
    return PlayerProfileManager(db_path=os.path.join(tmp_dir, "profiles.db"))


def test_profile_topics_persist_across_manager_instances() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = make_manager(tmp_dir)

        manager.record_chat_message(
            player_id="player",
            npc_name="张三",
            message="我最近一直在学 Python, 还在调试 Flask 报错。",
            occurred_at=datetime(2026, 6, 20, 20, 0, 0),
        )
        manager.record_chat_message(
            player_id="player",
            npc_name="张三",
            message="这个 Python bug 又卡住了, 能聊聊日志和断点吗?",
            occurred_at=datetime(2026, 6, 20, 21, 0, 0),
        )

        reloaded = make_manager(tmp_dir)
        profile = reloaded.get_profile("player")
        tags = {item["tag"]: item for item in profile["items"]}

        assert tags["programming/python"]["confidence"] >= 0.6
        assert tags["programming/python"]["evidence_count"] == 2
        assert tags["programming/python"]["source_counts"]["张三"] == 2
        assert tags["programming/debugging"]["confidence"] >= 0.6


def test_player_correction_rejects_item_and_blocks_prompt_context() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = make_manager(tmp_dir)
        for index in range(3):
            manager.record_chat_message(
                player_id="player",
                npc_name="张三",
                message=f"我想继续聊 Python 调试和 bug 日志 {index}",
                occurred_at=datetime(2026, 6, 20, 20, index, 0),
            )

        before = manager.build_prompt_context("player", "张三")
        assert "Python" in before

        manager.record_chat_message(
            player_id="player",
            npc_name="张三",
            message="我其实不喜欢 Python, 以后别老提这个。",
            occurred_at=datetime(2026, 6, 20, 21, 0, 0),
        )

        profile = manager.get_profile("player")
        python_item = next(item for item in profile["items"] if item["tag"] == "programming/python")
        after = manager.build_prompt_context("player", "张三")

        assert python_item["status"] == "rejected"
        assert "Python" not in after


def test_prompt_context_is_role_aware_and_limited() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = make_manager(tmp_dir)
        for index in range(3):
            manager.record_chat_message(
                player_id="player",
                npc_name="张三",
                message=f"Python 调试 bug 日志 traceback {index}",
                occurred_at=datetime(2026, 6, 20, 19, index, 0),
            )
            manager.record_chat_message(
                player_id="player",
                npc_name="王五",
                message=f"我想看看界面 UI 颜色 按钮 布局 {index}",
                occurred_at=datetime(2026, 6, 20, 20, index, 0),
            )

        zhang_context = manager.build_prompt_context("player", "张三")
        wang_context = manager.build_prompt_context("player", "王五")

        assert "Python" in zhang_context
        assert "颜色" not in zhang_context
        assert "颜色" in wang_context
        assert zhang_context.count("- ") <= 4
        assert wang_context.count("- ") <= 4


def test_evening_time_habit_requires_repeated_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = make_manager(tmp_dir)

        for index in range(4):
            manager.record_chat_message(
                player_id="player",
                npc_name="李四",
                message=f"普通聊天 {index}",
                occurred_at=datetime(2026, 6, 20, 20, index, 0),
            )
        assert not manager.get_profile("player")["time_habits"]

        manager.record_chat_message(
            player_id="player",
            npc_name="李四",
            message="晚上再聊一下产品反馈",
            occurred_at=datetime(2026, 6, 20, 21, 0, 0),
        )

        profile = manager.get_profile("player")
        habit = profile["time_habits"][0]

        assert habit["bucket"] == "evening"
        assert habit["confidence"] >= 0.6
        assert "晚上活跃" in manager.build_prompt_context("player", "李四")


def test_status_update_and_clear_profile() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = make_manager(tmp_dir)
        for index in range(3):
            manager.record_chat_message(
                player_id="player",
                npc_name="李四",
                message=f"我最近在找工作, 也想了解产品经理怎么收集用户反馈 {index}",
                occurred_at=datetime(2026, 6, 20, 15, index, 0),
            )

        item = manager.get_profile("player")["items"][0]
        updated = manager.update_item_status("player", item["id"], "suppressed")
        profile_after_update = manager.get_profile("player")
        updated_item = next(entry for entry in profile_after_update["items"] if entry["id"] == item["id"])

        assert updated["status"] == "suppressed"
        assert updated_item["status"] == "suppressed"

        cleared = manager.clear_profile("player")

        assert cleared["deleted_items"] > 0
        assert manager.get_profile("player")["items"] == []


def test_profile_update_failure_does_not_block_simulated_chat() -> None:
    class FailingProfileManager:
        def record_chat_message(self, **kwargs):
            raise RuntimeError("profile db unavailable")

    manager = NPCAgentManager.__new__(NPCAgentManager)
    manager.agents = {"张三": None}
    manager.memories = {}
    manager.relationship_manager = None
    manager.player_profile_manager = FailingProfileManager()

    result = manager.chat_with_events("张三", "我想聊 Python", "player")

    assert result["message"].startswith("你好!我是张三")
    assert result["task_events"] == []


def main() -> None:
    tests = [
        test_profile_topics_persist_across_manager_instances,
        test_player_correction_rejects_item_and_blocks_prompt_context,
        test_prompt_context_is_role_aware_and_limited,
        test_evening_time_habit_requires_repeated_evidence,
        test_status_update_and_clear_profile,
        test_profile_update_failure_does_not_block_simulated_chat,
    ]
    for test in tests:
        test()
    print(f"player profile system checks passed: {len(tests)}")


if __name__ == "__main__":
    main()
