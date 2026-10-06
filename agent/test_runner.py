import subprocess
from pathlib import Path

from command_guard import validate_command


def run_command(
    command: str,
    project_path: str,
    timeout: int = 120
) -> dict:

    root = Path(project_path).resolve()

    allowed, reason = validate_command(command)

    if not allowed:

        print(f"\nCOMMAND BLOCKED: {reason}")
        print(f"Command: {command}")

        return {
            "success": False,
            "blocked": True,
            "return_code": -1,
            "stdout": "",
            "stderr": reason,
            "command": command
        }

    try:

        result = subprocess.run(
            command,
            cwd=root,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        return {
            "success": result.returncode == 0,
            "blocked": False,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": command
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "blocked": False,
            "return_code": -1,
            "stdout": "",
            "stderr": (
                f"Command timed out after "
                f"{timeout} seconds."
            ),
            "command": command
        }

    except Exception as error:

        return {
            "success": False,
            "blocked": False,
            "return_code": -1,
            "stdout": "",
            "stderr": str(error),
            "command": command
        }


def run_tests(
    project_path: str,
    test_commands: list[str]
) -> dict:

    if not test_commands:

        return {
            "success": True,
            "message": "No test commands provided.",
            "results": []
        }

    results = []

    for command in test_commands:

        print("\n" + "=" * 60)
        print(f"RUNNING: {command}")
        print("=" * 60)

        result = run_command(
            command,
            project_path
        )

        results.append(result)

        if result["stdout"]:
            print("\nSTDOUT:")
            print(result["stdout"])

        if result["stderr"]:
            print("\nSTDERR:")
            print(result["stderr"])

        if result["blocked"]:

            return {
                "success": False,
                "message": "Command was blocked.",
                "results": results
            }

        if not result["success"]:

            print(
                f"\nTest failed. "
                f"Exit code: {result['return_code']}"
            )

            return {
                "success": False,
                "message": "A test command failed.",
                "results": results
            }

        print("\nTest passed.")

    return {
        "success": True,
        "message": "All tests passed.",
        "results": results
    }