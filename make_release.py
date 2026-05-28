from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "SmartLecture_release.zip"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".vscode",
    ".idea",
    "node_modules",
}

EXCLUDED_FILES = {"SmartLecture_release.zip"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".log", ".sqlite", ".sqlite3", ".db", ".zip"}


def is_env_file(path: Path) -> bool:
    return path.name == ".env" or (path.suffix == ".env" and path.name != ".env.example")


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return True
    if path.name in EXCLUDED_FILES:
        return True
    if is_env_file(path):
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    if len(rel.parts) >= 2 and rel.parts[0] == "instance" and path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
        return True
    return False


def scan_warnings():
    warnings = []
    if (ROOT / ".env").exists():
        warnings.append(".env found in source tree")
    database_files = [
        path.relative_to(ROOT)
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}
        and ".git" not in path.parts
        and ".venv" not in path.parts
    ]
    if database_files:
        warnings.append("database files found: " + ", ".join(str(path) for path in database_files[:8]))
    return warnings


def build_release():
    if OUTPUT.exists():
        OUTPUT.unlink()

    file_count = 0
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in ROOT.rglob("*"):
            if path.is_dir() or should_skip(path):
                continue
            archive.write(path, path.relative_to(ROOT))
            file_count += 1

    print(f"Archive: {OUTPUT.name}")
    print(f"Files: {file_count}")
    print("Excluded directories: " + ", ".join(sorted(EXCLUDED_DIRS)))
    warnings = scan_warnings()
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("Warnings: none")


if __name__ == "__main__":
    build_release()
