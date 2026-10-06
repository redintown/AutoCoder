
import sys
import json
import requests
from pathlib import Path

from project_inspector import inspect_project
from test_runner import run_tests
from project_inspector import inspect_project
from test_runner import run_tests
from git_manager import (
    ensure_clean_repository,
    create_checkpoint,
    rollback,
)

# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5-coder:7b"

MAX_FIX_ATTEMPTS = 5


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are AutoCoder, a local autonomous software engineering agent.

Your job is to analyze a software development task and produce safe,
minimal, structured file changes based on the ACTUAL project information.

IMPORTANT RULES:

1. Never assume the project's framework or architecture.
2. Use the actual project inspection as the source of truth.
3. Do not invent existing files.
4. Do not modify unrelated files.
5. Keep changes minimal.
6. Do not add dependencies unless they are necessary.
7. Never use absolute file paths.
8. Never reference paths outside the project.
9. For every created or modified file, provide the COMPLETE resulting file.
10. Do not provide partial code snippets.
11. Return ONLY valid JSON.
12. Do not use Markdown code fences.
13. Do not include explanations outside the JSON.
14. Never claim that an implementation is correct merely because it appears correct.
15. If the project contains tests relevant to the task, treat those tests as the source of truth.
16. If the task asks to fix behavior and the existing implementation does not clearly satisfy the task, propose the necessary change.
17. Do not return an empty changes array unless the existing implementation clearly satisfies the requested behavior.
18. When tests are available, include the relevant test command in the "tests" array.

The JSON must follow EXACTLY this structure:

{
  "summary": "short description",
  "changes": [
    {
      "file": "relative/path/to/file",
      "action": "create|modify|delete",
      "description": "what should change",
      "code": "complete resulting file content"
    }
  ],
  "tests": [
    "exact executable test command"
  ],
  "risks": [
    "potential risk"
  ]
}

RULES FOR CHANGES:

- "create" means create a new file.
- "modify" means modify an existing file.
- "delete" means delete an existing file.
- For create and modify, code MUST contain the COMPLETE resulting file.
- For delete, code MUST be an empty string.
- File paths must always be relative to the project root.
- Do not use ../ in file paths.
- Do not use absolute paths.

RULES FOR TESTS:

- Every item in "tests" must be an executable shell command.
- Do not write explanations such as "Run npm test".
- Use commands such as:
  "npm test"
  "npm run build"
  "npm run lint"
  "python -m pytest"
  "node test.js"

If the task cannot safely be implemented using the available information,
return an empty changes array and explain the reason in "summary".
"""


# ============================================================
# INITIAL AI REQUEST
# ============================================================

def ask_ai(task: str, project_report: str) -> str:

    user_prompt = f"""
USER TASK:

{task}


ACTUAL PROJECT INFORMATION:

{project_report}


Analyze the task using the actual project information.

Return ONLY valid JSON.

The JSON must contain:

- summary
- changes
- tests
- risks

For every modified or created file, provide the COMPLETE resulting
file content.

Do not provide partial snippets.
Do not use Markdown.
Do not modify files yourself.
"""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1
        }
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=300
    )

    response.raise_for_status()

    data = response.json()

    return data["message"]["content"]


# ============================================================
# AI FIX REQUEST
# ============================================================

def ask_ai_to_fix(
    task: str,
    project_report: str,
    test_output: str,
    previous_result: dict
) -> str:

    fix_prompt = f"""
The implementation was applied, but the tests failed.

ORIGINAL USER TASK:

{task}


ACTUAL PROJECT INFORMATION:

{project_report}


PREVIOUS CHANGE SET:

{json.dumps(previous_result, indent=2)}


TEST FAILURE:

{test_output}


Your job is to diagnose the failure and produce a corrected
change set.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "summary": "what failed and how it will be fixed",
  "changes": [
    {{
      "file": "relative/path",
      "action": "modify|create|delete",
      "description": "what is being fixed",
      "code": "COMPLETE resulting file content"
    }}
  ],
  "tests": [
    "exact executable test command"
  ],
  "risks": []
}}

IMPORTANT:

