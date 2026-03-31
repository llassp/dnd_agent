import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class LLMResult:
    content: str
    raw_response: dict[str, Any]
    model: str
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class CitationContext:
    chunk_id: str
    source_title: str
    snippet: str
    score: float | None = None


@dataclass
class EvidenceBundle:
    query: str
    citations: list[CitationContext]
    agent_type: str


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        raise NotImplementedError

    @abstractmethod
    async def generate_with_citations(
        self,
        evidence_bundle: EvidenceBundle,
        task_prompt: str,
        mode: str,
    ) -> LLMResult:
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        base_url: str | None = None,
    ):
        import httpx

        self.api_key = api_key or settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or settings.llm_model
        self.temperature = temperature or settings.llm_temperature
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.base_url = base_url or settings.openai_base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        import httpx

        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            return LLMResult(
                content=data["choices"][0]["message"]["content"],
                raw_response=data,
                model=data.get("model", self.model),
                usage=data.get("usage", {}),
            )
        except httpx.HTTPStatusError as e:
            logger.error("openai_api_error", status=e.response.status_code, detail=e.response.text)
            raise RuntimeError(f"OpenAI API error: {e.response.status_code}")
        except Exception as e:
            logger.error("openai_generation_error", error=str(e))
            raise

    async def generate_with_citations(
        self,
        evidence_bundle: EvidenceBundle,
        task_prompt: str,
        mode: str,
    ) -> LLMResult:
        system_prompt = self._build_citation_system_prompt(mode)
        evidence_text = self._format_evidence(evidence_bundle)

        user_message = f"""Task: {task_prompt}

Evidence:
{evidence_text}

Remember:
- Answer based ONLY on the evidence provided above
- If evidence is insufficient, say so and ask for clarification
- Always cite your sources
- Format your response with Conclusion, Evidence, and DM Adjudication Note sections"""

        messages = [{"role": "user", "content": user_message}]
        return await self.generate(messages, system_prompt)

    def _build_citation_system_prompt(self, mode: str) -> str:
        base = """You are a helpful D&D Game Master assistant.

CRITICAL RULES:
1. NEVER fabricate rule text or citations. Only use information from the provided evidence.
2. If evidence is unclear or insufficient, state that you cannot answer confidently.
3. Always format responses with these sections:
   - **Conclusion**: Your direct answer
   - **Evidence**: Summary of supporting citations (use source titles)
   - **DM Adjudication Note**: Only if there is ambiguity, rule conflict, or low confidence

4. Keep snippets brief (under 200 characters each)."""

        if mode == "rules":
            return base + "\n\nYou are answering a RULES question. Be precise and cite specific rules."
        elif mode == "narrative":
            return base + "\n\nYou are providing NARRATIVE content. Describe scenes vividly using the provided lore."
        elif mode == "encounter":
            return base + "\n\nYou are handling an ENCOUNTER. Provide combat tactics and monster information."
        elif mode == "state":
            return base + "\n\nYou are updating WORLD STATE. Summarize what changed."
        return base

    def _format_evidence(self, bundle: EvidenceBundle) -> str:
        if not bundle.citations:
            return "No evidence available."

        lines = []
        for i, citation in enumerate(bundle.citations, 1):
            lines.append(
                f"{i}. [{citation.source_title}] (chunk: {citation.chunk_id[:8]}...)\n"
                f"   \"{citation.snippet[:200]}...\""
            )
        return "\n".join(lines)


class AnthropicProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        import httpx

        self.api_key = api_key or settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model or settings.llm_model
        self.temperature = temperature or settings.llm_temperature
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        import httpx

        if system_prompt:
            system = [{"type": "text", "text": system_prompt}]
        else:
            system = None

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        if system:
            payload["system"] = system

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        try:
            response = await self.client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            return LLMResult(
                content=data["content"][0]["text"],
                raw_response=data,
                model=data.get("model", self.model),
                usage={
                    "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": data.get("usage", {}).get("output_tokens", 0),
                },
            )
        except httpx.HTTPStatusError as e:
            logger.error("anthropic_api_error", status=e.response.status_code)
            raise RuntimeError(f"Anthropic API error: {e.response.status_code}")
        except Exception as e:
            logger.error("anthropic_generation_error", error=str(e))
            raise

    async def generate_with_citations(
        self,
        evidence_bundle: EvidenceBundle,
        task_prompt: str,
        mode: str,
    ) -> LLMResult:
        system_prompt = self._build_citation_system_prompt(mode)
        evidence_text = self._format_evidence(evidence_bundle)

        user_message = f"""Task: {task_prompt}

Evidence:
{evidence_text}

Remember to answer based ONLY on the evidence provided. If insufficient, say so."""

        return await self.generate([{"role": "user", "content": user_message}], system_prompt)

    def _build_citation_system_prompt(self, mode: str) -> str:
        base = """You are a D&D Game Master assistant. Never fabricate information.

Format your response with:
- **Conclusion**: Direct answer
- **Evidence**: Citation summaries  
- **DM Adjudication Note**: Only when needed"""

        if mode == "rules":
            return base + "\n\nAnswering a RULES question. Be precise."
        elif mode == "narrative":
            return base + "\n\nProviding NARRATIVE content. Describe vividly."
        elif mode == "encounter":
            return base + "\n\nHandling ENCOUNTER. Give tactical advice."
        elif mode == "state":
            return base + "\n\nUpdating WORLD STATE."
        return base

    def _format_evidence(self, bundle: EvidenceBundle) -> str:
        if not bundle.citations:
            return "No evidence available."

        lines = []
        for i, citation in enumerate(bundle.citations, 1):
            lines.append(
                f"{i}. [{citation.source_title}]\n   \"{citation.snippet[:200]}...\""
            )
        return "\n".join(lines)


class StubProvider(LLMProvider):
    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResult:
        logger.warning("using_stub_llm_provider")
        return LLMResult(
            content="[Stub Response] LLM provider not configured. Please set LLM_PROVIDER environment variable.",
            raw_response={},
            model="stub",
        )

    async def generate_with_citations(
        self,
        evidence_bundle: EvidenceBundle,
        task_prompt: str,
        mode: str,
    ) -> LLMResult:
        return await self.generate([], f"{task_prompt}\n\nEvidence: {len(evidence_bundle.citations)} citations available.")


class LLMProviderFactory:
    @staticmethod
    def from_env() -> LLMProvider:
        provider = settings.llm_provider.lower()

        if provider == "openai":
            return OpenAIProvider()
        elif provider == "anthropic":
            return AnthropicProvider()
        else:
            logger.warning("llm_provider_not_configured_using_stub", provider=provider)
            return StubProvider()
