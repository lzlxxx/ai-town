"""数据模型定义"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

class EmotionInfo(BaseModel):
    """NPC情绪信息"""
    dominant: str = Field(..., description="主情绪: neutral/joy/sadness/anger/excitement")
    label: str = Field(..., description="主情绪中文标签")
    intensity: float = Field(..., description="主情绪强度")
    level: str = Field(..., description="强度等级: low/medium/high")
    level_label: str = Field(..., description="强度等级中文标签")
    values: Dict[str, float] = Field(..., description="完整情绪值")
    reason: str = Field(default="", description="最近变化原因")
    updated_at: Optional[str] = Field(default=None, description="更新时间")

class TaskEvent(BaseModel):
    """任务事件"""
    event_type: str = Field(..., description="事件类型: accepted/completed")
    task_id: str = Field(..., description="任务ID")
    npc_name: str = Field(..., description="任务所属NPC")
    title: str = Field(..., description="任务标题")
    message: str = Field(..., description="事件说明")
    reward_affinity: float = Field(default=0.0, description="好感度奖励")
    new_affinity: Optional[float] = Field(default=None, description="奖励后的好感度")

class ChatRequest(BaseModel):
    """单个NPC对话请求"""
    npc_name: str = Field(..., description="NPC名称")
    message: str = Field(..., description="玩家消息")
    player_id: str = Field(default="player", description="玩家ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "npc_name": "张三",
                "message": "你好,你在做什么?",
                "player_id": "player"
            }
        }

class ChatResponse(BaseModel):
    """单个NPC对话响应"""
    npc_name: str = Field(..., description="NPC名称")
    npc_title: str = Field(..., description="NPC职位")
    player_id: str = Field(default="player", description="玩家ID")
    message: str = Field(..., description="NPC回复")
    success: bool = Field(default=True, description="是否成功")
    task_events: List[TaskEvent] = Field(default_factory=list, description="本轮对话触发的任务事件")
    emotion: Optional[EmotionInfo] = Field(default=None, description="本轮对话后的NPC情绪状态")
    affinity: float = Field(default=50.0, description="NPC对玩家的当前好感度")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="时间戳")
    
    class Config:
        json_schema_extra = {
            "example": {
                "npc_name": "张三",
                "npc_title": "Python工程师",
                "message": "你好!我正在写代码,调试一个多智能体系统的bug。",
                "success": True
            }
        }

class NPCInfo(BaseModel):
    """NPC信息"""
    name: str = Field(..., description="NPC名称")
    title: str = Field(..., description="NPC职位")
    location: str = Field(..., description="NPC位置")
    activity: str = Field(..., description="当前活动")
    available: bool = Field(default=True, description="是否可对话")
    emotion: Optional[EmotionInfo] = Field(default=None, description="当前NPC情绪状态")

class NPCStatusResponse(BaseModel):
    """NPC状态响应"""
    dialogues: Dict[str, str] = Field(..., description="NPC当前对话内容")
    last_update: Optional[datetime] = Field(None, description="上次更新时间")
    next_update_in: int = Field(..., description="下次更新倒计时(秒)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dialogues": {
                    "张三": "终于把这个bug修复了,测试通过!",
                    "李四": "下周的产品评审会需要准备一下资料。",
                    "王五": "这个界面的配色方案还需要优化一下。"
                },
                "last_update": "2024-01-15T10:30:00",
                "next_update_in": 25
            }
        }

class NPCListResponse(BaseModel):
    """NPC列表响应"""
    npcs: List[NPCInfo] = Field(..., description="NPC列表")
    total: int = Field(..., description="NPC总数")

class TaskInfo(BaseModel):
    """任务信息"""
    task_id: str = Field(..., description="任务ID")
    npc_name: str = Field(..., description="任务所属NPC")
    npc_title: str = Field(..., description="NPC职位")
    title: str = Field(..., description="任务标题")
    description: str = Field(..., description="任务描述")
    objective: str = Field(..., description="任务目标")
    status: str = Field(..., description="任务状态")
    unlock_affinity: float = Field(..., description="解锁所需好感度")
    current_affinity: float = Field(..., description="当前好感度")
    reward_affinity: float = Field(..., description="完成奖励好感度")
    hint: str = Field(..., description="当前状态提示")
    can_accept: bool = Field(default=False, description="是否可接受")
    accepted_at: Optional[datetime] = Field(default=None, description="接受时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    progress: Dict[str, Any] = Field(default_factory=dict, description="任务进度信息")

class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskInfo] = Field(..., description="任务列表")
    total: int = Field(..., description="任务总数")
    player_id: str = Field(default="player", description="玩家ID")

class TaskAcceptResponse(BaseModel):
    """任务接受响应"""
    success: bool = Field(..., description="是否成功")
    reason: str = Field(..., description="结果说明")
    task: Optional[TaskInfo] = Field(default=None, description="任务信息")

class PlayerProfileItem(BaseModel):
    """玩家画像项"""
    id: int = Field(..., description="画像项ID")
    category: str = Field(..., description="一级分类")
    tag: str = Field(..., description="画像标签")
    label: str = Field(..., description="玩家可读标签")
    confidence: float = Field(..., description="置信度")
    status: str = Field(..., description="状态: active/suppressed/stale/rejected")
    evidence_count: int = Field(..., description="证据数量")
    source_npcs: List[str] = Field(default_factory=list, description="来源NPC")
    source_counts: Dict[str, int] = Field(default_factory=dict, description="各NPC来源计数")
    evidence_summary: str = Field(default="", description="短证据摘要")
    last_seen_at: Optional[str] = Field(default=None, description="最近证据时间")
    last_mentioned_at: Optional[str] = Field(default=None, description="最近被提及时间")
    last_mentioned_by_npc: Optional[str] = Field(default=None, description="最近提及的NPC")
    mention_count: int = Field(default=0, description="提及次数")
    updated_at: Optional[str] = Field(default=None, description="更新时间")

class TimeHabitInfo(PlayerProfileItem):
    """玩家时间习惯画像项"""
    bucket: str = Field(..., description="时间段: morning/afternoon/evening/late_night")

class PlayerProfileResponse(BaseModel):
    """玩家画像响应"""
    player_id: str = Field(..., description="玩家ID")
    items: List[PlayerProfileItem] = Field(default_factory=list, description="兴趣/偏好画像项")
    time_habits: List[TimeHabitInfo] = Field(default_factory=list, description="时间习惯")
    summary: str = Field(default="", description="玩家可读摘要")

class ProfileItemStatusUpdate(BaseModel):
    """画像项状态更新请求"""
    status: str = Field(..., description="新状态: active/suppressed/stale/rejected")

class ProfileClearResponse(BaseModel):
    """画像清空响应"""
    player_id: str = Field(..., description="玩家ID")
    deleted_items: int = Field(..., description="删除的画像项数量")
    deleted_events: int = Field(..., description="删除的画像事件数量")
