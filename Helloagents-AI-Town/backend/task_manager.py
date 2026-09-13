"""NPC task system for CyberTown.

Version 1 intentionally keeps task state in memory and uses preset templates.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set


TASK_LOCKED = "locked"
TASK_AVAILABLE = "available"
TASK_ACTIVE = "active"
TASK_COMPLETED = "completed"

ACCEPT_KEYWORDS = [
    "接受", "可以", "我帮你", "没问题", "交给我", "愿意", "试试",
    "好啊", "好的", "来吧", "帮忙", "我来"
]


@dataclass(frozen=True)
class TaskTemplate:
    task_id: str
    npc_name: str
    npc_title: str
    title: str
    description: str
    objective: str
    active_hint: str
    completed_hint: str
    completion_keywords: List[str]
    unlock_affinity: float = 60.0
    reward_affinity: float = 10.0
    required_contact_npc: Optional[str] = None


@dataclass
class TaskState:
    status: str = TASK_LOCKED
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.now)


TASK_TEMPLATES: Dict[str, TaskTemplate] = {
    "zhang_debug_code": TaskTemplate(
        task_id="zhang_debug_code",
        npc_name="张三",
        npc_title="Python工程师",
        title="帮张三调试代码",
        description="张三遇到一段多智能体调用链的异常,需要你一起定位问题。",
        objective="和张三聊代码排查思路,给出与 bug、日志、测试或边界情况有关的建议。",
        active_hint="围绕报错、日志、断点、空值、边界、测试、缓存等方向给张三建议。",
        completed_hint="你已经帮张三梳理了调试思路。",
        completion_keywords=[
            "bug", "报错", "异常", "日志", "断点", "空值", "边界", "测试",
            "递归", "复杂度", "缓存", "调用链", "复现", "堆栈", "traceback"
        ],
    ),
    "li_collect_feedback": TaskTemplate(
        task_id="li_collect_feedback",
        npc_name="李四",
        npc_title="产品经理",
        title="帮李四收集用户反馈",
        description="李四想知道设计侧对当前产品体验的看法,需要你先去问问王五。",
        objective="先和王五聊一次,再回到李四这里转述用户体验或设计反馈。",
        active_hint="先找王五聊聊,再把反馈、建议、体验问题或用户需求告诉李四。",
        completed_hint="你已经帮李四带回了有效反馈。",
        completion_keywords=[
            "反馈", "建议", "问题", "体验", "用户", "需求", "设计", "可用性",
            "痛点", "优化", "评价", "意见"
        ],
        required_contact_npc="王五",
    ),
    "wang_design_review": TaskTemplate(
        task_id="wang_design_review",
        npc_name="王五",
        npc_title="UI设计师",
        title="帮王五评价设计方案",
        description="王五正在打磨一个界面方案,希望你从视觉和交互角度给出评价。",
        objective="和王五聊设计评价,给出与颜色、布局、按钮、字体、间距或交互有关的看法。",
        active_hint="围绕颜色、布局、对比度、字体、间距、按钮、视觉层级或交互体验给王五建议。",
        completed_hint="你已经帮王五完成了一轮设计评价。",
        completion_keywords=[
            "颜色", "布局", "对比度", "可读性", "按钮", "字体", "间距",
            "视觉", "交互", "层级", "留白", "动效", "一致性", "可用性"
        ],
    ),
}


class TaskManager:
    """Manage in-memory NPC task state for one backend process."""

    def __init__(self):
        self.player_tasks: Dict[str, Dict[str, TaskState]] = {}
        self.npc_contacts: Dict[str, Set[str]] = {}

    def get_tasks(
        self,
        player_id: str,
        get_affinity: Callable[[str, str], float],
    ) -> List[Dict[str, Any]]:
        """Return all task info after refreshing unlock state."""
        self._refresh_unlocks(player_id, get_affinity)
        return [
            self._build_task_info(template, player_id, get_affinity)
            for template in TASK_TEMPLATES.values()
        ]

    def accept_task(
        self,
        task_id: str,
        player_id: str,
        get_affinity: Callable[[str, str], float],
    ) -> Dict[str, Any]:
        """Accept an available task and return an API-friendly result."""
        template = TASK_TEMPLATES.get(task_id)
        if template is None:
            return {
                "success": False,
                "reason": "任务不存在",
                "task": None,
            }

        self._refresh_unlocks(player_id, get_affinity)
        state = self._get_state(player_id, task_id)

        if state.status == TASK_COMPLETED:
            return {
                "success": False,
                "reason": "任务已完成",
                "task": self._build_task_info(template, player_id, get_affinity),
            }

        if state.status == TASK_ACTIVE:
            return {
                "success": True,
                "reason": "任务已接受",
                "task": self._build_task_info(template, player_id, get_affinity),
            }

        if state.status != TASK_AVAILABLE:
            return {
                "success": False,
                "reason": "好感度不足,暂未解锁",
                "task": self._build_task_info(template, player_id, get_affinity),
            }

        state.status = TASK_ACTIVE
        state.accepted_at = datetime.now()
        state.updated_at = datetime.now()

        return {
            "success": True,
            "reason": "任务已接受",
            "task": self._build_task_info(template, player_id, get_affinity),
        }

    def record_npc_contact(self, player_id: str, npc_name: str) -> None:
        """Record that the player has talked with an NPC in this server run."""
        if player_id not in self.npc_contacts:
            self.npc_contacts[player_id] = set()
        self.npc_contacts[player_id].add(npc_name)

    def build_prompt_context(
        self,
        npc_name: str,
        player_id: str,
        get_affinity: Callable[[str, str], float],
    ) -> str:
        """Build task context for the current NPC reply prompt."""
        template = self._get_template_by_npc(npc_name)
        if template is None:
            return ""

        self._refresh_unlocks(player_id, get_affinity)
        task_info = self._build_task_info(template, player_id, get_affinity)
        status = task_info["status"]

        if status == TASK_AVAILABLE:
            return (
                "【当前任务线索】\n"
                f"你可以自然邀请玩家帮你完成任务「{template.title}」。\n"
                f"任务目标: {template.objective}\n"
                "如果玩家表达愿意或接受,系统会自动标记任务已接受。\n\n"
            )

        if status == TASK_ACTIVE:
            return (
                "【当前任务进展】\n"
                f"玩家已接受你的任务「{template.title}」。\n"
                f"完成提示: {task_info['hint']}\n"
                "如果玩家给出了有效帮助或反馈,请自然表达感谢。\n\n"
            )

        if status == TASK_COMPLETED:
            return (
                "【当前任务进展】\n"
                f"玩家已经完成你的任务「{template.title}」。可以自然提及这次帮助。\n\n"
            )

        return ""

    def process_dialogue_after_response(
        self,
        npc_name: str,
        player_message: str,
        player_id: str,
        get_affinity: Callable[[str, str], float],
    ) -> List[Dict[str, Any]]:
        """Update task state from dialogue and return task events."""
        template = self._get_template_by_npc(npc_name)
        if template is None:
            return []

        self._refresh_unlocks(player_id, get_affinity)
        events: List[Dict[str, Any]] = []
        state = self._get_state(player_id, template.task_id)

        if state.status == TASK_AVAILABLE and self._matches_any(player_message, ACCEPT_KEYWORDS):
            accept_result = self.accept_task(template.task_id, player_id, get_affinity)
            if accept_result["success"]:
                events.append(self._build_event("accepted", template, "任务已接受"))
                state = self._get_state(player_id, template.task_id)

        if state.status == TASK_ACTIVE and self._is_completion_message(template, player_message, player_id):
            state.status = TASK_COMPLETED
            state.completed_at = datetime.now()
            state.updated_at = datetime.now()
            events.append(self._build_event("completed", template, "任务已完成"))

        return events

    def _refresh_unlocks(
        self,
        player_id: str,
        get_affinity: Callable[[str, str], float],
    ) -> None:
        player_states = self._get_player_states(player_id)
        for task_id, template in TASK_TEMPLATES.items():
            state = player_states.setdefault(task_id, TaskState())
            if state.status in (TASK_ACTIVE, TASK_COMPLETED):
                continue

            affinity = get_affinity(template.npc_name, player_id)
            next_status = TASK_AVAILABLE if affinity >= template.unlock_affinity else TASK_LOCKED
            if state.status != next_status:
                state.status = next_status
                state.updated_at = datetime.now()

    def _build_task_info(
        self,
        template: TaskTemplate,
        player_id: str,
        get_affinity: Callable[[str, str], float],
    ) -> Dict[str, Any]:
        state = self._get_state(player_id, template.task_id)
        affinity = get_affinity(template.npc_name, player_id)
        hint = self._build_hint(template, player_id, state.status, affinity)

        return {
            "task_id": template.task_id,
            "npc_name": template.npc_name,
            "npc_title": template.npc_title,
            "title": template.title,
            "description": template.description,
            "objective": template.objective,
            "status": state.status,
            "unlock_affinity": template.unlock_affinity,
            "current_affinity": affinity,
            "reward_affinity": template.reward_affinity,
            "hint": hint,
            "can_accept": state.status == TASK_AVAILABLE,
            "accepted_at": state.accepted_at,
            "completed_at": state.completed_at,
            "progress": {
                "talked_to": sorted(self.npc_contacts.get(player_id, set())),
                "required_contact_npc": template.required_contact_npc,
                "required_contact_met": self._required_contact_met(template, player_id),
            },
        }

    def _build_hint(
        self,
        template: TaskTemplate,
        player_id: str,
        status: str,
        affinity: float,
    ) -> str:
        if status == TASK_LOCKED:
            missing = max(0.0, template.unlock_affinity - affinity)
            return f"好感度达到{template.unlock_affinity:.0f}后解锁,还差{missing:.0f}点。"

        if status == TASK_AVAILABLE:
            return "可以接受任务。"

        if status == TASK_ACTIVE:
            if template.required_contact_npc and not self._required_contact_met(template, player_id):
                return f"需要先和{template.required_contact_npc}聊一次,再回来反馈。"
            return template.active_hint

        return template.completed_hint

    def _build_event(self, event_type: str, template: TaskTemplate, message: str) -> Dict[str, Any]:
        return {
            "event_type": event_type,
            "task_id": template.task_id,
            "npc_name": template.npc_name,
            "title": template.title,
            "message": message,
            "reward_affinity": template.reward_affinity if event_type == "completed" else 0.0,
        }

    def _is_completion_message(
        self,
        template: TaskTemplate,
        player_message: str,
        player_id: str,
    ) -> bool:
        if template.required_contact_npc and not self._required_contact_met(template, player_id):
            return False
        return self._matches_any(player_message, template.completion_keywords)

    def _required_contact_met(self, template: TaskTemplate, player_id: str) -> bool:
        if not template.required_contact_npc:
            return True
        return template.required_contact_npc in self.npc_contacts.get(player_id, set())

    def _get_template_by_npc(self, npc_name: str) -> Optional[TaskTemplate]:
        for template in TASK_TEMPLATES.values():
            if template.npc_name == npc_name:
                return template
        return None

    def _get_player_states(self, player_id: str) -> Dict[str, TaskState]:
        if player_id not in self.player_tasks:
            self.player_tasks[player_id] = {}
        return self.player_tasks[player_id]

    def _get_state(self, player_id: str, task_id: str) -> TaskState:
        states = self._get_player_states(player_id)
        if task_id not in states:
            states[task_id] = TaskState()
        return states[task_id]

    def _matches_any(self, text: str, keywords: List[str]) -> bool:
        normalized = text.lower()
        return any(keyword.lower() in normalized for keyword in keywords)


_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """Return the process-wide task manager singleton."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
