import hashlib
import sys
from pathlib import Path

# Allow importing git_manager.py from the same agent folder
AGENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(AGENT_DIR))

from git_manager import (
    ensure_clean_repository,
    create_checkpoint,
    rollback,
    get_current_commit,
)


def sha256(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest().upper()


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print(
            r'python rollback_test.py "C:\path\to\test-project"'
        )
        return

    project_path = Path(sys.argv[1]).resolve()
    app_file = project_path / "src" / "app.js"

    print("=" * 60)
    print("AUTOCODER - GIT ROLLBACK TEST")
    print("=" * 60)

    print(f"\nProject:")
    print(project_path)

    if not project_path.exists():
        print("\nERROR: Project does not exist.")
        return

    if not app_file.exists():
        print("\nERROR: src/app.js does not exist.")
        return

    # ---------------------------------------------------------
    # STEP 1: Verify clean repository
    # ---------------------------------------------------------
    print("\n[1/6] Checking clean Git repository...")

    try:
        ensure_clean_repository(str(project_path))
    except Exception as error:
        print("\nGit safety check failed:")
        print(error)
        return

    print("Repository is clean.")

    # ---------------------------------------------------------
    # STEP 2: Capture baseline
    # ---------------------------------------------------------
    print("\n[2/6] Capturing baseline...")

    baseline_commit = get_current_commit(str(project_path))
    baseline_hash = sha256(app_file)

    print(f"Baseline commit:")
    print(baseline_commit)

    print("\nBaseline SHA-256:")
    print(baseline_hash)

    # ---------------------------------------------------------
    # STEP 3: Create AutoCoder checkpoint
    # ---------------------------------------------------------
    print("\n[3/6] Creating AutoCoder checkpoint...")

    try:
        checkpoint = create_checkpoint(
            str(project_path),
            "AutoCoder rollback test checkpoint"
        )
    except Exception as error:
        print("\nCheckpoint creation failed:")
        print(error)
        return

    print("\nCheckpoint created successfully.")
    print(f"Rollback target:")
    print(checkpoint)

    # ---------------------------------------------------------
    # STEP 4: Make controlled destructive change
    # ---------------------------------------------------------
    print("\n[4/6] Creating controlled test failure...")

    original = app_file.read_text(encoding="utf-8")

    expected_line = "title = title.trim();"
    broken_line = "title = title.toUpperCase();"

    if expected_line not in original:
        print(
            "\nERROR: Expected source line was not found:"
        )
        print(expected_line)
        return

    modified = original.replace(
        expected_line,
        broken_line,
        1
    )

    app_file.write_text(
        modified,
        encoding="utf-8"
    )

    changed_hash = sha256(app_file)

    print("\nControlled change applied:")
    print(f"  {expected_line}")
    print("  ↓")
    print(f"  {broken_line}")

    print("\nChanged SHA-256:")
    print(changed_hash)

    if changed_hash == baseline_hash:
        print("\nERROR: File hash did not change.")
        return

    print("\nFile successfully changed.")

    # ---------------------------------------------------------
    # STEP 5: Rollback
    # ---------------------------------------------------------
    print("\n[5/6] Executing Git rollback...")

    rollback_success = rollback(
        str(project_path),
        checkpoint
    )

    if not rollback_success:
        print("\nERROR: Rollback failed.")
        return

    # ---------------------------------------------------------
    # STEP 6: Verify restoration
    # ---------------------------------------------------------
    print("\n[6/6] Verifying restored state...")

    restored_hash = sha256(app_file)
    restored_commit = get_current_commit(str(project_path))

    print("\nOriginal SHA-256:")
    print(baseline_hash)

    print("\nRestored SHA-256:")
    print(restored_hash)

    print("\nOriginal commit:")
    print(baseline_commit)

    print("\nRestored commit:")
    print(restored_commit)

    print("\n" + "=" * 60)

    if restored_hash != baseline_hash:
        print("ROLLBACK TEST FAILED")
        print("=" * 60)
        print("\nFile content was not restored correctly.")
        return

    if restored_commit != baseline_commit:
        print("ROLLBACK TEST FAILED")
        print("=" * 60)
        print("\nGit commit was not restored correctly.")
        return

    print("ROLLBACK TEST PASSED")
    print("=" * 60)

    print(
        "\nGit successfully restored the project "
        "to its pre-checkpoint state."
    )

    print(
        "\nOriginal file content restored."
    )

    print(
        "\nOriginal Git commit restored."
    )


if __name__ == "__main__":
    main()