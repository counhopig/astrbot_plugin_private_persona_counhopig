"""
反思引擎：自动分析对话历史，生成自我校准记录
"""

import json
import re

from ..config import PluginConfig
from ..models import ReflectionRecord
from ..storage import PersonaStorage


class ReflectionEngine:
    def __init__(self, storage: PersonaStorage, cfg: PluginConfig):
        self.storage = storage
        self.cfg = cfg

    def build_prompt(self, user_id: str, messages: list[dict]) -> str:
        """构造反思 Prompt"""
        history_text = self._format_messages(messages)
        existing_facts = self.storage.format_profile_facts_for_prompt(user_id)
        latest_reflection = self.storage.get_latest_reflection(user_id)

        parts = [
            "请对以下对话进行反思和总结。",
            "",
            "=== 对话历史 ===",
            history_text,
        ]

        if existing_facts:
            parts += [
                "",
                "=== 已有的用户画像 ===",
                existing_facts,
            ]

        if latest_reflection:
            parts += [
                "",
                f"=== 上次反思 ({latest_reflection.created_at}) ===",
                latest_reflection.note,
            ]

        parts += [
            "",
            "=== 任务 ===",
            "1. 简要总结这次对话的主题和氛围。",
            "2. 分析 Bot 的回复是否恰当，有没有说错话、误解用户、或语气不当。",
            "3. 用户情绪变化：从对话开始到结束，用户的情绪是如何变化的？",
            "4. 提取关于用户的新事实（偏好、身份、习惯、情绪模式），用 bullet point 列出。",
            "5. 认知纠偏：如果发现之前对用户的了解有误，请指出并修正。",
            "",
            "请用以下 JSON 格式输出（只输出 JSON，不要其他内容）：",
            "```json",
            "{",
            '  "summary": "对话摘要",',
            '  "self_evaluation": "Bot 表现评价",',
            '  "emotion_change": "用户情绪变化",',
            '  "facts": ["新事实1", "新事实2"],',
            '  "bias_correction": "认知纠偏（没有则留空）"',
            "}",
            "```",
        ]

        return "\n".join(parts)

    def _format_messages(self, messages: list[dict]) -> str:
        lines = []
        for m in messages:
            role = m.get("role", "unknown")
            content = m.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def parse_result(self, user_id: str, llm_text: str) -> ReflectionRecord:
        """解析 LLM 输出，生成反思记录和画像事实"""
        data = self._extract_json(llm_text)

        summary = data.get("summary", "")
        self_eval = data.get("self_evaluation", "")
        emotion_change = data.get("emotion_change", "")
        facts = data.get("facts", [])
        bias = data.get("bias_correction", "")

        note_parts = []
        if summary:
            note_parts.append(f"【摘要】{summary}")
        if self_eval:
            note_parts.append(f"【自评】{self_eval}")
        if emotion_change:
            note_parts.append(f"【用户情绪】{emotion_change}")
        note = "\n".join(note_parts)

        facts_str = "|".join(facts) if facts else ""

        record = self.storage.add_reflection(
            user_id=user_id,
            trigger="auto",
            note=note,
            facts_str=facts_str,
            bias=bias,
        )

        # 自动将 facts 写入画像
        for fact in facts:
            self.storage.add_profile_fact(
                user_id=user_id,
                category="auto",
                content=fact,
                evidence=summary,
            )

        return record

    def _extract_json(self, text: str) -> dict:
        """从 LLM 输出中提取 JSON"""
        # 尝试找 ```json ... ``` 包裹的内容
        pattern = r"```json\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # 尝试找最外层的大括号
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = text[start:end + 1]
            else:
                json_str = text

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {
                "summary": text[:200],
                "self_evaluation": "",
                "emotion_change": "",
                "facts": [],
                "bias_correction": "",
            }
