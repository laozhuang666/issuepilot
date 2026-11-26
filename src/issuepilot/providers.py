import json
from typing import Any, Protocol

from openai import AsyncOpenAI

from issuepilot.agent_tools import CHAT_TOOL_DEFINITIONS, TOOL_DEFINITIONS, AgentToolbox
from issuepilot.config import Settings


class AgentProvider(Protocol):
    name: str

    async def complete(
        self,
        prompt: dict[str, Any],
        instructions: str,
        toolbox: AgentToolbox,
    ) -> str: ...


class OpenAIResponsesAgent:
    name = "openai"

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self.client = client or AsyncOpenAI(api_key=settings.effective_api_key)

    async def complete(
        self,
        prompt: dict[str, Any],
        instructions: str,
        toolbox: AgentToolbox,
    ) -> str:
        response = await self.client.responses.create(
            model=self.settings.effective_model,
            instructions=instructions,
            input=json.dumps(prompt, ensure_ascii=False),
            tools=TOOL_DEFINITIONS,
        )

        for round_number in range(self.settings.max_agent_rounds + 1):
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                return response.output_text
            if round_number == self.settings.max_agent_rounds:
                break

            outputs = []
            for index, call in enumerate(calls):
                result = await self._execute_call(
                    toolbox,
                    round_number + 1,
                    index,
                    call.name,
                    call.arguments,
                )
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": result,
                    }
                )
            response = await self.client.responses.create(
                model=self.settings.effective_model,
                previous_response_id=response.id,
                input=outputs,
                tools=TOOL_DEFINITIONS,
            )

        raise ValueError("The analysis agent exceeded its tool-call round limit.")

    async def _execute_call(
        self,
        toolbox: AgentToolbox,
        round_number: int,
        index: int,
        name: str,
        arguments: str,
    ) -> str:
        if index >= self.settings.max_agent_calls_per_round:
            return "Error: per-round tool-call limit exceeded."
        return await toolbox.execute(round_number, name, arguments)


class ChatCompletionsAgent:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self.name = settings.llm_provider
        self.client = client or AsyncOpenAI(
            api_key=settings.effective_api_key or "ollama",
            base_url=settings.effective_base_url,
        )

    async def complete(
        self,
        prompt: dict[str, Any],
        instructions: str,
        toolbox: AgentToolbox,
    ) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ]

        for round_number in range(self.settings.max_agent_rounds + 1):
            response = await self.client.chat.completions.create(
                model=self.settings.effective_model,
                messages=messages,
                tools=CHAT_TOOL_DEFINITIONS,
                tool_choice="auto",
            )
            message = response.choices[0].message
            calls = message.tool_calls or []
            if not calls:
                if not isinstance(message.content, str) or not message.content.strip():
                    raise ValueError("The model returned neither tool calls nor a final plan.")
                return message.content
            if round_number == self.settings.max_agent_rounds:
                break

            messages.append(self._assistant_message(message))
            for index, call in enumerate(calls):
                result = await self._execute_call(
                    toolbox,
                    round_number + 1,
                    index,
                    call.function.name,
                    call.function.arguments,
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    }
                )

        raise ValueError("The analysis agent exceeded its tool-call round limit.")

    async def _execute_call(
        self,
        toolbox: AgentToolbox,
        round_number: int,
        index: int,
        name: str,
        arguments: str,
    ) -> str:
        if index >= self.settings.max_agent_calls_per_round:
            return "Error: per-round tool-call limit exceeded."
        return await toolbox.execute(round_number, name, arguments)

    @staticmethod
    def _assistant_message(message: Any) -> dict[str, Any]:
        tool_calls = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls or []
        ]
        return {
            "role": "assistant",
            "content": message.content,
            "tool_calls": tool_calls,
        }


def build_agent_provider(settings: Settings, client: Any | None = None) -> AgentProvider | None:
    if not settings.agent_enabled:
        return None
    if settings.llm_provider == "openai":
        return OpenAIResponsesAgent(settings, client)
    return ChatCompletionsAgent(settings, client)
