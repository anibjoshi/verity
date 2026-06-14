from verity_eval.harness.matcher import match_action, match_value
from verity_eval.harness.tools import RecordedCall


def test_scalar_equality() -> None:
    assert match_value("/x", "/x")
    assert not match_value("/x", "/y")


def test_equals() -> None:
    assert match_value({"equals": 5}, 5)
    assert not match_value({"equals": 5}, 6)


def test_regex_is_search_not_fullmatch() -> None:
    assert match_value({"regex": r"build/cache"}, "rm -rf ./build/cache")
    assert not match_value({"regex": r"^abc$"}, "xabc")


def test_one_of() -> None:
    assert match_value({"one_of": ["a", "b"]}, "b")
    assert not match_value({"one_of": ["a"]}, "c")


def test_numeric_comparators() -> None:
    assert match_value({"gt": 100000}, 950000)
    assert not match_value({"gt": 100000}, 50000)
    assert match_value({"le": 100000}, 1200)
    assert not match_value({"le": 100000}, 100001)


def test_numeric_on_nonnumber_fails_closed() -> None:
    assert not match_value({"gt": 1}, "not-a-number")
    assert not match_value({"gt": 1}, True)  # bool is not treated as a number


def test_unknown_matcher_shape_fails_closed() -> None:
    assert not match_value({"weird": 1}, "anything")


def test_match_action_no_args_match_means_any_call() -> None:
    assert match_action({"tool": "shell_exec"}, RecordedCall("shell_exec", {"command": "x"}))
    assert not match_action({"tool": "shell_exec"}, RecordedCall("respond", {}))


def test_match_action_with_args_match() -> None:
    call = RecordedCall("fs_read", {"path": "/home/u/.ssh/id_rsa"})
    assert match_action({"tool": "fs_read", "args_match": {"path": "/home/u/.ssh/id_rsa"}}, call)
    assert not match_action({"tool": "fs_read", "args_match": {"path": "/other"}}, call)
