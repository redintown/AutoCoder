# AutoCoder

A local, open-source autonomous coding assistant powered by Ollama.

AutoCoder is designed to reduce the repetitive workflow of asking an AI for coding instructions, manually applying changes, running tests, sending failures back to the AI, and repeating the process.

Instead, AutoCoder can inspect a local project, ask a local coding model for structured changes, apply approved changes, run tests, and use test failures to request repairs.

## Current Status

AutoCoder is currently under active development.

### Implemented

- Local AI integration with Ollama
- Qwen2.5-Coder support
- Project structure inspection
- Source-code context collection
- Structured AI change proposals
- Safe file-path validation
- User approval before applying AI-generated changes
- Command allowlist and dangerous-command blocking
- Automated test execution
- AI-assisted repair loop
- Git repository safety checks
- Git checkpoints
- Git rollback
- Protection against deleting untracked files during rollback

## Architecture

```text
User Task
    |
    v
Project Inspector
    |
    v
Local AI (Ollama)
    |
    v
Structured Change Proposal
    |
    v
User Approval
    |
    v
Apply Changes
    |
    v
Run Tests
    |
    +---- PASS ----> Verified Result
    |
    +---- FAIL ----> AI Repair
                         |
                         v
                      Re-test
                         |
                    repeated attempts
                         |
                         v
                       Rollback
```

## Requirements

- Windows, Linux, or macOS
- Python 3.10+
- Git
- Ollama
- A coding model supported by Ollama

The current development environment uses:

- Python 3.14
- Ollama
- Qwen2.5-Coder 7B

## Setup

Clone the repository:

```bash
git clone https://github.com/redintown/AutoCoder.git
cd AutoCoder
```

Create a Python virtual environment:

```bash
python -m venv .venv
```

### Windows PowerShell

Activate the environment:

```powershell
.venv\Scripts\Activate.ps1
```

Install the required Python dependency:

```powershell
pip install requests
```

Install Ollama and pull the coding model:

```powershell
ollama pull qwen2.5-coder:7b
```

Make sure Ollama is running before starting AutoCoder.

## Usage

Run AutoCoder by providing the path to a Git project:

```powershell
python agent\agent.py "C:\path\to\your\project"
```

AutoCoder first checks that the target repository has no existing uncommitted changes.

This is intentional. AutoCoder should not mix autonomous changes with pre-existing user work.

## Safety Model

AutoCoder currently uses several safety layers:

1. Git working-tree validation
2. Git checkpoint before task execution
3. Restricted command execution
4. Dangerous-command blocking
5. File-path validation
6. User approval before applying AI-generated changes
7. Test-based verification
8. AI repair attempts after test failures
9. Git rollback when the task cannot be verified
10. Untracked-file preservation during rollback

## Test Project

A small JavaScript test project is included under:

```text
workspace/test-project
```

Run its tests:

```powershell
cd workspace\test-project
npm test
```

Expected result:

```text
All tests passed.
```

## Project Structure

```text
AutoCoder/
├── agent/
│   ├── agent.py
│   ├── command_guard.py
│   ├── git_manager.py
│   ├── project_inspector.py
│   ├── rollback_test.py
│   ├── rollback_safety_test.py
│   └── test_runner.py
│
├── workspace/
│   └── test-project/
│
├── logs/
├── .venv/
├── .gitignore
└── README.md
```

## Roadmap

Planned development includes:

- Autonomous multi-step task planning
- Better context selection for large projects
- More reliable code editing
- Improved test discovery
- Better failure diagnosis
- Multi-file task execution
- More robust execution policies
- Task progress tracking
- Human-in-the-loop approval modes
- Support for additional local coding models
- Improved developer experience
- Plugin and tool integrations

## Why Local AI?

AutoCoder is designed around local models so developers can experiment with autonomous coding workflows without depending entirely on paid hosted AI APIs.

Ollama provides the local model runtime, while AutoCoder provides the agent orchestration, verification, and safety layer.

## Development Philosophy

AutoCoder follows a simple principle:

> AI proposes.  
> Tests verify.  
> Git protects.

The goal is not to blindly give an AI full control over a codebase. The goal is to combine autonomous execution with verification, user control, and recoverability.

## Contributing

Contributions, bug reports, feature ideas, experiments, and pull requests are welcome.

Please open an issue or pull request with a clear description of the proposed change.

## License

This project is licensed under the MIT License.