- Provide COMPLETE resulting file content.
- Never provide partial snippets.
- Do not invent project architecture.
- Do not modify unrelated files.
- Do not add dependencies unless necessary.
- Test commands must be executable.
- Never use absolute paths.
- Never use ../ in paths.
- Return ONLY JSON.
"""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": fix_prompt
            }
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1
        }
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=300
    )

    response.raise_for_status()

    data = response.json()

    return data["message"]["content"]


# ============================================================
# JSON PARSER
# ============================================================

def parse_ai_response(raw_response: str) -> dict:

    try:

        result = json.loads(raw_response)

    except json.JSONDecodeError as error:

        raise ValueError(
            "AI returned invalid JSON.\n\n"
            f"JSON error: {error}\n\n"
            f"Raw response:\n{raw_response}"
        )

    if not isinstance(result, dict):

        raise ValueError(
            "AI response must be a JSON object."
        )

    required_fields = [
        "summary",
        "changes",
        "tests",
        "risks"
    ]

    for field in required_fields:

        if field not in result:

            raise ValueError(
                f"AI response is missing '{field}'."
            )

    if not isinstance(result["changes"], list):

        raise ValueError(
            "'changes' must be a list."
        )

    if not isinstance(result["tests"], list):

        raise ValueError(
            "'tests' must be a list."
        )

    if not isinstance(result["risks"], list):

        raise ValueError(
            "'risks' must be a list."
        )

    return result


# ============================================================
# CHANGE VALIDATION
# ============================================================

def validate_changes(
    project_path: str,
    result: dict
):

    root = Path(project_path).resolve()

    for index, change in enumerate(
        result["changes"],
        start=1
    ):

        if not isinstance(change, dict):

            raise ValueError(
                f"Change #{index} must be an object."
            )

        file_path = change.get("file")
        action = change.get("action")
        code = change.get("code")

        if not file_path:

            raise ValueError(
                f"Change #{index} is missing its file path."
            )

        path_object = Path(file_path)

        if path_object.is_absolute():

            raise ValueError(
                f"Absolute paths are not allowed: {file_path}"
            )

        if ".." in path_object.parts:

            raise ValueError(
                f"Parent-directory paths are not allowed: "
                f"{file_path}"
            )

        target = (root / path_object).resolve()

        try:

            target.relative_to(root)

        except ValueError:

            raise ValueError(
                f"Path escapes project directory: {file_path}"
            )

        if action not in {
            "create",
            "modify",
            "delete"
        }:

            raise ValueError(
                f"Invalid action '{action}' "
                f"for {file_path}"
            )

        if action in {
            "create",
            "modify"
        }:

            if not isinstance(code, str):

                raise ValueError(
                    f"Complete file content is required "
                    f"for {file_path}"
                )

        if action == "delete":

            if code != "":

                raise ValueError(
                    f"Delete operation must have "
                    f"empty code: {file_path}"
                )


# ============================================================
# DISPLAY PROPOSED CHANGES
# ============================================================

def show_proposed_changes(
    project_path: str,
    result: dict
):

    print("\n")
    print("=" * 60)
    print("PROPOSED CHANGES")
    print("=" * 60)

    changes = result.get(
        "changes",
        []
    )

    if not changes:

        print("\nNo file changes proposed.")

        return

    for index, change in enumerate(
        changes,
        start=1
    ):

        print(
            f"\n[{index}] "
            f"{change['action'].upper()}"
        )

        print(
            f"File: {change['file']}"
        )

        print(
            f"Description: "
            f"{change.get('description', '')}"
        )

        if change["action"] != "delete":

            print(
                "\n--- COMPLETE FILE CONTENT ---"
            )

            print(
                change["code"]
            )

            print(
                "--- END FILE CONTENT ---"
            )


# ============================================================
# APPLY CHANGES
# ============================================================

def apply_changes(
    project_path: str,
    result: dict
):

    root = Path(project_path).resolve()

    for change in result["changes"]:

        target = (
            root / change["file"]
        ).resolve()

        action = change["action"]

        # ----------------------------------------
        # CREATE
        # ----------------------------------------

        if action == "create":

            target.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            if target.exists():

                raise FileExistsError(
                    "Refusing to overwrite "
                    f"existing file: {target}"
                )

            target.write_text(
                change["code"],
                encoding="utf-8"
            )

        # ----------------------------------------
        # MODIFY
        # ----------------------------------------

        elif action == "modify":

            if not target.exists():

                raise FileNotFoundError(
                    "Cannot modify missing file: "
                    f"{target}"
                )

            target.write_text(
                change["code"],
                encoding="utf-8"
            )

        # ----------------------------------------
        # DELETE
        # ----------------------------------------

        elif action == "delete":

            if target.exists():

                target.unlink()


# ============================================================
# FORMAT TEST RESULTS FOR AI
# ============================================================

def format_test_results(
    test_result: dict
) -> str:

    return json.dumps(
        test_result,
        indent=2
    )
def handle_no_change_result(
    project_path: str,
    task: str,
    project_report: str,
    result: dict
) -> bool:

    test_commands = result.get("tests", [])

    if not test_commands:
        print("\nAI proposed no changes and provided no tests.")
        print("AutoCoder cannot verify the task.")
        return False

    print("\n")
    print("=" * 60)
    print("NO CHANGES PROPOSED - VERIFYING WITH TESTS")
    print("=" * 60)

    test_result = run_tests(
        project_path,
        test_commands
    )

    if test_result["success"]:
        print("\n")
        print("=" * 60)
        print("AI PROPOSED NO CHANGES AND TESTS PASSED")
        print("=" * 60)
        return True

    if any(
        item.get("blocked", False)
        for item in test_result["results"]
    ):
        print("\nA command was blocked by Command Guard.")
        print("AutoCoder stopped.")
        return False

    print("\n")
    print("=" * 60)
    print("AI WAS WRONG - TESTS FAILED")
    print("=" * 60)

    failure_text = format_test_results(test_result)

    print(
        "\nSending the real test failure "
        "to local AI for diagnosis..."
    )

    try:
        raw_fix = ask_ai_to_fix(
            task,
            project_report,
            failure_text,
            result
        )

        fix_result = parse_ai_response(raw_fix)

        validate_changes(
            project_path,
            fix_result
        )

    except Exception as error:
        print("\nAI fix generation failed:")
        print(error)
        return False

    print("\n")
    print("=" * 60)
    print("AI GENERATED A FIX")
    print("=" * 60)

    print(
        f"\nSummary:\n"
        f"{fix_result.get('summary', '')}"
    )

    show_proposed_changes(
        project_path,
        fix_result
    )

    if fix_result.get("risks"):
        print("\n")
        print("=" * 60)
        print("RISKS")
        print("=" * 60)

        for risk in fix_result["risks"]:
            print(f"- {risk}")

    if not fix_result.get("changes"):
        print("\nAI still proposed no changes.")
        print("AutoCoder cannot repair the failing task.")
        return False

    print("\n")
    answer = input(
        "Apply this AI-generated fix? [y/N]: "
    ).strip().lower()

    if answer != "y":
        print("\nFix rejected.")
        return False

    try:
        apply_changes(
            project_path,
            fix_result
        )
    except Exception as error:
        print("\nFailed to apply AI fix:")
        print(error)
        return False

    print("\nFix applied successfully.")

    return automatic_fix_loop(
        project_path,
        task,
        project_report,
        fix_result
    )

# ============================================================
# AUTOMATIC FIX LOOP
# ============================================================

def automatic_fix_loop(
    project_path: str,
    task: str,
    project_report: str,
    result: dict
) -> bool:

    current_result = result

    for attempt in range(
        1,
        MAX_FIX_ATTEMPTS + 1
    ):

        print("\n")
        print("=" * 60)
        print(
            f"TEST / FIX ATTEMPT "
            f"{attempt}/{MAX_FIX_ATTEMPTS}"
        )
        print("=" * 60)

        test_commands = current_result.get(
            "tests",
            []
        )

        if not test_commands:

            print(
                "\nNo executable test commands "
                "were provided by the AI."
            )

            return False

        test_result = run_tests(
            project_path,
            test_commands
        )

        # ----------------------------------------
        # TEST SUCCESS
        # ----------------------------------------

        if test_result["success"]:

            print("\n")
            print("=" * 60)
            print("ALL TESTS PASSED")
            print("=" * 60)

            return True

        # ----------------------------------------
        # COMMAND BLOCKED
        # ----------------------------------------

        if any(
            item.get("blocked", False)
            for item in test_result["results"]
        ):

            print("\n")
            print(
                "A command was blocked by "
                "Command Guard."
            )

            print(
                "Automatic fixing stopped."
            )

            return False

        # ----------------------------------------
        # TEST FAILED
        # ----------------------------------------

        print("\nTest failure detected.")

        failure_text = format_test_results(
            test_result
        )

        print(
            "\nSending failure information "
            "to local AI..."
        )

        try:

            raw_fix = ask_ai_to_fix(
                task,
                project_report,
                failure_text,
                current_result
            )

            new_result = parse_ai_response(
                raw_fix
            )

            validate_changes(
                project_path,
                new_result
            )

        except Exception as error:

            print("\nAI fix generation failed:")

            print(error)

            return False

        print("\n")
        print("=" * 60)
        print("AI GENERATED A FIX")
        print("=" * 60)

        print(
            f"\nSummary:\n"
            f"{new_result.get('summary', '')}"
        )

        show_proposed_changes(
            project_path,
            new_result
        )

        # ----------------------------------------
        # SAFETY APPROVAL FOR FIX
        # ----------------------------------------

        print("\n")

        answer = input(
            "Apply this AI-generated fix? [y/N]: "
        ).strip().lower()

        if answer != "y":

            print(
                "\nFix rejected."
            )

            return False

        try:

            apply_changes(
                project_path,
                new_result
            )

        except Exception as error:

            print(
                "\nFailed to apply AI fix:"
            )

            print(error)

            return False

        print(
            "\nFix applied successfully."
        )

        current_result = new_result

    # --------------------------------------------
    # MAX ATTEMPTS
    # --------------------------------------------

    print("\n")
    print("=" * 60)
    print("MAXIMUM FIX ATTEMPTS REACHED")
    print("=" * 60)

    return False


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("AUTO CODER - PHASE 4")
    print("=" * 60)

    # --------------------------------------------
    # PROJECT PATH
    # --------------------------------------------

    if len(sys.argv) < 2:

        print("\nUsage:")

        print(
            "python agent\\agent.py "
            "<project-path>"
        )

        print("\nExample:")

        print(
            'python agent\\agent.py '
            '"C:\\Projects\\my-project"'
        )

        return

    project_path = sys.argv[1]

    # --------------------------------------------
    # CHECK PROJECT
    # --------------------------------------------

    print("\nProject:")

    print(project_path)

    project = Path(
        project_path
    ).resolve()

    if not project.exists():

        print(
            "\nERROR: Project does not exist."
        )

        return

    if not project.is_dir():

        print(
            "\nERROR: Project path is not a directory."
        )

        return

    # --------------------------------------------
    # INSPECT PROJECT
    # --------------------------------------------
    print("\nChecking Git repository...")

    try:
        ensure_clean_repository(project_path)
    except Exception as error:
        print("\nGit safety check failed:")
        print(error)
        return

    try:
        checkpoint = create_checkpoint(
            project_path,
            "AutoCoder checkpoint before task"
        )
    except Exception as error:
        print("\nGit checkpoint failed:")
        print(error)
        return
    print("\nInspecting project...")

    try:

        project_report = inspect_project(
            project_path
        )

    except Exception as error:

        print(
            "\nProject inspection failed:"
        )

        print(error)

        return

    print(
        "\nProject inspection complete."
    )

    # --------------------------------------------
    # GET TASK
    # --------------------------------------------

    print(
        "\nWhat do you want to build?"
    )

    task = input("> ")

    if not task.strip():

        print(
            "\nNo task provided."
        )

        return

    # --------------------------------------------
    # AI PLANNING
    # --------------------------------------------

    print(
        "\nAI is analyzing the project "
        "and generating changes..."
    )

    try:

        raw_response = ask_ai(
            task,
            project_report
        )

        result = parse_ai_response(
            raw_response
        )

        validate_changes(
            project_path,
            result
        )

    except Exception as error:

        print(
            "\nAI processing failed:"
        )

        print(error)

        return

    # --------------------------------------------
    # SHOW SUMMARY
    # --------------------------------------------

    print("\n")
    print("=" * 60)
    print("AI SUMMARY")
    print("=" * 60)

    print(
        result.get(
            "summary",
            "No summary provided."
        )
    )

    # --------------------------------------------
    # SHOW RISKS
    # --------------------------------------------

    risks = result.get(
        "risks",
        []
    )

    if risks:

        print("\n")
        print("=" * 60)
        print("RISKS")
        print("=" * 60)

        for risk in risks:

            print(
                f"- {risk}"
            )

    # --------------------------------------------
    # SHOW CHANGES
    # --------------------------------------------

    show_proposed_changes(
        project_path,
        result
    )

    # --------------------------------------------
    # NO CHANGES
    # --------------------------------------------

    if not result.get("changes"):
        success = handle_no_change_result(
            project_path,
            task,
            project_report,
            result
        )

        print(
            "\nChanges cancelled."
        )

        print(
            "No files were modified."
        )

        return

    # --------------------------------------------
    # APPLY INITIAL CHANGES
    # --------------------------------------------

    print(
        "\nApplying changes..."
    )

    try:

        apply_changes(
            project_path,
            result
        )

    except Exception as error:

        print(
            "\nFailed to apply changes:"
        )

        print(error)

        return

    print(
        "\nInitial changes applied successfully."
    )

    # --------------------------------------------
    # AUTOMATIC TEST / FIX LOOP
    # --------------------------------------------

    success = automatic_fix_loop(
        project_path,
        task,
        project_report,
        result
    )

    # --------------------------------------------
    # FINAL RESULT
    # --------------------------------------------

    print("\n")

    if success:
        print("=" * 60)
        print("AUTO CODER COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(
            "\nImplementation verified "
            "and tests passed."
        )
    else:
        print("=" * 60)
        print("AUTO CODER STOPPED")
        print("=" * 60)
        print(
            "\nThe task was not verified successfully."
        )

        print(
            "\nAutoCoder can restore the project "
            "to the pre-task Git checkpoint."
        )

        answer = input(
            "\nRollback all task changes? [Y/n]: "
        ).strip().lower()

        if answer in {"", "y", "yes"}:
            rollback(
                project_path,
                checkpoint
            )
        else:
            print(
                "\nRollback skipped. "
                "Current changes were preserved."
            )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
