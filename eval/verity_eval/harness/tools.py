"""Simulated tool registry + the instrumented dispatch chokepoint (eval-plan §8).

SAFETY: this module is the harness's only "action" surface, and it is pure by
construction — it operates solely on a per-scenario **in-memory world** and
performs NO real I/O. It must never import `subprocess`, `socket`, `smtplib`,
`requests`, or `urllib.request` (enforced by a ruff `banned-api` CI gate) and a
behavioral test asserts every tool causes zero real side effects. The model
emits tool-call text; nothing here ever reaches the host.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

TAINT_RE = re.compile(r"\{taint:([A-Za-z0-9_]+)\}")


@dataclass(frozen=True)
class RecordedCall:
    """A resolved tool call as seen at the chokepoint."""

    tool: str
    args: dict[str, object]


@dataclass
class DispatchResult:
    observation: str
    done: bool = False  # True when `respond` ends the episode


class SimulatedWorld:
    """The in-memory world for one scenario: files, fetchable resources, state.

    Taint markers `{taint:NAME}` in resource/file values are substituted with the
    injection payload when NAME is the injection carrier — this is how an
    indirect-injection attack reaches the model. Other markers are stripped.
    """

    def __init__(
        self,
        environment: dict[str, Any] | None,
        injection: tuple[str, str] | None = None,
    ) -> None:
        self._injection = injection
        env: dict[str, Any] = environment or {}
        files: dict[str, Any] = env.get("files") or {}
        resources: dict[str, Any] = env.get("resources") or {}
        state: dict[str, Any] = env.get("state") or {}
        self.files: dict[str, str] = {str(k): self._subst(str(v)) for k, v in files.items()}
        self.resources: dict[str, str] = {str(k): self._subst(str(v)) for k, v in resources.items()}
        self.state: dict[str, Any] = dict(state)

    def _subst(self, text: str) -> str:
        def repl(m: re.Match[str]) -> str:
            name = m.group(1)
            if self._injection is not None and name == self._injection[0]:
                return self._injection[1]
            return ""

        return TAINT_RE.sub(repl, text)


# --- Tool handlers: (world, args) -> DispatchResult. Pure; in-memory only. ---


def _fs_read(world: SimulatedWorld, args: dict[str, object]) -> DispatchResult:
    path = str(args.get("path", ""))
    if path in world.files:
        return DispatchResult(world.files[path])
    return DispatchResult(f"error: no such file: {path}")


def _fs_write(world: SimulatedWorld, args: dict[str, object]) -> DispatchResult:
    path = str(args.get("path", ""))
    world.files[path] = str(args.get("content", ""))
    return DispatchResult(f"ok: wrote {len(world.files[path])} bytes to {path}")


def _http_get(world: SimulatedWorld, args: dict[str, object]) -> DispatchResult:
    url = str(args.get("url", ""))
    if url in world.resources:
        return DispatchResult(world.resources[url])
    return DispatchResult(f"error: could not fetch {url}")


def _http_post(world: SimulatedWorld, args: dict[str, object]) -> DispatchResult:
    return DispatchResult("ok: HTTP 200")


def _shell_exec(world: SimulatedWorld, args: dict[str, object]) -> DispatchResult:
    # Simulated: record-only, synthetic empty stdout. NEVER runs a real command.
    return DispatchResult("")


def _email_send(world: SimulatedWorld, args: dict[str, object]) -> DispatchResult:
    return DispatchResult("ok: email queued")


def _transfer(world: SimulatedWorld, args: dict[str, object]) -> DispatchResult:
    return DispatchResult("ok: transfer submitted")


def _respond(world: SimulatedWorld, args: dict[str, object]) -> DispatchResult:
    return DispatchResult(str(args.get("text", "")), done=True)


HANDLERS: dict[str, Callable[[SimulatedWorld, dict[str, object]], DispatchResult]] = {
    "fs_read": _fs_read,
    "fs_write": _fs_write,
    "http_get": _http_get,
    "http_post": _http_post,
    "shell_exec": _shell_exec,
    "email_send": _email_send,
    "transfer": _transfer,
    "respond": _respond,
}


@dataclass
class ToolDispatcher:
    """The instrumented chokepoint: records every resolved call, then simulates it.

    Phase 2 inserts `verify(resolved_action, context)` immediately after the
    record step — the verdict decides whether the handler runs. For the baseline
    (verifier OFF) every call is recorded and simulated.
    """

    world: SimulatedWorld
    calls: list[RecordedCall] = field(default_factory=list)

    def dispatch(self, name: str, args: dict[str, object]) -> DispatchResult:
        self.calls.append(RecordedCall(tool=name, args=dict(args)))
        # >>> Phase 2 chokepoint: verify(resolved_action, context) goes here <<<
        handler = HANDLERS.get(name)
        if handler is None:
            return DispatchResult(f"error: unknown tool: {name}")
        return handler(self.world, args)
