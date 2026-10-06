import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(AGENT_DIR))

from git_manager import (
    get_current_commit,
    get_untracked_files,
    rollback,
)


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print(
            r'python rollback_safety_test.py "C:\path\to\test-project"'
        )
        return

    project_path = Path(sys.argv[1]).resolve()
    app_file = project_path / "src" / "app.js"
    safety_file = project_path / "rollback-safety-test.txt"

    print("=" * 60)
    print("AUTOCODER - UNTRACKED FILE SAFETY TEST")
    print("=" * 60)

    print(f"\nProject:")
    print(project_path)

    # ---------------------------------------------------------
    # STEP 1: Verify safety file exists
    # ---------------------------------------------------------

    print("\n[1/5] Checking untracked safety file...")

    if not safety_file.exists():
        print("\nERROR: rollback-safety-test.txt does not exist.")
        return

    safety_content = safety_file.read_text(
        encoding="utf-8"
    )

    print("Safety file exists.")
    print(f"Content: {safety_content}")

    if safety_content != "DO NOT DELETE":
        print("\nERROR: Unexpected safety file content.")
        return

    # ---------------------------------------------------------
    # STEP 2: Capture current commit
    # ---------------------------------------------------------

    print("\n[2/5] Capturing current Git commit...")

    try:
        commit = get_current_commit(str(project_path))
    except Exception as error:
        print("\nERROR:")
        print(error)
        return

    print(f"Commit:")
    print(commit)

    # ---------------------------------------------------------
    # STEP 3: Create a controlled tracked-file modification
    # ---------------------------------------------------------

    print("\n[3/5] Creating controlled tracked-file change...")

    original = app_file.read_text(
        encoding="utf-8"
    )

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

    print("Tracked file modified.")

    # ---------------------------------------------------------
    # STEP 4: Rollback without deleting untracked files
    # ---------------------------------------------------------

    print("\n[4/5] Executing safe rollback...")

    success = rollback(
        str(project_path),
        commit,
        remove_untracked=False
    )

    if not success:
        print("\nERROR: Rollback failed.")
        return

    # ---------------------------------------------------------
    # STEP 5: Verify untracked file survived
    # ---------------------------------------------------------

    print("\n[5/5] Verifying untracked file protection...")

    if not safety_file.exists():
        print("\nROLLBACK SAFETY TEST FAILED")
        print("=" * 60)
        print(
            "\nThe untracked file was deleted."
        )
        return

    restored_content = safety_file.read_text(
        encoding="utf-8"
    )

    print("\nUntracked file still exists.")

    print(
        f"Content after rollback: {restored_content}"
    )

    if restored_content != "DO NOT DELETE":
        print("\nROLLBACK SAFETY TEST FAILED")
        print("=" * 60)
        print(
            "\nThe untracked file survived but its content changed."
        )
        return

    untracked_files = get_untracked_files(
        str(project_path)
    )

    if "rollback-safety-test.txt" not in untracked_files:
        print("\nROLLBACK SAFETY TEST FAILED")
        print("=" * 60)
        print(
            "\nThe safety file is no longer reported as untracked."
        )
        return

    print("\n" + "=" * 60)
    print("ROLLBACK SAFETY TEST PASSED")
    print("=" * 60)

    print(
        "\nTracked project files were restored."
    )

    print(
        "\nUntracked file was preserved."
    )

    print(
        "\nUntracked file content was preserved."
    )

    print(
        "\nAutoCoder did NOT delete the user's untracked file."
    )


if __name__ == "__main__":
    main()