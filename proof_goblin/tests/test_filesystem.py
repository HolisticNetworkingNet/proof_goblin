from __future__ import annotations

import os
from pathlib import Path

import pytest

from proof_goblin.filesystem import read_limited_regular_file


@pytest.mark.skipif(
    os.name == "nt",
    reason="Windows does not permit replacing this test's open file",
)
def test_limited_read_remains_bound_to_opened_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = tmp_path / "selected.txt"
    replacement = tmp_path / "replacement.txt"
    selected.write_bytes(b"opened content")
    replacement.write_bytes(b"replacement content")
    real_fstat = os.fstat
    replaced = False

    def replace_after_open(descriptor: int) -> os.stat_result:
        nonlocal replaced
        if not replaced:
            os.replace(replacement, selected)
            replaced = True
        return real_fstat(descriptor)

    monkeypatch.setattr("proof_goblin.filesystem.os.fstat", replace_after_open)
    measurements: list[int] = []

    content, resolved = read_limited_regular_file(
        selected,
        max_bytes=100,
        enforce_limit=measurements.append,
    )

    assert content == b"opened content"
    assert selected.read_bytes() == b"replacement content"
    assert resolved == selected.resolve()
    assert measurements == [len(content), len(content)]


def test_limited_read_rejects_non_regular_path(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        read_limited_regular_file(
            tmp_path,
            max_bytes=100,
            enforce_limit=lambda measured: None,
        )
