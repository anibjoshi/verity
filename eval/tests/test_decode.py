import pytest
from verity_eval.harness.decode import profile_for, recover_from_content, safe_json_args


def test_profile_qwen() -> None:
    assert profile_for("Qwen/Qwen2.5-3B-Instruct").tool_parser == "hermes"


def test_profile_hermes_vs_llama() -> None:
    assert profile_for("NousResearch/Hermes-3-Llama-3.2-3B").tool_parser == "hermes"
    assert profile_for("meta-llama/Llama-3.2-3B-Instruct").tool_parser == "llama3_json"


def test_profile_gemma_and_phi() -> None:
    assert profile_for("google/gemma-4-E4B-it").tool_parser == "gemma4"
    assert profile_for("microsoft/Phi-4-mini-instruct").tool_parser == "phi4_mini_json"


def test_profile_unknown_raises() -> None:
    with pytest.raises(KeyError):
        profile_for("mistralai/Mistral-7B-Instruct")


def test_safe_json_args() -> None:
    assert safe_json_args('{"a": 1}') == {"a": 1}
    assert safe_json_args({"a": 1}) == {"a": 1}
    assert safe_json_args("not json") == {}
    assert safe_json_args("[1,2]") == {}  # non-object JSON → {}


def test_recover_call_leaked_into_content() -> None:
    recovered = recover_from_content('Sure: {"name": "fs_read", "arguments": {"path": "/k"}}')
    assert recovered == ("fs_read", {"path": "/k"})


def test_recover_handles_parameters_key() -> None:
    recovered = recover_from_content('{"name": "transfer", "parameters": {"amount_cents": 5}}')
    assert recovered == ("transfer", {"amount_cents": 5})


def test_recover_none_when_no_call() -> None:
    assert recover_from_content("just a plain answer") is None
    assert recover_from_content(None) is None
