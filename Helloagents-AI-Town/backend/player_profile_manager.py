"""Persistent player profile learning for CyberTown."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
import re
import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Sequence


PROFILE_ACTIVE = "active"
PROFILE_SUPPRESSED = "suppressed"
PROFILE_STALE = "stale"
PROFILE_REJECTED = "rejected"
VALID_PROFILE_STATUSES = {
    PROFILE_ACTIVE,
    PROFILE_SUPPRESSED,
    PROFILE_STALE,
    PROFILE_REJECTED,
}

DEFAULT_PROFILE_DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "profile_data",
    "player_profiles.db",
)


@dataclass(frozen=True)
class TopicRule:
    category: str
    tag: str
    label: str
    keywords: Sequence[str]


TOPIC_RULES: Sequence[TopicRule] = (
    TopicRule(
        category="programming",
        tag="programming/python",
        label="Python",
        keywords=("python", "py", "flask", "django"),
    ),
    TopicRule(
        category="programming",
        tag="programming/debugging",
        label="调试",
        keywords=(
            "调试", "报错", "bug", "日志", "断点", "debug",
            "error", "traceback", "log", "异常", "堆栈",
        ),
    ),
    TopicRule(
        category="design",
        tag="design/color",
        label="颜色",
        keywords=("颜色", "配色", "color", "palette"),
    ),
    TopicRule(
        category="design",
        tag="design/ui_feedback",
        label="界面体验",
        keywords=(
            "设计", "界面", "ui", "按钮", "布局", "交互", "字体",
            "间距", "视觉", "可用性", "design", "button", "layout",
            "usability",
        ),
    ),
    TopicRule(
        category="product",
        tag="product/user_feedback",
        label="用户反馈",
        keywords=(
            "用户反馈", "反馈", "需求", "用户需求", "产品", "prd",
            "竞品", "product", "feedback", "requirement",
        ),
    ),
    TopicRule(
        category="career",
        tag="career/job_search",
        label="找工作",
        keywords=("找工作", "求职", "面试", "简历", "job", "interview", "resume", "offer"),
    ),
    TopicRule(
        category="gameplay",
        tag="gameplay/gaming",
        label="游戏",
        keywords=("游戏", "打游戏", "game", "gaming"),
    ),
)

LABELS: Dict[str, str] = {
    "programming/python": "Python",
    "programming/debugging": "调试",
    "design/color": "颜色",
    "design/ui_feedback": "界面体验",
    "product/user_feedback": "用户反馈",
    "career/job_search": "找工作",
    "gameplay/gaming": "游戏",
    "social/friendly_interaction": "友好互动",
    "time/morning": "早上活跃",
    "time/afternoon": "下午活跃",
    "time/evening": "晚上活跃",
    "time/late_night": "深夜活跃",
}

NPC_RELEVANT_CATEGORIES: Dict[str, set[str]] = {
    "张三": {"programming", "gameplay", "social"},
    "李四": {"product", "career", "social", "gameplay"},
    "王五": {"design", "product", "social"},
}

EXPLICIT_INTEREST_MARKERS = (
    "喜欢", "感兴趣", "一直", "经常", "常", "最近在学", "学习", "在学",
    "想继续", "关注", "love", "like", "interested", "often", "usually",
    "learning",
)
STRONG_REJECTION_MARKERS = (
    "不喜欢", "没兴趣", "不感兴趣", "讨厌", "别说我喜欢", "do not like",
    "don't like", "not interested", "hate",
)
SUPPRESS_MARKERS = (
    "别老提", "不要再提", "别提", "不想聊", "少提", "stop mentioning",
    "do not mention", "don't mention",
)


class PlayerProfileManager:
    """Manage persistent per-player preference and habit profiles."""

    MIN_PROMPT_CONFIDENCE = 0.6
    STRONG_CONFIDENCE = 0.8
    TIME_HABIT_MIN_COUNT = 5
    TIME_HABIT_MIN_RATIO = 0.45
    MENTION_COOLDOWN_CONVERSATIONS = 3

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("PLAYER_PROFILE_DB_PATH") or DEFAULT_PROFILE_DB_PATH
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def record_chat_message(
        self,
        player_id: str,
        npc_name: str,
        message: str,
        occurred_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        occurred_at = occurred_at or datetime.now()
        occurred_at_text = occurred_at.isoformat()
        self._record_event(
            player_id=player_id,
            event_type="chat_interaction",
            npc_name=npc_name,
            category="meta",
            tag="meta/chat",
            weight=0.0,
            occurred_at=occurred_at_text,
            evidence_summary=f"玩家和{npc_name}发生一次互动",
        )

        signals = self.extract_topic_signals(message, occurred_at)
        corrections = self.extract_corrections(message)
        updated_items: List[Dict[str, Any]] = []

        correction_tags = {entry["tag"]: entry for entry in corrections}
        signal_tags = {signal["tag"] for signal in signals}

        for signal in signals:
            correction = correction_tags.get(signal["tag"])
            if correction:
                updated_items.append(
                    self._apply_correction(
                        player_id=player_id,
                        npc_name=npc_name,
                        signal=signal,
                        status=correction["status"],
                        occurred_at=occurred_at_text,
                    )
                )
                continue

            updated_items.append(
                self._apply_signal(
                    player_id=player_id,
                    npc_name=npc_name,
                    signal=signal,
                    event_type="chat_topic_detected",
                    occurred_at=occurred_at_text,
                )
            )

        for correction in corrections:
            if correction["tag"] in signal_tags:
                continue
            signal = {
                "category": correction["category"],
                "tag": correction["tag"],
                "label": correction["label"],
                "weight": 0.0,
                "evidence_summary": f"玩家纠正了{correction['label']}相关画像",
            }
            updated_items.append(
                self._apply_correction(
                    player_id=player_id,
                    npc_name=npc_name,
                    signal=signal,
                    status=correction["status"],
                    occurred_at=occurred_at_text,
                )
            )

        time_habit = self._record_time_habit(player_id, npc_name, occurred_at)

        return {
            "signals": signals,
            "corrections": corrections,
            "updated_items": updated_items,
            "time_habit": time_habit,
        }

    def record_task_events(
        self,
        player_id: str,
        npc_name: str,
        task_events: Sequence[Dict[str, Any]],
        occurred_at: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        occurred_at = occurred_at or datetime.now()
        occurred_at_text = occurred_at.isoformat()
        updated: List[Dict[str, Any]] = []

        for event in task_events:
            event_type = str(event.get("event_type", "task_event"))
            text = " ".join(
                str(event.get(key, ""))
                for key in ("title", "message", "task_id", "npc_name")
            )
            for signal in self.extract_topic_signals(text, occurred_at):
                signal = dict(signal)
                signal["weight"] = max(float(signal["weight"]), 0.20)
                signal["evidence_summary"] = f"玩家触发了{signal['label']}相关任务事件"
                updated.append(
                    self._apply_signal(
                        player_id=player_id,
                        npc_name=npc_name,
                        signal=signal,
                        event_type=f"task_{event_type}",
                        occurred_at=occurred_at_text,
                    )
                )

        return updated

    def record_relationship_event(
        self,
        player_id: str,
        npc_name: str,
        affinity_result: Optional[Dict[str, Any]],
        occurred_at: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        if not affinity_result or not affinity_result.get("changed"):
            return None
        if affinity_result.get("sentiment") != "positive":
            return None

        occurred_at = occurred_at or datetime.now()
        signal = {
            "category": "social",
            "tag": "social/friendly_interaction",
            "label": label_for_tag("social/friendly_interaction"),
            "weight": 0.20,
            "evidence_summary": f"玩家和{npc_name}出现了积极互动",
        }
        return self._apply_signal(
            player_id=player_id,
            npc_name=npc_name,
            signal=signal,
            event_type="affinity_changed",
            occurred_at=occurred_at.isoformat(),
        )

    def extract_topic_signals(
        self,
        message: str,
        occurred_at: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        text = normalize_text(message)
        if not text:
            return []

        explicit = any(marker in text for marker in EXPLICIT_INTEREST_MARKERS)
        recent_bonus = 0.10 if self._is_recent(occurred_at or datetime.now()) else 0.0
        signals: List[Dict[str, Any]] = []

        for rule in TOPIC_RULES:
            if not any(contains_keyword(text, keyword) for keyword in rule.keywords):
                continue
            weight = 0.15 + recent_bonus
            if explicit:
                weight += 0.30
            signals.append({
                "category": rule.category,
                "tag": rule.tag,
                "label": rule.label,
                "weight": round(min(weight, 1.0), 2),
                "evidence_summary": f"玩家提到{rule.label}相关话题",
            })

        return signals

    def extract_corrections(self, message: str) -> List[Dict[str, Any]]:
        text = normalize_text(message)
        if not text:
            return []

        has_rejection = any(marker in text for marker in STRONG_REJECTION_MARKERS)
        has_suppression = any(marker in text for marker in SUPPRESS_MARKERS)
        if not has_rejection and not has_suppression:
            return []

        status = PROFILE_REJECTED if has_rejection else PROFILE_SUPPRESSED
        corrections: List[Dict[str, Any]] = []
        for rule in TOPIC_RULES:
            if any(contains_keyword(text, keyword) for keyword in rule.keywords):
                corrections.append({
                    "category": rule.category,
                    "tag": rule.tag,
                    "label": rule.label,
                    "status": status,
                })

        if not corrections and ("晚上" in text or "夜里" in text or "evening" in text or "night" in text):
            corrections.append({
                "category": "time",
                "tag": "time/evening",
                "label": label_for_tag("time/evening"),
                "status": PROFILE_SUPPRESSED,
            })

        return corrections

    def build_prompt_context(
        self,
        player_id: str,
        npc_name: str,
        current_message: str = "",
        mark_mentioned: bool = True,
    ) -> str:
        current_signals = self.extract_topic_signals(current_message)
        current_tags = {signal["tag"] for signal in current_signals}
        current_labels = [signal["label"] for signal in current_signals]

        interests = self._prompt_interest_items(player_id, npc_name, current_tags)
        time_habit = self._prompt_time_habit(player_id)
        lines: List[str] = []

        if interests or time_habit:
            lines.append("【玩家画像】")
            for item in interests[:3]:
                confidence = int(round(item["confidence"] * 100))
                lines.append(f"- 玩家稳定关注{item['label']} (置信度 {confidence}%)。")
            if time_habit:
                lines.append(f"- 玩家通常{time_habit['label']}, 回复时可以轻松但不要打扰。")

        if current_labels:
            labels = "、".join(current_labels[:3])
            if lines:
                lines.append("")
            lines.append("【本轮兴趣线索】")
            lines.append(f"玩家本轮提到{labels}, 可以自然接话, 不要当成长期偏好反复强调。")

        if mark_mentioned and interests:
            mentioned_ids = [
                item["id"]
                for item in interests[:3]
                if item["tag"] not in current_tags
            ]
            if mentioned_ids:
                self._mark_items_mentioned(player_id, npc_name, mentioned_ids)
            if time_habit:
                self._mark_items_mentioned(player_id, npc_name, [time_habit["id"]])

        if not lines:
            return ""
        return "\n".join(lines) + "\n\n"

    def get_profile(self, player_id: str) -> Dict[str, Any]:
        rows = self._fetch_items(player_id)
        items = [self._row_to_item(row) for row in rows if row["category"] != "time"]
        time_habits = [
            self._row_to_time_habit(row)
            for row in rows
            if row["category"] == "time"
            and row["status"] == PROFILE_ACTIVE
            and float(row["confidence"]) >= self.MIN_PROMPT_CONFIDENCE
            and int(row["evidence_count"]) >= self.TIME_HABIT_MIN_COUNT
        ]
        return {
            "player_id": player_id,
            "items": items,
            "time_habits": time_habits,
            "summary": self._build_summary(items, time_habits),
        }

    def update_item_status(self, player_id: str, item_id: int, status: str) -> Dict[str, Any]:
        if status not in VALID_PROFILE_STATUSES:
            raise ValueError(f"画像状态无效: {status}")

        now = datetime.now().isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM profile_items WHERE id = ? AND player_id = ?",
                (item_id, player_id),
            ).fetchone()
            if row is None:
                raise KeyError(f"画像项不存在: {item_id}")

            conn.execute(
                """
                UPDATE profile_items
                SET status = ?, updated_at = ?
                WHERE id = ? AND player_id = ?
                """,
                (status, now, item_id, player_id),
            )

        return self.get_item(player_id, item_id)

    def get_item(self, player_id: str, item_id: int) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM profile_items WHERE id = ? AND player_id = ?",
                (item_id, player_id),
            ).fetchone()
        if row is None:
            raise KeyError(f"画像项不存在: {item_id}")
        if row["category"] == "time":
            return self._row_to_time_habit(row)
        return self._row_to_item(row)

    def clear_profile(self, player_id: str) -> Dict[str, int]:
        with self._connect() as conn:
            item_count = conn.execute(
                "SELECT COUNT(*) FROM profile_items WHERE player_id = ?",
                (player_id,),
            ).fetchone()[0]
            event_count = conn.execute(
                "SELECT COUNT(*) FROM profile_events WHERE player_id = ?",
                (player_id,),
            ).fetchone()[0]
            conn.execute("DELETE FROM profile_items WHERE player_id = ?", (player_id,))
            conn.execute("DELETE FROM profile_events WHERE player_id = ?", (player_id,))
        return {
            "deleted_items": int(item_count),
            "deleted_events": int(event_count),
        }

    def _apply_signal(
        self,
        player_id: str,
        npc_name: str,
        signal: Dict[str, Any],
        event_type: str,
        occurred_at: str,
    ) -> Dict[str, Any]:
        self._record_event(
            player_id=player_id,
            event_type=event_type,
            npc_name=npc_name,
            category=signal["category"],
            tag=signal["tag"],
            weight=float(signal["weight"]),
            occurred_at=occurred_at,
            evidence_summary=signal["evidence_summary"],
        )
        return self._upsert_item(
            player_id=player_id,
            npc_name=npc_name,
            category=signal["category"],
            tag=signal["tag"],
            label=signal.get("label") or label_for_tag(signal["tag"]),
            weight=float(signal["weight"]),
            evidence_summary=signal["evidence_summary"],
            occurred_at=occurred_at,
        )

    def _apply_correction(
        self,
        player_id: str,
        npc_name: str,
        signal: Dict[str, Any],
        status: str,
        occurred_at: str,
    ) -> Dict[str, Any]:
        self._record_event(
            player_id=player_id,
            event_type="profile_correction",
            npc_name=npc_name,
            category=signal["category"],
            tag=signal["tag"],
            weight=0.0,
            occurred_at=occurred_at,
            evidence_summary=f"玩家纠正了{signal['label']}相关画像",
        )
        item = self._upsert_item(
            player_id=player_id,
            npc_name=npc_name,
            category=signal["category"],
            tag=signal["tag"],
            label=signal.get("label") or label_for_tag(signal["tag"]),
            weight=0.0,
            evidence_summary=f"玩家纠正了{signal['label']}相关画像",
            occurred_at=occurred_at,
            forced_status=status,
        )
        return item

    def _upsert_item(
        self,
        player_id: str,
        npc_name: str,
        category: str,
        tag: str,
        label: str,
        weight: float,
        evidence_summary: str,
        occurred_at: str,
        forced_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM profile_items WHERE player_id = ? AND tag = ?",
                (player_id, tag),
            ).fetchone()

            if row is None:
                source_counts = {npc_name: 1} if npc_name else {}
                status = forced_status or PROFILE_ACTIVE
                confidence = self._clamp_confidence(weight)
                conn.execute(
                    """
                    INSERT INTO profile_items (
                        player_id, category, tag, label, confidence, evidence_count,
                        source_npcs, source_counts, status, evidence_summary,
                        last_seen_at, mention_count, last_mentioned_event_count, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, 0, 0, ?)
                    """,
                    (
                        player_id,
                        category,
                        tag,
                        label,
                        confidence,
                        json_dumps(sorted(source_counts)),
                        json_dumps(source_counts),
                        status,
                        evidence_summary,
                        occurred_at,
                        occurred_at,
                    ),
                )
            else:
                source_counts = json_loads(row["source_counts"], {})
                sources_before = set(source_counts)
                if npc_name:
                    source_counts[npc_name] = int(source_counts.get(npc_name, 0)) + 1
                cross_npc_bonus = 0.15 if npc_name and sources_before and npc_name not in sources_before else 0.0
                confidence = self._clamp_confidence(
                    float(row["confidence"]) + weight + cross_npc_bonus
                )
                status = forced_status or row["status"]
                if row["status"] == PROFILE_REJECTED and forced_status is None:
                    status = PROFILE_REJECTED
                if row["status"] == PROFILE_SUPPRESSED and forced_status is None:
                    status = PROFILE_SUPPRESSED
                if row["status"] == PROFILE_STALE and confidence >= self.MIN_PROMPT_CONFIDENCE:
                    status = PROFILE_ACTIVE

                evidence_count = int(row["evidence_count"]) + 1
                summary = self._merge_evidence_summary(
                    label=label,
                    source_counts=source_counts,
                    evidence_count=evidence_count,
                    fallback=evidence_summary,
                )
                conn.execute(
                    """
                    UPDATE profile_items
                    SET confidence = ?, evidence_count = ?, source_npcs = ?,
                        source_counts = ?, status = ?, evidence_summary = ?,
                        last_seen_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        confidence,
                        evidence_count,
                        json_dumps(sorted(source_counts)),
                        json_dumps(source_counts),
                        status,
                        summary,
                        occurred_at,
                        occurred_at,
                        row["id"],
                    ),
                )

            item_row = conn.execute(
                "SELECT * FROM profile_items WHERE player_id = ? AND tag = ?",
                (player_id, tag),
            ).fetchone()

        if item_row["category"] == "time":
            return self._row_to_time_habit(item_row)
        return self._row_to_item(item_row)

    def _record_time_habit(
        self,
        player_id: str,
        npc_name: str,
        occurred_at: datetime,
    ) -> Dict[str, Any]:
        bucket = time_bucket(occurred_at)
        tag = f"time/{bucket}"
        signal = {
            "category": "time",
            "tag": tag,
            "label": label_for_tag(tag),
            "weight": 0.0,
            "evidence_summary": f"玩家在{label_for_tag(tag)}时段互动",
        }
        item = self._apply_signal(
            player_id=player_id,
            npc_name=npc_name,
            signal=signal,
            event_type="active_time_detected",
            occurred_at=occurred_at.isoformat(),
        )
        self._recompute_time_habit_confidence(player_id)
        return self.get_item(player_id, item["id"])

    def _recompute_time_habit_confidence(self, player_id: str) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, evidence_count, status
                FROM profile_items
                WHERE player_id = ? AND category = 'time'
                """,
                (player_id,),
            ).fetchall()
            total = sum(int(row["evidence_count"]) for row in rows)
            if total <= 0:
                return
            for row in rows:
                count = int(row["evidence_count"])
                ratio = count / total
                status = row["status"]
                if status not in (PROFILE_SUPPRESSED, PROFILE_REJECTED):
                    status = PROFILE_ACTIVE
                conn.execute(
                    """
                    UPDATE profile_items
                    SET confidence = ?, status = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (round(ratio, 4), status, datetime.now().isoformat(), row["id"]),
                )

    def _prompt_interest_items(
        self,
        player_id: str,
        npc_name: str,
        current_tags: set[str],
    ) -> List[Dict[str, Any]]:
        relevant_categories = NPC_RELEVANT_CATEGORIES.get(npc_name, {"social", "gameplay"})
        conversation_count = self._conversation_count(player_id)
        rows = self._fetch_items(player_id)
        items: List[Dict[str, Any]] = []

        for row in rows:
            if row["category"] == "time":
                continue
            if row["status"] != PROFILE_ACTIVE:
                continue
            if float(row["confidence"]) < self.MIN_PROMPT_CONFIDENCE:
                continue
            if row["category"] not in relevant_categories:
                continue
            if row["tag"] not in current_tags and not self._mention_allowed(row, conversation_count):
                continue
            items.append(self._row_to_item(row))

        items.sort(
            key=lambda item: (
                item["tag"] not in current_tags,
                -item["confidence"],
                -item["evidence_count"],
            )
        )
        return items[:3]

    def _prompt_time_habit(self, player_id: str) -> Optional[Dict[str, Any]]:
        conversation_count = self._conversation_count(player_id)
        rows = self._fetch_items(player_id)
        habits = []
        for row in rows:
            if row["category"] != "time":
                continue
            if row["status"] != PROFILE_ACTIVE:
                continue
            if int(row["evidence_count"]) < self.TIME_HABIT_MIN_COUNT:
                continue
            if float(row["confidence"]) < self.MIN_PROMPT_CONFIDENCE:
                continue
            if not self._mention_allowed(row, conversation_count):
                continue
            habits.append(self._row_to_time_habit(row))

        if not habits:
            return None
        habits.sort(key=lambda item: (-item["confidence"], -item["evidence_count"]))
        return habits[0]

    def _mention_allowed(self, row: sqlite3.Row, conversation_count: int) -> bool:
        mention_count = int(row["mention_count"] or 0)
        if mention_count == 0:
            return True
        last_event_count = int(row["last_mentioned_event_count"] or 0)
        return conversation_count - last_event_count >= self.MENTION_COOLDOWN_CONVERSATIONS

    def _mark_items_mentioned(self, player_id: str, npc_name: str, item_ids: Sequence[int]) -> None:
        if not item_ids:
            return
        now = datetime.now().isoformat()
        event_count = self._conversation_count(player_id)
        placeholders = ",".join("?" for _ in item_ids)
        with self._connect() as conn:
            conn.execute(
                f"""
                UPDATE profile_items
                SET mention_count = mention_count + 1,
                    last_mentioned_at = ?,
                    last_mentioned_by_npc = ?,
                    last_mentioned_event_count = ?,
                    updated_at = ?
                WHERE player_id = ? AND id IN ({placeholders})
                """,
                (now, npc_name, event_count, now, player_id, *item_ids),
            )

    def _conversation_count(self, player_id: str) -> int:
        with self._connect() as conn:
            value = conn.execute(
                """
                SELECT COUNT(*)
                FROM profile_events
                WHERE player_id = ? AND event_type = 'chat_interaction'
                """,
                (player_id,),
            ).fetchone()[0]
        return int(value)

    def _fetch_items(self, player_id: str) -> List[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM profile_items
                WHERE player_id = ?
                ORDER BY confidence DESC, evidence_count DESC, updated_at DESC
                """,
                (player_id,),
            ).fetchall()
        return list(rows)

    def _row_to_item(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": int(row["id"]),
            "category": row["category"],
            "tag": row["tag"],
            "label": row["label"] or label_for_tag(row["tag"]),
            "confidence": round(float(row["confidence"]), 4),
            "status": row["status"],
            "evidence_count": int(row["evidence_count"]),
            "source_npcs": json_loads(row["source_npcs"], []),
            "source_counts": json_loads(row["source_counts"], {}),
            "evidence_summary": row["evidence_summary"] or "",
            "last_seen_at": row["last_seen_at"],
            "last_mentioned_at": row["last_mentioned_at"],
            "last_mentioned_by_npc": row["last_mentioned_by_npc"],
            "mention_count": int(row["mention_count"] or 0),
            "updated_at": row["updated_at"],
        }

    def _row_to_time_habit(self, row: sqlite3.Row) -> Dict[str, Any]:
        item = self._row_to_item(row)
        item["bucket"] = item["tag"].split("/", 1)[-1]
        return item

    def _build_summary(
        self,
        items: Sequence[Dict[str, Any]],
        time_habits: Sequence[Dict[str, Any]],
    ) -> str:
        active_labels = [
            item["label"]
            for item in items
            if item["status"] == PROFILE_ACTIVE
            and item["confidence"] >= self.MIN_PROMPT_CONFIDENCE
        ][:3]
        parts: List[str] = []
        if active_labels:
            parts.append(f"玩家对{'、'.join(active_labels)}有稳定兴趣")
        if time_habits:
            parts.append(f"常在{time_habits[0]['label'].replace('活跃', '')}互动")
        if not parts:
            return "暂未形成稳定画像。"
        return "，".join(parts) + "。"

    def _merge_evidence_summary(
        self,
        label: str,
        source_counts: Dict[str, int],
        evidence_count: int,
        fallback: str,
    ) -> str:
        if evidence_count <= 1:
            return fallback
        sorted_sources = sorted(source_counts, key=lambda name: (-source_counts[name], name))
        source_text = "、".join(sorted_sources[:2])
        return f"玩家多次和{source_text}提到{label}相关话题"

    def _record_event(
        self,
        player_id: str,
        event_type: str,
        npc_name: str,
        category: str,
        tag: str,
        weight: float,
        occurred_at: str,
        evidence_summary: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO profile_events (
                    player_id, event_type, npc_name, category, tag, weight,
                    occurred_at, evidence_summary
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    player_id,
                    event_type,
                    npc_name,
                    category,
                    tag,
                    float(weight),
                    occurred_at,
                    evidence_summary,
                ),
            )

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    label TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    evidence_count INTEGER NOT NULL DEFAULT 0,
                    source_npcs TEXT NOT NULL DEFAULT '[]',
                    source_counts TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'active',
                    evidence_summary TEXT NOT NULL DEFAULT '',
                    last_seen_at TEXT,
                    last_mentioned_at TEXT,
                    last_mentioned_by_npc TEXT,
                    last_mentioned_event_count INTEGER NOT NULL DEFAULT 0,
                    mention_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT,
                    UNIQUE(player_id, tag)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    npc_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 0,
                    occurred_at TEXT NOT NULL,
                    evidence_summary TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_profile_items_player
                ON profile_items(player_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_profile_events_player_type
                ON profile_events(player_id, event_type)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _is_recent(self, occurred_at: datetime) -> bool:
        try:
            age = datetime.now() - occurred_at
        except TypeError:
            return True
        return age.days <= 7

    def _clamp_confidence(self, value: float) -> float:
        return round(max(0.0, min(1.0, value)), 4)


def normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def contains_keyword(text: str, keyword: str) -> bool:
    keyword = keyword.lower()
    if not keyword:
        return False
    if keyword.isascii() and re.match(r"^[a-z0-9_+-]+$", keyword):
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None
    return keyword in text


def label_for_tag(tag: str) -> str:
    if tag in LABELS:
        return LABELS[tag]
    suffix = tag.split("/", 1)[-1]
    return suffix.replace("_", " ")


def time_bucket(value: datetime) -> str:
    hour = value.hour
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 23:
        return "evening"
    return "late_night"


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def json_loads(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


_player_profile_manager: Optional[PlayerProfileManager] = None


def get_player_profile_manager() -> PlayerProfileManager:
    global _player_profile_manager
    if _player_profile_manager is None:
        _player_profile_manager = PlayerProfileManager()
    return _player_profile_manager
