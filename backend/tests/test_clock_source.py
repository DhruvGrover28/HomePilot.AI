from pathlib import Path


def test_direct_datetime_now_is_only_in_clock_module():
    root = Path(__file__).parents[1] / "app"
    for path in root.rglob("*.py"):
        if path.name == "clock.py":
            continue
        assert "datetime.now(" not in path.read_text(encoding="utf-8")
        assert "datetime.utcnow(" not in path.read_text(encoding="utf-8")
