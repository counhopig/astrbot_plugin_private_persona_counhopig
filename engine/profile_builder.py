"""
画像构建引擎：自动从对话中提取用户画像事实
也提供 upsert_cognitive_memory 工具给 LLM 主动调用
"""

import json
import re

from ..config import PluginConfig
from ..models import ProfileFact
from ..storage import PersonaStorage


class ProfileBuilder:
    def __init__(self, storage: PersonaStorage, cfg: PluginConfig):
        self.storage = storage
        self.cfg = cfg

    def build_prompt(self, user_id: str, messages: list[dict]) -> str:
        """构造画像构建 Prompt"""
        history_text = self._format_messages(messages)
        existing_facts = self.storage.format_profile_facts_for_prompt(user_id)

        parts = [
            "请从以下对话中提取关于用户的事实，用于构建用户画像。",
            "",
            "=== 对话历史 ===",
            history_text,
        ]

        if existing_facts:
            parts += [
                "",
                "=== 已有的画像事实 ===",
                existing_facts,
            ]

        parts += [
            "",
            "=== 提取规则 ===",
            "1. 只提取明确提到或强烈暗示的事实，不要猜测。",
            "2. 事实类型包括：preference(偏好)、identity(身份)、habit(习惯)、emotion(情绪模式)。",
            "3. 如果对话中提到了已有事实的新证据，可以提高置信度。",
            "4. 如果新信息与已有事实矛盾，以新信息为准并标记旧事实为需更新。",
            "",
            "请用以下 JSON 格式输出（只输出 JSON，不要其他内容）：",
            "```json",
            "{",
            '  "facts": [',
            '    {"category": "preference", "content": "用户喜欢喝美式咖啡", "evidence": "用户说: 我每天早上都喝美式", "confidence": 0.9}',
            '  ]',
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

    def parse_result(self, user_id: str, llm_text: str) -> list[ProfileFact]:
        """解析 LLM 输出，写入画像事实"""
        data = self._extract_json(llm_text)
        facts_data = data.get("facts", [])

        results = []
        for f in facts_data:
            category = f.get("category", "auto")
            content = f.get("content", "")
            evidence = f.get("evidence", "")
            confidence = float(f.get("confidence", 1.0))

            if not content:
                continue

            fact = self.storage.add_profile_fact(
                user_id=user_id,
                category=category,
                content=content,
                evidence=evidence,
                confidence=confidence,
            )
            results.append(fact)

        return results

    def upsert_fact(self, user_id: str, category: str, content: str, evidence: str = "", confidence: float = 1.0) -> ProfileFact:
        """LLM 工具调用的入口：插入或更新一个认知记忆"""
        return self.storage.add_profile_fact(
            user_id=user_id,
            category=category,
            content=content,
            evidence=evidence,
            confidence=confidence,
        )

    def _extract_json(self, text: str) -> dict:
        """从 LLM 输出中提取 JSON"""
        pattern = r"```json\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = text[start:end + 1]
            else:
                json_str = text

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"facts": []}
