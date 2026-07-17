"""Small filesystem primitives with explicit same-object read semantics."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from pathlib import Path


def read_limited_regular_file(
    path: Path,
    *,
    max_bytes: int,
    enforce_limit: Callable[[int], None],
) -> tuple[bytes, Path]:
    """Read one resolved regular file through a single open descriptor.

    The returned path is an informational resolved name. Size inspection and
    content reading are both bound to the opened object.
    """

    resolved_path = path.resolve(strict=True)
    with resolved_path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode):
            raise OSError(f"{resolved_path} is not a regular file")
        enforce_limit(opened.st_size)
        content = stream.read(max_bytes + 1)
    enforce_limit(len(content))
    return content, resolved_path
