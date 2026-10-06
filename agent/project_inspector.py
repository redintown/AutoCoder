from pathlib import Path


IGNORED_DIRECTORIES = {
    ".git",
    ".next",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "__pycache__",
    ".idea",
    ".vscode",
}


IMPORTANT_FILES = {
    "package.json",
    "tsconfig.json",
    "jsconfig.json",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "vite.config.js",
    "vite.config.ts",
    "requirements.txt",
    "pyproject.toml",
    "README.md",
    "docker-compose.yml",
    "Dockerfile",
}


SOURCE_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".java",
    ".c",
    ".cpp",
    ".cc",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".html",
    ".css",
    ".scss",
    ".sql",
}


MAX_FILE_SIZE = 100_000
MAX_SOURCE_FILES = 30


def should_ignore(path: Path) -> bool:

    for part in path.parts:

        if part in IGNORED_DIRECTORIES:
            return True

        if part.startswith(".env"):
            return True

    return False


def get_project_tree(
    project_path: str,
    max_depth: int = 4
) -> str:

    root = Path(project_path).resolve()

    if not root.exists():
        raise FileNotFoundError(
            f"Project does not exist: {root}"
        )

    if not root.is_dir():
        raise ValueError(
            f"Project path is not a directory: {root}"
        )

    lines = [
        f"PROJECT: {root}"
    ]

    def walk(
        directory: Path,
        prefix: str,
        depth: int
    ):

        if depth > max_depth:
            return

        try:
            entries = sorted(
                directory.iterdir(),
                key=lambda p: (
                    p.is_file(),
                    p.name.lower()
                )
            )

        except PermissionError:
            return

        visible_entries = [
            entry
            for entry in entries
            if not should_ignore(
                entry.relative_to(root)
            )
        ]

        for index, entry in enumerate(
            visible_entries
        ):

            is_last = (
                index == len(visible_entries) - 1
            )

            connector = (
                "└── "
                if is_last
                else "├── "
            )

            lines.append(
                prefix
                + connector
                + entry.name
            )

            if entry.is_dir():

                next_prefix = (
                    prefix
                    + (
                        "    "
                        if is_last
                        else "│   "
                    )
                )

                walk(
                    entry,
                    next_prefix,
                    depth + 1
                )

    walk(
        root,
        "",
        0
    )

    return "\n".join(lines)


def find_important_files(
    project_path: str
) -> list[str]:

    root = Path(project_path).resolve()

    found = []

    for path in root.rglob("*"):

        if not path.is_file():
            continue

        relative = path.relative_to(root)

        if should_ignore(relative):
            continue

        if path.name in IMPORTANT_FILES:

            found.append(
                str(relative)
            )

    return sorted(found)


def find_source_files(
    project_path: str
) -> list[Path]:

    root = Path(project_path).resolve()

    source_files = []

    for path in root.rglob("*"):

        if not path.is_file():
            continue

        relative = path.relative_to(root)

        if should_ignore(relative):
            continue

        if path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue

        try:
            size = path.stat().st_size
        except OSError:
            continue

        if size > MAX_FILE_SIZE:
            continue

        source_files.append(path)

    source_files.sort(
        key=lambda p: (
            0
            if p.name in IMPORTANT_FILES
            else 1,
            str(p).lower()
        )
    )

    return source_files[:MAX_SOURCE_FILES]


def read_file(
    path: Path,
    root: Path
) -> str:

    try:

        content = path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        try:

            content = path.read_text(
                encoding="utf-8",
                errors="replace"
            )

        except Exception:
            return "[Unable to read file]"

    except Exception as error:

        return (
            f"[Unable to read file: {error}]"
        )

    relative = path.relative_to(root)

    return (
        f"\n"
        f"===== FILE: {relative} =====\n"
        f"{content}\n"
        f"===== END FILE: {relative} =====\n"
    )


def get_source_context(
    project_path: str
) -> str:

    root = Path(project_path).resolve()

    files = find_source_files(
        project_path
    )

    if not files:

        return (
            "=== SOURCE CODE ===\n"
            "No readable source files found."
        )

    sections = [
        "=== SOURCE CODE ==="
    ]

    for path in files:

        sections.append(
            read_file(
                path,
                root
            )
        )

    return "\n".join(sections)


def inspect_project(
    project_path: str
) -> str:

    tree = get_project_tree(
        project_path
    )

    important_files = find_important_files(
        project_path
    )

    source_context = get_source_context(
        project_path
    )

    report = [
        "=== PROJECT INSPECTION ===",
        "",
        tree,
        "",
        "=== IMPORTANT FILES ===",
    ]

    if important_files:

        report.extend(
            f"- {file}"
            for file in important_files
        )

    else:

        report.append(
            "- None detected"
        )

    report.append("")
    report.append(
        source_context
    )

    return "\n".join(report)