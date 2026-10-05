from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.security import resolve_static

def _tree(tmp_path):
    root = tmp_path / "frontend_dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("spa", encoding="utf-8")
    (root / "assets" / "app.js").write_text("js", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=dummy", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    return root

def test_normal_files_are_served(tmp_path):
    root = _tree(tmp_path)
    assert resolve_static(root, "index.html") == (root / "index.html").resolve()
    assert resolve_static(root, "assets/app.js") == (root / "assets" / "app.js").resolve()

def test_parent_directory_is_blocked(tmp_path):
    root = _tree(tmp_path)
    for rel in ("../.env", "../secret.txt", "assets/../../.env", "../../../../etc/passwd", "..\\..\\.env"):
        assert resolve_static(root, rel) is None

def test_absolute_path_is_blocked(tmp_path):
    root = _tree(tmp_path)
    assert resolve_static(root, str(tmp_path / ".env")) is None
    assert resolve_static(root, "/etc/passwd") is None

def test_odd_input_does_not_crash(tmp_path):
    root = _tree(tmp_path)
    assert resolve_static(root, "bad\x00name") is None
    assert resolve_static(root, "") is None
    assert resolve_static(root, "no/such/file.js") is None

def test_symlink_out_of_root_is_blocked(tmp_path):
    root = _tree(tmp_path)
    link = root / "link.txt"
    try:
        link.symlink_to(tmp_path / "secret.txt")
    except (OSError, NotImplementedError):
        return
    assert resolve_static(root, "link.txt") is None

print("Traversal protection installed")
