"""Otto AI Copilot client leveraging the Anthropic Claude API."""

import json
from collections.abc import AsyncIterator
from typing import Any
import anthropic


OTTO_SYSTEM_PROMPT = """You are Otto, ServiceNow's AI assistant embedded directly inside the now-workbench developer and demonstration environment.

Your mission is to assist Solution Consultants, Technical Architects, and Developers:
1. Explain ServiceNow Fluent SDK concepts (@servicenow/sdk, *.now.ts tables, business rules, ACLs).
2. Diagnose and explain build/deployment errors from now-sdk.
3. Suggest seed record structures for Table API demonstrations.
4. Help presenters navigate customer demonstration scripts, personas, and key talking points.

Tone & Style:
- Professional, concise, knowledgeable about ServiceNow releases (Washington DC, Xanadu, Yokohama).
- Use code blocks with language tags (`typescript`, `json`, `bash`) for technical snippets.
- When errors occur, offer actionable direct fixes first, followed by clear explanations.
"""


class OttoClient:
    """Conversational assistant for now-workbench powered by Claude."""

    def __init__(self, api_key: str = "", model: str = "claude-3-7-sonnet-20250219") -> None:
        self.api_key = api_key
        self.model = model
        self.client: anthropic.AsyncAnthropic | None = None
        if self.api_key:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """Stream an Otto response for a multi-turn conversation with workspace context."""
        context_str = ""
        if context:
            context_str = f"\n\n[Active Workspace Context]\n{json.dumps(context, indent=2)}\n"

        system = OTTO_SYSTEM_PROMPT + context_str

        # Fallback / simulated Otto response if API key is not configured
        if not self.client:
            yield "Hello! I'm **Otto**, your ServiceNow AI assistant.\n\n"
            yield "*(Note: `WORKBENCH_ANTHROPIC_API_KEY` is not configured, running in simulation mode.)*\n\n"
            last_msg = messages[-1]["content"] if messages else "help"
            if "build" in last_msg.lower() or "error" in last_msg.lower():
                yield "I noticed you mentioned a build or error. With the Fluent SDK, common issues include:\n"
                yield "1. **Missing table extension definitions** in `*.now.ts`\n"
                yield "2. **Target instance version mismatch** (e.g. Washington vs Xanadu syntax)\n"
                yield "3. **Scoped application permission boundaries**\n"
            else:
                yield f"I received: *\"{last_msg}\"*. Once connected to Claude, I can guide demo execution, synthesize mock data, and fix Fluent SDK syntax!"
            return

        # Real Claude API streaming
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=2048,
                system=system,
                messages=messages,  # type: ignore[arg-type]
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            yield f"\n[Otto error contacting Claude API: {e}]"
