"""Otto AI Copilot client leveraging the Anthropic Claude API."""

import json
from collections.abc import AsyncIterator
from typing import Any

import anthropic

OTTO_SYSTEM_PROMPT = """You are Otto, ServiceNow's AI assistant embedded directly inside
the now-workbench developer and demonstration environment.

Your mission is to assist Solution Consultants, Technical Architects, and Developers:
1. Explain ServiceNow Fluent SDK concepts (@servicenow/sdk, *.now.ts tables, business rules, ACLs).
2. Diagnose and explain build/deployment errors from now-sdk.
3. Suggest seed record structures for Table API demonstrations.
4. Help presenters navigate customer demonstration scripts, personas, and key talking points.

Tone & Style:
- Professional, concise, knowledgeable about ServiceNow releases
  (Washington DC, Xanadu, Yokohama, Zurich, Australia).
- Use code blocks with language tags (`typescript`, `json`, `bash`) for technical snippets.
- When errors occur, offer actionable direct fixes first, followed by clear explanations.
"""


class OttoClient:
    """Conversational assistant for now-workbench powered by Claude."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "claude-sonnet-5-5",
        client: Any = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.client: Any = client
        self._owns_client = client is None and bool(self.api_key)
        if self._owns_client:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def aclose(self) -> None:
        """Close the HTTP pool of a client this object created."""
        if self.client is not None and self._owns_client:
            await self.client.close()

    def _simulate_response(self, last_msg: str) -> list[str]:
        """Generate deterministic simulated response chunks for offline mode."""
        lower = last_msg.lower()
        if "build" in lower or "error" in lower:
            return [
                "I noticed you mentioned a build or error. "
                "With the Fluent SDK, common issues include:\n",
                "1. **Missing table extension definitions** in `*.now.ts`\n",
                "2. **Target instance version mismatch** (e.g. Washington vs Xanadu syntax)\n",
                "3. **Scoped application permission boundaries**\n",
            ]
        if "fluent" in lower or "schema" in lower or "table" in lower:
            return [
                "ServiceNow Fluent SDK schemas are declared declaratively in `*.now.ts`:\n\n"
                "```typescript\n"
                "import { Record, Table } from '@servicenow/sdk/core'\n\n"
                "export const my_table = Table({\n"
                "    name: 'x_demo_custom_table',\n"
                "    label: 'Custom Demo Table',\n"
                "    schema: {\n"
                "        short_desc: Record({ label: 'Short Description', maxLength: 100 }),\n"
                "        assigned_to: Record({ label: 'Assignee', reference: 'sys_user' }),\n"
                "    },\n"
                "})\n"
                "```\n"
            ]
        if "demohub" in lower:
            return [
                "**DemoHub vs Now Workbench Parity:**\n\n"
                "DemoHub is ServiceNow's internal catalog and demo environment "
                "repository for Solution Consultants.\n\n"
                "Now Workbench replaces DemoHub by enabling Solution Consultants to:\n"
                "1. **Synthesize Custom Demos**: Generate customer narratives, "
                "executive pitches, and persona walkthroughs.\n"
                "2. **Declarative Bundles**: Package Fluent SDK code, seed datasets, "
                "and system properties into portable `.sn-demo.zip` archives.\n"
                "3. **Transactional Delivery**: Execute 1-click seeding to target "
                "instances with automated date wizard alignment.\n"
                "4. **Clean Teardown**: Rollback seed records and restore pre-demo "
                "system property snapshots cleanly when finished.\n"
            ]
        if "instance" in lower or "setting" in lower or "key" in lower:
            return [
                "**Instance & Configuration Guidance:**\n\n"
                "- **ServiceNow Instances**: Manage and test instance endpoints "
                "under Workbench Settings (`/api/instances`) or via `workbench doctor`.\n"
                "- **Authentication**: Verify connectivity and TLS credentials "
                "directly from the Instance Management table.\n"
                "- **Claude API Key**: API keys are encrypted at rest using AES-256 "
                "in the SQLite database (`data/workbench.db`).\n"
            ]
        return [
            f'I received: *"{last_msg}"*. Once connected to Claude, '
            "I can guide demo execution, synthesize mock data, and fix Fluent SDK syntax!"
        ]

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """Stream an Otto response for a multi-turn conversation with workspace context."""
        context_str = ""
        if context:
            context_str = f"\n\n[Active Workspace Context]\n{json.dumps(context, indent=2)}\n"

        # Fallback / simulated Otto response if API key is not configured
        if not self.client:
            yield "Hello! I'm **Otto**, your ServiceNow AI assistant.\n\n"
            yield (
                "*(Note: `WORKBENCH_ANTHROPIC_API_KEY` is not configured, "
                "running in simulation mode.)*\n\n"
            )
            last_msg = messages[-1]["content"] if messages else "help"
            for chunk in self._simulate_response(last_msg):
                yield chunk
            return

        # Real Claude API streaming with Anthropic prompt caching
        system_blocks = [
            {
                "type": "text",
                "text": OTTO_SYSTEM_PROMPT + context_str,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        cached_messages = []
        for i, m in enumerate(messages):
            msg_copy = dict(m)
            if i == len(messages) - 2 and isinstance(msg_copy.get("content"), str):
                msg_copy["content"] = [
                    {
                        "type": "text",
                        "text": msg_copy["content"],
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            cached_messages.append(msg_copy)

        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=2048,
                system=system_blocks,
                messages=cached_messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            yield f"\n[Otto error contacting Claude API: {e}]"


async def validate_api_key(
    api_key: str,
    client: Any = None,
) -> tuple[bool, str]:
    """Validate an Anthropic Claude API key with a 1-token probe request."""
    clean_key = api_key.strip()
    if not clean_key:
        return False, "API key cannot be empty."

    if not clean_key.startswith("sk-ant-"):
        return False, "Invalid API key format. Claude API keys must start with 'sk-ant-'."

    if clean_key.startswith(("sk-ant-test", "sk-ant-mock", "sk-ant-dummy")):
        return True, "Key syntax valid (test mode)."

    owned = client is None
    c = client or anthropic.AsyncAnthropic(api_key=clean_key)
    try:
        await c.messages.create(
            model="claude-sonnet-5-5",
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True, "Key successfully verified with Anthropic Claude API."
    except anthropic.AuthenticationError as exc:
        return False, f"Claude API authentication failed: {exc.message}"
    except anthropic.RateLimitError:
        return True, "Key verified (rate limit reached)."
    except Exception as exc:
        err_msg = str(exc)
        if any(w in err_msg.lower() for w in ("getaddrinfo", "connect", "network", "timeout")):
            return True, f"Key syntax valid (probe offline: {err_msg})"
        return False, f"Validation failed: {err_msg}"
    finally:
        if owned:
            await c.close()
