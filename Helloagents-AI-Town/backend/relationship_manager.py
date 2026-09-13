"""NPC好感度管理系统"""

import sys
import os

# 添加HelloAgents到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'HelloAgents'))

from hello_agents import SimpleAgent, HelloAgentsLLM
from typing import Dict, Optional, Tuple
from datetime import datetime
import json
import re
from config import normalize_base_url
from llm_client import CyberTownLLM

class RelationshipManager:
    """NPC好感度管理器
    
    功能:
    - 管理NPC与玩家的好感度 (0-100)
    - 使用LLM分析对话情感
    - 自动更新好感度
    - 提供好感度等级和修饰词
    - 管理NPC对玩家的长期情绪状态
    """

    EMOTION_KEYS = ("joy", "sadness", "anger", "excitement")
    EMOTION_HISTORY_LIMIT = 10
    EMOTION_DECAY_RATE = 0.10
    EMOTION_DOMINANT_THRESHOLD = 40.0
    MAX_EMOTION_DELTA = 25
    MIN_AFFINITY_DELTA = -10
    MAX_AFFINITY_DELTA = 8

    DEFAULT_EMOTION_BASELINE = {
        "joy": 45.0,
        "sadness": 20.0,
        "anger": 18.0,
        "excitement": 40.0,
    }
    NPC_EMOTION_BASELINES = {
        "张三": {
            "joy": 45.0,
            "sadness": 20.0,
            "anger": 18.0,
            "excitement": 55.0,
        },
        "李四": {
            "joy": 55.0,
            "sadness": 15.0,
            "anger": 15.0,
            "excitement": 45.0,
        },
        "王五": {
            "joy": 45.0,
            "sadness": 30.0,
            "anger": 18.0,
            "excitement": 40.0,
        },
    }
    EMOTION_LABELS = {
        "neutral": "平静",
        "joy": "开心",
        "sadness": "难过",
        "anger": "生气",
        "excitement": "兴奋",
    }
    EMOTION_MODIFIERS = {
        "neutral": "按当前好感度自然交流。",
        "joy": "语气更温和积极,愿意解释并分享一点额外信息。",
        "sadness": "语气低落克制,少用感叹,可以表达需要支持。",
        "anger": "语气冷淡简短,边界感更强,避免主动分享无关信息,但不要辱骂玩家。",
        "excitement": "语气更积极有活力,愿意展开细节和任务线索。",
    }
    
    def __init__(self, llm: HelloAgentsLLM):
        """初始化好感度管理器
        
        Args:
            llm: HelloAgentsLLM实例
        """
        self.llm = llm
        self.affinity_llm = self._create_affinity_llm(llm)
        
        # 存储每个NPC与玩家的好感度
        # 格式: {npc_name: {player_id: affinity_score}}
        self.affinity_scores: Dict[str, Dict[str, float]] = {}

        # 存储每个NPC与玩家的长期情绪状态
        # 格式: {npc_name: {player_id: {"values": {...}, ...}}}
        self.emotion_states: Dict[str, Dict[str, Dict]] = {}
        self.emotion_history: Dict[str, Dict[str, list[Dict]]] = {}
        
        # 创建好感度分析Agent
        self.analyzer_agent = SimpleAgent(
            name="AffinityAnalyzer",
            llm=self.affinity_llm,
            system_prompt=self._create_analyzer_prompt()
        )
        self.fallback_analyzer_agent = None
        if self.affinity_llm is not llm:
            self.fallback_analyzer_agent = SimpleAgent(
                name="AffinityAnalyzerFallback",
                llm=llm,
                system_prompt=self._create_analyzer_prompt()
            )
        
        print("💖 好感度管理系统已初始化")

    def _create_affinity_llm(self, fallback_llm: HelloAgentsLLM) -> HelloAgentsLLM:
        """Create a dedicated LLM for affinity analysis, falling back to main chat config."""
        affinity_model = self._env_value("LLM_AFFINITY_MODEL_ID", "LLM_AFFINITY_MODEL")
        affinity_api_key = self._env_value("LLM_AFFINITY_API_KEY", "AFFINITY_API_KEY")
        affinity_base_url = self._env_value("LLM_AFFINITY_BASE_URL", "AFFINITY_BASE_URL")

        model = affinity_model or getattr(fallback_llm, "model", None)
        api_key = affinity_api_key or getattr(fallback_llm, "api_key", None)
        base_url = normalize_base_url(affinity_base_url) or getattr(fallback_llm, "base_url", None)
        timeout = self._env_int("LLM_AFFINITY_TIMEOUT", 8)
        max_retries = self._env_int("LLM_AFFINITY_MAX_RETRIES", self._env_int("LLM_MAX_RETRIES", 0))

        if not all([model, api_key, base_url]):
            print("⚠️  好感度分析LLM配置不完整,将复用主对话LLM")
            return fallback_llm

        try:
            affinity_llm = CyberTownLLM(
                model=model,
                api_key=api_key,
                base_url=base_url,
                provider="custom",
                temperature=0,
                max_tokens=120,
                timeout=timeout,
                max_retries=max_retries
            )

            if affinity_model or affinity_api_key or affinity_base_url:
                print(f"💖 好感度分析LLM已使用独立配置: {model} @ {base_url}")
            else:
                print(f"💖 好感度分析LLM复用主配置: {model} @ {base_url}")

            return affinity_llm
        except Exception as e:
            print(f"⚠️  好感度分析LLM初始化失败,将复用主对话LLM: {e}")
            return fallback_llm
    
    def _create_analyzer_prompt(self) -> str:
        """创建情感分析Agent的系统提示词"""
        return """你是一个情感分析专家,负责分析对话中的情感倾向,判断是否应该改变NPC对玩家的好感度和长期情绪状态。

【任务】
分析玩家与NPC的对话,判断是否应该改变好感度,以及开心、难过、生气、兴奋四种情绪的变化幅度。

【分析维度】
1. **玩家态度**: 友好/中立/不友好
2. **对话内容**: 积极/中立/消极
3. **互动质量**: 深入/一般/敷衍
4. **情感倾向**: 赞美/批评/中性

【好感度变化规则】
- 赞美、感谢、请教: +3 到 +8
- 友好问候、正常交流: +1 到 +3
- 普通闲聊、中性话题: 0
- 批评、质疑、不耐烦: -3 到 -8
- 侮辱、攻击、恶意: -8 到 -15

【情绪变化规则】
- joy: 被鼓励、感谢、赞美、获得帮助时上升,被攻击或冷落时下降
- sadness: 失望、道歉、挫败、被否定时上升,得到支持时下降
- anger: 被侮辱、攻击、冒犯、不耐烦对待时上升,被尊重或安抚时下降
- excitement: 新想法、项目进展、任务线索、积极讨论时上升,冷场或挫败时下降

【输出格式】(严格遵守JSON格式,不要添加任何其他文字)
{
    "should_change": true/false,
    "change_amount": -10到+8之间的整数,
    "reason": "简短说明原因(10字以内)",
    "sentiment": "positive/neutral/negative",
    "emotion_deltas": {
        "joy": -25到+25之间的整数,
        "sadness": -25到+25之间的整数,
        "anger": -25到+25之间的整数,
        "excitement": -25到+25之间的整数
    }
}

【示例1】
玩家: "你好,很高兴认识你!"
NPC: "你好!我也很高兴认识你。"
输出: {"should_change": true, "change_amount": 5, "reason": "友好问候", "sentiment": "positive", "emotion_deltas": {"joy": 8, "sadness": -2, "anger": -2, "excitement": 4}}

【示例2】
玩家: "你这个设计太丑了!"
NPC: "抱歉,我会改进的..."
输出: {"should_change": true, "change_amount": -8, "reason": "批评工作", "sentiment": "negative", "emotion_deltas": {"joy": -8, "sadness": 5, "anger": 12, "excitement": -3}}

【示例3】
玩家: "今天天气不错"
NPC: "是啊,挺好的。"
输出: {"should_change": false, "change_amount": 0, "reason": "普通闲聊", "sentiment": "neutral", "emotion_deltas": {"joy": 0, "sadness": 0, "anger": 0, "excitement": 0}}

【示例4】
玩家: "你的代码写得真棒!"
NPC: "谢谢!我最近在研究新技术。"
输出: {"should_change": true, "change_amount": 8, "reason": "赞美工作", "sentiment": "positive", "emotion_deltas": {"joy": 12, "sadness": -3, "anger": -4, "excitement": 6}}

【示例5】
玩家: "能教教我吗?"
NPC: "当然可以!我很乐意分享。"
输出: {"should_change": true, "change_amount": 6, "reason": "请教学习", "sentiment": "positive", "emotion_deltas": {"joy": 8, "sadness": -2, "anger": -3, "excitement": 8}}

【重要】
- 只输出JSON,不要添加任何解释或其他文字
- change_amount必须是整数
- reason必须简短(10字以内)
- sentiment必须是positive/neutral/negative之一
- emotion_deltas必须包含joy/sadness/anger/excitement四个键
"""
    
    def get_affinity(self, npc_name: str, player_id: str = "player") -> float:
        """获取好感度 (0-100)
        
        Args:
            npc_name: NPC名称
            player_id: 玩家ID
            
        Returns:
            好感度值 (0-100)
        """
        if npc_name not in self.affinity_scores:
            self.affinity_scores[npc_name] = {}
        
        if player_id not in self.affinity_scores[npc_name]:
            self.affinity_scores[npc_name][player_id] = 50.0  # 初始好感度50
        
        return self.affinity_scores[npc_name][player_id]
    
    def set_affinity(self, npc_name: str, affinity: float, player_id: str = "player"):
        """设置好感度
        
        Args:
            npc_name: NPC名称
            affinity: 好感度值 (0-100)
            player_id: 玩家ID
        """
        if npc_name not in self.affinity_scores:
            self.affinity_scores[npc_name] = {}
        
        # 限制在0-100范围内
        affinity = max(0.0, min(100.0, affinity))
        self.affinity_scores[npc_name][player_id] = affinity
    
    def analyze_and_update_affinity(
        self,
        npc_name: str,
        player_message: str,
        npc_response: str,
        player_id: str = "player"
    ) -> Dict:
        """分析对话并更新好感度
        
        Args:
            npc_name: NPC名称
            player_message: 玩家消息
            npc_response: NPC回复
            player_id: 玩家ID
            
        Returns:
            分析结果字典
        """
        # 构建分析提示
        prompt = f"""请分析以下对话:

玩家: {player_message}
{npc_name}: {npc_response}

请判断是否应该改变好感度,并给出变化量。
"""

        if os.getenv("LLM_AFFINITY_ENABLED", "true").lower() in ("0", "false", "no", "off"):
            return {
                "changed": False,
                "affinity": self.get_affinity(npc_name, player_id),
                "reason": "分析已关闭",
                "sentiment": "neutral",
                "emotion": self.get_emotion_state(npc_name, player_id)
            }
        
        try:
            analysis = self._run_analysis(prompt, self.analyzer_agent)
            return self._apply_analysis(npc_name, player_id, analysis)
        except Exception as e:
            if self._should_fallback_to_main_llm():
                try:
                    print("⚠️  独立好感度LLM失败,尝试使用主对话LLM兜底")
                    analysis = self._run_analysis(prompt, self.fallback_analyzer_agent)
                    return self._apply_analysis(npc_name, player_id, analysis)
                except Exception as fallback_error:
                    e = fallback_error

            reason = self._classify_analysis_error(e)
            print(f"⚠️  好感度/情绪分析失败,使用规则兜底: {reason} ({e})")
            analysis = self._build_rule_analysis(player_message, npc_response, reason)
            return self._apply_analysis(npc_name, player_id, analysis)

    def _run_analysis(self, prompt: str, agent: Optional[SimpleAgent]) -> Dict:
        """Run the affinity analyzer and parse its JSON response."""
        if agent is None:
            raise RuntimeError("没有可用的好感度分析Agent")

        response = agent.run(
            prompt,
            temperature=0,
            max_tokens=180,
            timeout=self._env_int("LLM_AFFINITY_TIMEOUT", 8)
        )
        return self._parse_analysis(response)

    def _apply_analysis(self, npc_name: str, player_id: str, analysis: Dict) -> Dict:
        """Apply parsed relationship analysis to affinity and emotion state."""
        analysis = self._normalize_analysis(analysis)
        emotion_deltas = analysis.get("emotion_deltas", {})
        emotion = self._update_emotion_state(
            npc_name=npc_name,
            player_id=player_id,
            emotion_deltas=emotion_deltas,
            reason=analysis["reason"],
        )

        base_delta = analysis["change_amount"] if analysis["should_change"] else 0
        emotion_adjustment = self._emotion_affinity_adjustment(emotion_deltas)
        final_delta = self._clamp(
            base_delta + emotion_adjustment,
            self.MIN_AFFINITY_DELTA,
            self.MAX_AFFINITY_DELTA,
        )

        current_affinity = self.get_affinity(npc_name, player_id)
        old_level = self.get_affinity_level(current_affinity)
        if final_delta != 0:
            new_affinity = self._clamp(current_affinity + final_delta, 0.0, 100.0)
            self.set_affinity(npc_name, new_affinity, player_id)
            new_level = self.get_affinity_level(new_affinity)
            return {
                "changed": True,
                "old_affinity": current_affinity,
                "new_affinity": new_affinity,
                "change_amount": final_delta,
                "base_change_amount": base_delta,
                "emotion_affinity_adjustment": emotion_adjustment,
                "reason": analysis["reason"],
                "sentiment": analysis.get("sentiment", "neutral"),
                "old_level": old_level,
                "new_level": new_level,
                "emotion": emotion,
                "emotion_deltas": emotion_deltas,
            }

        return {
            "changed": False,
            "affinity": current_affinity,
            "reason": analysis["reason"],
            "sentiment": analysis.get("sentiment", "neutral"),
            "emotion": emotion,
            "emotion_deltas": emotion_deltas,
        }

    def _classify_analysis_error(self, error: Exception) -> str:
        """Return a concise user-facing reason for affinity-analysis fallback."""
        error_text = str(error).lower()
        if "timed out" in error_text or "timeout" in error_text:
            return "分析超时"
        if "rate limit" in error_text or "429" in error_text:
            return "限流跳过"
        if "401" in error_text or "unauthorized" in error_text:
            return "鉴权失败"
        if "500" in error_text or "bad_response_status_code" in error_text:
            return "模型服务错误"
        if "model" in error_text and "not" in error_text:
            return "模型不可用"
        return "分析失败"

    def _should_fallback_to_main_llm(self) -> bool:
        return (
            self.fallback_analyzer_agent is not None
            and self._env_bool("LLM_AFFINITY_FALLBACK_TO_MAIN", True)
        )

    def _env_value(self, *names: str) -> Optional[str]:
        for name in names:
            value = os.getenv(name)
            if value and value.strip():
                return value.strip()
        return None

    def _env_int(self, name: str, default: int) -> int:
        value = os.getenv(name)
        if not value or not value.strip():
            return default
        try:
            return max(0, int(value))
        except ValueError:
            return default

    def _env_bool(self, name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None or not value.strip():
            return default
        return value.strip().lower() not in ("0", "false", "no", "off")

    def get_emotion_state(self, npc_name: str, player_id: str = "player") -> Dict:
        """Return the current in-memory emotion summary for an NPC/player pair."""
        state = self._ensure_emotion_state(npc_name, player_id)
        return self._build_emotion_summary(
            state["values"],
            state.get("reason", "初始状态"),
            state.get("updated_at"),
        )

    def get_emotion_history(self, npc_name: str, player_id: str = "player") -> list[Dict]:
        """Return recent in-memory emotion changes for debugging/API use."""
        return list(self.emotion_history.get(npc_name, {}).get(player_id, []))

    def get_emotion_prompt_context(self, npc_name: str, player_id: str = "player") -> str:
        """Build compact prompt context from the current dominant emotion."""
        emotion = self.get_emotion_state(npc_name, player_id)
        dominant = emotion["dominant"]
        label = emotion["label"]
        level = emotion["level_label"]
        intensity = emotion["intensity"]
        modifier = self.EMOTION_MODIFIERS.get(dominant, self.EMOTION_MODIFIERS["neutral"])
        return (
            "【当前情绪】\n"
            f"主情绪: {label} (强度: {level}, {dominant}={intensity:.0f}/100)\n"
            f"对话风格: {modifier}\n\n"
        )

    def _ensure_emotion_state(self, npc_name: str, player_id: str) -> Dict:
        if npc_name not in self.emotion_states:
            self.emotion_states[npc_name] = {}
        if player_id not in self.emotion_states[npc_name]:
            self.emotion_states[npc_name][player_id] = {
                "values": self._get_emotion_baseline(npc_name),
                "reason": "初始状态",
                "updated_at": datetime.now().isoformat(),
            }
        return self.emotion_states[npc_name][player_id]

    def _get_emotion_baseline(self, npc_name: str) -> Dict[str, float]:
        baseline = self.NPC_EMOTION_BASELINES.get(npc_name, self.DEFAULT_EMOTION_BASELINE)
        return {key: float(baseline.get(key, self.DEFAULT_EMOTION_BASELINE[key])) for key in self.EMOTION_KEYS}

    def _update_emotion_state(
        self,
        npc_name: str,
        player_id: str,
        emotion_deltas: Dict,
        reason: str,
    ) -> Dict:
        state = self._ensure_emotion_state(npc_name, player_id)
        baseline = self._get_emotion_baseline(npc_name)
        normalized_deltas = self._normalize_emotion_deltas(emotion_deltas)
        next_values: Dict[str, float] = {}

        for key in self.EMOTION_KEYS:
            changed = self._clamp(
                state["values"][key] + normalized_deltas[key],
                0.0,
                100.0,
            )
            decayed = changed * (1.0 - self.EMOTION_DECAY_RATE) + baseline[key] * self.EMOTION_DECAY_RATE
            next_values[key] = round(self._clamp(decayed, 0.0, 100.0), 2)

        state["values"] = next_values
        state["reason"] = reason
        state["updated_at"] = datetime.now().isoformat()
        summary = self._build_emotion_summary(next_values, reason, state["updated_at"])
        self._record_emotion_history(npc_name, player_id, normalized_deltas, summary)
        return summary

    def _record_emotion_history(
        self,
        npc_name: str,
        player_id: str,
        emotion_deltas: Dict[str, int],
        emotion: Dict,
    ) -> None:
        if npc_name not in self.emotion_history:
            self.emotion_history[npc_name] = {}
        history = self.emotion_history[npc_name].setdefault(player_id, [])
        history.append({
            "timestamp": emotion.get("updated_at"),
            "reason": emotion.get("reason", ""),
            "dominant": emotion.get("dominant", "neutral"),
            "label": emotion.get("label", "平静"),
            "intensity": emotion.get("intensity", 0.0),
            "emotion_deltas": dict(emotion_deltas),
            "values": dict(emotion.get("values", {})),
        })
        if len(history) > self.EMOTION_HISTORY_LIMIT:
            del history[: len(history) - self.EMOTION_HISTORY_LIMIT]

    def _build_emotion_summary(
        self,
        values: Dict[str, float],
        reason: str,
        updated_at: Optional[str],
    ) -> Dict:
        safe_values = {
            key: round(self._clamp(float(values.get(key, 0.0)), 0.0, 100.0), 2)
            for key in self.EMOTION_KEYS
        }
        dominant_key = max(self.EMOTION_KEYS, key=lambda key: safe_values[key])
        intensity = safe_values[dominant_key]
        if intensity < self.EMOTION_DOMINANT_THRESHOLD:
            dominant_key = "neutral"
            intensity = 0.0

        level = self._emotion_level(intensity)
        return {
            "dominant": dominant_key,
            "label": self.EMOTION_LABELS.get(dominant_key, dominant_key),
            "intensity": round(intensity, 2),
            "level": level,
            "level_label": {"low": "低", "medium": "中", "high": "高"}[level],
            "values": safe_values,
            "reason": reason,
            "updated_at": updated_at,
        }

    def _emotion_level(self, intensity: float) -> str:
        if intensity >= 70:
            return "high"
        if intensity >= 40:
            return "medium"
        return "low"

    def _normalize_emotion_deltas(self, emotion_deltas: Optional[Dict]) -> Dict[str, int]:
        result: Dict[str, int] = {}
        emotion_deltas = emotion_deltas or {}
        for key in self.EMOTION_KEYS:
            value = emotion_deltas.get(key, 0)
            try:
                value = int(value)
            except (TypeError, ValueError):
                value = 0
            result[key] = int(self._clamp(value, -self.MAX_EMOTION_DELTA, self.MAX_EMOTION_DELTA))
        return result

    def _normalize_analysis(self, analysis: Optional[Dict]) -> Dict:
        analysis = analysis or {}
        change_amount = analysis.get("change_amount", 0)
        try:
            change_amount = int(change_amount)
        except (TypeError, ValueError):
            change_amount = 0

        sentiment = str(analysis.get("sentiment", "neutral")).lower()
        if sentiment not in ("positive", "neutral", "negative"):
            sentiment = "neutral"

        return {
            "should_change": bool(analysis.get("should_change", change_amount != 0)),
            "change_amount": int(self._clamp(change_amount, self.MIN_AFFINITY_DELTA, self.MAX_AFFINITY_DELTA)),
            "reason": str(analysis.get("reason", "普通互动"))[:20],
            "sentiment": sentiment,
            "emotion_deltas": self._normalize_emotion_deltas(analysis.get("emotion_deltas")),
        }

    def _emotion_affinity_adjustment(self, emotion_deltas: Dict) -> int:
        deltas = self._normalize_emotion_deltas(emotion_deltas)
        adjustment = 0
        joy = deltas["joy"]
        anger = deltas["anger"]

        if joy >= 8:
            adjustment += 2
        elif joy >= 3:
            adjustment += 1

        if anger >= 15:
            adjustment -= 3
        elif anger >= 8:
            adjustment -= 2
        elif anger >= 3:
            adjustment -= 1

        return adjustment

    def _build_rule_analysis(self, player_message: str, npc_response: str, reason: str = "规则兜底") -> Dict:
        """Build safe deterministic relationship analysis when LLM analysis fails."""
        text = f"{player_message} {npc_response}".lower()
        positive_keywords = [
            "谢谢", "感谢", "真棒", "厉害", "喜欢", "支持", "帮助", "请教",
            "不错", "很好", "辛苦", "鼓励", "高兴", "开心"
        ]
        negative_keywords = [
            "太烂", "垃圾", "讨厌", "滚", "笨", "差劲", "丑", "烦", "闭嘴",
            "攻击", "恶意", "不耐烦"
        ]
        apology_keywords = ["抱歉", "对不起", "不好意思"]
        excitement_keywords = ["太好了", "有趣", "期待", "项目", "任务", "新想法", "进展"]

        if any(keyword in text for keyword in negative_keywords):
            return {
                "should_change": True,
                "change_amount": -5,
                "reason": reason,
                "sentiment": "negative",
                "emotion_deltas": {
                    "joy": -8,
                    "sadness": 4,
                    "anger": 14,
                    "excitement": -3,
                },
            }

        if any(keyword in text for keyword in positive_keywords):
            return {
                "should_change": True,
                "change_amount": 3,
                "reason": "友好互动",
                "sentiment": "positive",
                "emotion_deltas": {
                    "joy": 10,
                    "sadness": -2,
                    "anger": -4,
                    "excitement": 4,
                },
            }

        if any(keyword in text for keyword in apology_keywords):
            return {
                "should_change": True,
                "change_amount": 1,
                "reason": "表达歉意",
                "sentiment": "neutral",
                "emotion_deltas": {
                    "joy": 2,
                    "sadness": -2,
                    "anger": -5,
                    "excitement": 0,
                },
            }

        if any(keyword in text for keyword in excitement_keywords):
            return {
                "should_change": False,
                "change_amount": 0,
                "reason": "话题积极",
                "sentiment": "positive",
                "emotion_deltas": {
                    "joy": 2,
                    "sadness": 0,
                    "anger": 0,
                    "excitement": 8,
                },
            }

        return {
            "should_change": False,
            "change_amount": 0,
            "reason": reason,
            "sentiment": "neutral",
            "emotion_deltas": {
                "joy": 0,
                "sadness": 0,
                "anger": 0,
                "excitement": 0,
            },
        }

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
	    
    def _parse_analysis(self, response: str) -> Dict:
        """解析分析结果
        
        Args:
            response: LLM响应
            
        Returns:
            解析后的字典
        """
        response = response.strip()
        if response.startswith("```"):
            response = re.sub(r"^```(?:json)?\s*|\s*```$", "", response, flags=re.IGNORECASE | re.DOTALL).strip()

        try:
            # 尝试直接解析JSON
            analysis = json.loads(response)
            return self._normalize_analysis(analysis)
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            # 查找第一个 { 和最后一个 }
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start != -1 and end > start:
                json_str = response[start:end]
                try:
                    analysis = json.loads(json_str)
                    return self._normalize_analysis(analysis)
                except json.JSONDecodeError:
                    pass
            
            # 尝试使用正则表达式提取
            # 匹配 "should_change": true/false
            should_change_match = re.search(r'"should_change"\s*:\s*(true|false)', response, re.IGNORECASE)
            change_amount_match = re.search(r'"change_amount"\s*:\s*(-?\d+)', response)
            reason_match = re.search(r'"reason"\s*:\s*"([^"]+)"', response)
            sentiment_match = re.search(r'"sentiment"\s*:\s*"([^"]+)"', response)
            emotion_deltas = {
                key: int(match.group(1)) if match else 0
                for key in self.EMOTION_KEYS
                for match in [re.search(rf'"{key}"\s*:\s*(-?\d+)', response)]
            }
	            
            if should_change_match and change_amount_match:
                return self._normalize_analysis({
                    "should_change": should_change_match.group(1).lower() == "true",
                    "change_amount": int(change_amount_match.group(1)),
                    "reason": reason_match.group(1) if reason_match else "未知",
                    "sentiment": sentiment_match.group(1) if sentiment_match else "neutral",
                    "emotion_deltas": emotion_deltas,
                })
            
            # 解析失败,返回默认值
            print(f"⚠️  JSON解析失败,使用默认值。原始响应: {response[:100]}...")
            return self._normalize_analysis({
                "should_change": False,
                "change_amount": 0,
                "reason": "解析失败",
                "sentiment": "neutral",
                "emotion_deltas": {},
            })
    
    def get_affinity_level(self, affinity: float) -> str:
        """获取好感度等级
        
        Args:
            affinity: 好感度值 (0-100)
            
        Returns:
            好感度等级名称
        """
        if affinity >= 80:
            return "挚友"
        elif affinity >= 60:
            return "亲密"
        elif affinity >= 40:
            return "友好"
        elif affinity >= 20:
            return "熟悉"
        else:
            return "陌生"
    
    def get_affinity_modifier(self, affinity: float) -> str:
        """获取好感度修饰词 (用于调整对话风格)
        
        Args:
            affinity: 好感度值 (0-100)
            
        Returns:
            对话风格修饰词
        """
        if affinity >= 80:
            return "非常热情友好,像老朋友一样亲切,愿意分享私人话题"
        elif affinity >= 60:
            return "友好热情,愿意多聊,会主动关心对方"
        elif affinity >= 40:
            return "礼貌友善,正常交流,保持专业"
        elif affinity >= 20:
            return "礼貌但略显生疏,回答简洁"
        else:
            return "冷淡疏离,不太愿意多说,回答简短"
    
    def get_all_affinities(self, player_id: str = "player") -> Dict[str, Dict]:
        """获取所有NPC的好感度信息
        
        Args:
            player_id: 玩家ID
            
        Returns:
            所有NPC的好感度信息
        """
        result = {}
        for npc_name in self.affinity_scores:
            affinity = self.get_affinity(npc_name, player_id)
            result[npc_name] = {
                "affinity": affinity,
                "level": self.get_affinity_level(affinity),
                "modifier": self.get_affinity_modifier(affinity)
            }
        return result
