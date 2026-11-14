"""Live model adapter for the Claude API. Synthetic data only.

NOT RUN: no API key was available when this was written. The adapter has been
exercised only against a mock client (tests/test_live.py). Treat its behaviour
against the real API as unverified until someone runs it.

It implements the same interface as `ScriptedModel`:
`respond(system, messages, tools) -> ModelTurn`. The agent loop, guardrails
and report do not change.
"""
import json

from .agent import MAX_OUTPUT_TOKENS, ModelTurn, tokens

DEFAULT_MODEL = "claude-opus-5-5"
# USD per token (input, output) at list price. Add a row before using another model.
PRICES = {"claude-opus-5-5": (4.0 / 1e6, 20.0 / 1e6), "claude-sonnet-5-5": (2.0 / 1e6, 10.0 / 1e6), "claude-haiku-5-5": (0.10 / 1e6, 0.50 / 1e6)}
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicModel:
    """Keeps its own append-only Anthropic-format history.

    The agent's transcript holds only text, tool names and model-facing tool
    results. The API needs the assistant's content blocks (thinking and
    tool_use included) sent back unchanged, so they are stored here verbatim.
    """

    def __init__(self, client=None, model=DEFAULT_MODEL, max_output_tokens=4000, effort="low"):
        if model not in PRICES:
            raise ValueError("No price on file for " + model + "; add it to PRICES so the cost cap stays meaningful.")
        if client is None:
            import anthropic  # optional dependency: pip install '.[live]'
            client = anthropic.Anthropic()
        self.client, self.model, self.effort = client, model, effort
        self.max_output_tokens = max_output_tokens  # read by the agent loop for the worst-case cost check
        self.price_in, self.price_out = PRICES[model]
        self._history, self._pending, self._consumed = [], [], 0

    @staticmethod
    def _tools(tools):
        return [{"name": t["name"], "description": t["description"], "strict": True,
                 "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}} for t in tools]

    def _absorb(self, messages):
        """Append messages the API has not seen yet. Tool results answer the pending tool_use ids, in order, in one user message."""
        new = messages[self._consumed:]
        self._consumed = len(messages)
        results = []
        for message in new:
            if message["role"] == "user":
                self._history.append({"role": "user", "content": message["content"]})
            elif message["role"] == "tool" and self._pending:
                results.append({"type": "tool_result", "tool_use_id": self._pending.pop(0), "content": json.dumps(message["content"], sort_keys=True)})
        for tool_use_id in self._pending:  # a call the loop never answered (limit reached); keep the history valid
            results.append({"type": "tool_result", "tool_use_id": tool_use_id, "content": "not run", "is_error": True})
        self._pending = []
        if results:
            self._history.append({"role": "user", "content": results})

    def estimate_input_tokens(self, system, messages, tools):
        """Server-side token count for the next request, used by the cost cap. Does not change the history."""
        pending, consumed, history = list(self._pending), self._consumed, list(self._history)
        try:
            self._absorb(messages)
            counted = self.client.messages.count_tokens(model=self.model, system=system, messages=self._history, tools=self._tools(tools))
            return counted.input_tokens
        except Exception:  # fall back to the offline estimate, padded, so the cap still errs on the safe side
            return 2 * (tokens(system) + tokens(messages) + tokens(tools))
        finally:
            self._pending, self._consumed, self._history = pending, consumed, history

    def respond(self, system, messages, tools):
        self._absorb(messages)
        response = self.client.beta.messages.create(
            model=self.model, max_tokens=self.max_output_tokens, system=system, messages=self._history,
            tools=self._tools(tools), output_config={"effort": self.effort},
            betas=[FALLBACK_BETA], fallbacks="default")
        self._history.append({"role": "assistant", "content": response.content})
        self._consumed += 1  # the agent loop appends its own assistant entry for this turn
        usage = response.usage
        turn = ModelTurn(
            input_tokens=usage.input_tokens + (getattr(usage, "cache_creation_input_tokens", 0) or 0) + (getattr(usage, "cache_read_input_tokens", 0) or 0),
            output_tokens=usage.output_tokens)
        if response.stop_reason == "tool_use":
            for block in response.content:
                if block.type == "tool_use":
                    turn.tool_calls.append(block.name)
                    self._pending.append(block.id)
        elif response.stop_reason == "end_turn":
            turn.text = " ".join(block.text for block in response.content if block.type == "text").strip()
        # refusal, max_tokens or anything else: no tool calls and no narrative, so the
        # run ends and every check without a result is reported as not run.
        return turn
