from pathlib import Path


class UnsafePathError(ValueError):
    pass


def safe_resolve(root: Path, requested: str | Path, must_exist: bool = False) -> Path:
    root = root.resolve()
    target = (
        (root / requested).resolve()
        if not Path(requested).is_absolute()
        else Path(requested).resolve()
    )
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise UnsafePathError(f"Path escapes approved root: {requested}") from exc
    if must_exist and not target.exists():
        raise FileNotFoundError(target)
    if target.exists() and target.is_symlink():
        resolved = target.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise UnsafePathError("Symlink escapes approved root") from exc
    return target
