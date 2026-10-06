import subprocess
from pathlib import Path


def run_git(
    project_path: str,
    args: list[str]
) -> dict:

    root = Path(project_path).resolve()

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30
        )

        return {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except Exception as error:
        return {
            "success": False,
            "return_code": -1,
            "stdout": "",
            "stderr": str(error),
        }


def is_git_repository(project_path: str) -> bool:

    result = run_git(
        project_path,
        ["rev-parse", "--is-inside-work-tree"]
    )

    return (
        result["success"]
        and result["stdout"].strip().lower() == "true"
    )


def get_status(project_path: str) -> str:

    result = run_git(
        project_path,
        ["status", "--porcelain"]
    )

    if not result["success"]:
        raise RuntimeError(
            "Unable to read Git status:\n"
            + result["stderr"]
        )

    return result["stdout"].strip()


def ensure_clean_repository(project_path: str):

    if not is_git_repository(project_path):
        raise RuntimeError(
            "Project is not a Git repository."
        )

    status = get_status(project_path)

    if status:
        raise RuntimeError(
            "Git working tree is not clean.\n\n"
            "AutoCoder refuses to create a checkpoint "
            "because existing user changes are present.\n\n"
            "Current changes:\n"
            + status
        )


def get_current_commit(project_path: str) -> str:

    result = run_git(
        project_path,
        ["rev-parse", "HEAD"]
    )

    if not result["success"]:
        raise RuntimeError(
            "Unable to determine current Git commit:\n"
            + result["stderr"]
        )

    return result["stdout"].strip()


def create_checkpoint(
    project_path: str,
    message: str = "AutoCoder checkpoint"
) -> str:

    ensure_clean_repository(project_path)

    before_commit = get_current_commit(project_path)

    result = run_git(
        project_path,
        ["commit", "--allow-empty", "-m", message]
    )

    if not result["success"]:
        raise RuntimeError(
            "Failed to create Git checkpoint:\n"
            + result["stderr"]
        )

    checkpoint_commit = get_current_commit(project_path)

    print("\nGit checkpoint created.")
    print(f"Commit: {checkpoint_commit}")

    return before_commit


def get_untracked_files(project_path: str) -> list[str]:

    result = run_git(
        project_path,
        [
            "ls-files",
            "--others",
            "--exclude-standard"
        ]
    )

    if not result["success"]:
        raise RuntimeError(
            "Unable to determine untracked files:\n"
            + result["stderr"]
        )

    output = result["stdout"].strip()

    if not output:
        return []

    return output.splitlines()


def rollback(
    project_path: str,
    commit: str,
    remove_untracked: bool = False
) -> bool:

    print("\n")
    print("=" * 60)
    print("GIT ROLLBACK")
    print("=" * 60)

    print(
        f"\nRestoring project to commit:\n{commit}"
    )

    # ---------------------------------------------------------
    # Safety check
    # ---------------------------------------------------------

    if not is_git_repository(project_path):
        print("\nRollback failed:")
        print("Project is not a Git repository.")
        return False

    # ---------------------------------------------------------
    # Restore tracked files
    # ---------------------------------------------------------

    result = run_git(
        project_path,
        ["reset", "--hard", commit]
    )

    if not result["success"]:
        print("\nRollback failed:")
        print(result["stderr"])
        return False

    print("\nTracked files restored.")

    # ---------------------------------------------------------
    # Handle untracked files safely
    # ---------------------------------------------------------

    untracked = get_untracked_files(project_path)

    if untracked:

        print("\nUntracked files detected after rollback:")

        for file in untracked:
            print(f"  - {file}")

        if not remove_untracked:
            print(
                "\nSafety policy:"
            )
            print(
                "AutoCoder will NOT delete untracked files "
                "automatically."
            )

            print(
                "\nTracked project state was restored successfully."
            )

            return True

        print(
            "\nRemoving untracked files because "
            "remove_untracked=True..."
        )

        clean_result = run_git(
            project_path,
            ["clean", "-fd"]
        )

        if not clean_result["success"]:
            print(
                "\nWarning: unable to clean untracked files:"
            )
            print(clean_result["stderr"])
            return False

        print(
            "\nUntracked files removed."
        )

    else:
        print(
            "\nNo untracked files detected."
        )

    print(
        "\nRollback completed successfully."
    )

    return True