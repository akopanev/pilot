# PILOT

CLI pipeline orchestrator — run multi-step LLM workflows from `.pilot/pipeline.yaml`.

## Install

```bash
# One-line install (from private repo)
curl -sSL https://raw.githubusercontent.com/akopanev/pilot/main/install.sh | bash

# Or from a local checkout
PILOT_REPO=/path/to/pilot bash install.sh
```

Requires Python 3.11+. Installs to `~/.pilot/` with wrappers at `~/.local/bin/pilot` and `~/.local/bin/pilot-docker`.

## Quick start

```bash
# Scaffold a new project
pilot init

# Review the config
pilot steps

# Check your environment
pilot doctor

# Run the pipeline
pilot run --dry-run   # preview first
pilot run             # execute
pilot run --debug     # execute with state dump
pilot run --debug 0   # debug with full values (no truncation)
```

`pilot init` creates everything inside `.pilot/`:

```
.pilot/
├── pipeline.yaml          # pipeline config
├── prompts/               # prompt templates
│   ├── implement.md
│   ├── review.md
│   └── fix.md
├── agents/                # review agents (customizable)
│   ├── quality.md
│   ├── implementation.md
│   ├── testing.md
│   ├── simplification.md
│   └── documentation.md
├── tasks/                 # task files for iterator loops
├── README.md              # full spec reference
└── progress-*.log         # execution logs
```

## Docker

Run Pilot in a hermetic container with all tools pre-installed (claude-code, codex).

```bash
# Run from any project directory — image auto-builds on first use
cd ~/my-project
pilot-docker run --dry-run
pilot-docker run

# Force rebuild after pilot source changes
pilot-docker --build run

# With API keys instead of CLI auth
ANTHROPIC_API_KEY=sk-... pilot-docker run
```

The wrapper script:
- Auto-builds the image on first use (from the pilot source directory)
- Mounts `$(pwd)` as `/workspace` inside the container
- Extracts Claude credentials from macOS Keychain if needed
- Matches your host UID so files have correct ownership

### Credential handling

**Option 1 — CLI auth (subscription):** The wrapper extracts OAuth tokens from macOS Keychain (or disk), mounts them read-only. Claude Code / Codex inside think they're logged in.

```bash
pilot-docker run
```

**Option 2 — API keys:** Pass keys as environment variables.

```bash
ANTHROPIC_API_KEY=sk-... OPENAI_API_KEY=sk-... pilot-docker run
```

---

## Overview

**Language:** Python 3.11+
**Entry point:** `pilot run` (or `python -m pilot run`)
**Config:** `.pilot/pipeline.yaml`

---

## 1. Project Structure

```
pilot/
├── __init__.py             # Package init, version
├── __main__.py             # python -m pilot entry point
├── cli.py                  # CLI (argparse): run, validate, steps, init
├── config.py               # YAML parsing, defaults, validation, agent resolution
├── engine.py               # Pipeline runner (orchestration, retry, cancellation)
├── signals.py              # XML signal parsing
├── templates.py            # Template variable expansion (inputs, runtime, files, loops, emissions, agents)
├── agents.py               # Agent loading — frontmatter parsing, project-local agent files
├── git.py                  # Git utilities (default branch, HEAD hash, diff)
├── progress.py             # Timestamped progress log with ANSI color
├── models.py               # Data classes (Step types, AgentDef, Config, RuntimeContext)
├── defaults/
│   ├── __init__.py
│   ├── agents/             # Example agent definitions (copied by `pilot init`)
│   └── templates/          # Pipeline templates for `pilot init`
│       ├── implement-and-review/
│       └── code-review/
├── executors/
│   ├── __init__.py         # ExecutorPool — routes tools to executors
│   ├── claude.py           # Claude Code executor (JSON stream parsing)
│   ├── codex.py            # Codex executor (split stderr/stdout)
│   ├── custom.py           # Custom script executor
│   ├── generic.py          # Generic plain-text executor (opencode, aider, etc.)
│   └── shell.py            # Shell command executor
└── tests/
    ├── test_agents.py      # Agent loading + frontmatter tests
    ├── test_config.py      # Config parsing + validation + agent ref tests
    ├── test_engine.py      # Pipeline engine tests (loops, retry, cancel, signals)
    ├── test_executors.py   # Executor + pool routing tests
    ├── test_init.py        # pilot init command tests
    ├── test_progress.py    # Color detection + progress log tests
    ├── test_signals.py     # Signal parsing tests
    └── test_templates.py   # Template expansion tests (inputs, emissions, agents)
```

---

## 2. Configuration (`config.py`)

### YAML Schema

```yaml
version: "1.0"

inputs:                              # User-defined key → value pairs
  input: .pilot/input.md             # Available as {{input}} in templates
  plan:  .pilot/plan.md

agents:                              # Named agent definitions (optional)
  reviewer:
    prompt: prompts/review.md        # prompt text or file path
    tool: codex                      # optional tool override
    model: gpt-4o                    # optional model override
    retry: 2                         # optional retry override
    args: ["--sandbox", "read-only"] # optional extra CLI args
  quick: "Just check for bugs"       # shorthand: prompt-only

defaults:
  agent:
    tool: claude-code                # Default executor tool
    model: claude-sonnet-4           # Default model
    retry: 0                         # Default retry count (0 = no retries)
    args: []                         # Default extra CLI args for executors
  error_patterns:                    # Strings that indicate executor failure
    - "rate limit"
    - "quota exceeded"
  iteration_delay_ms: 2000           # Delay between loop iterations (ms)

pipeline:                            # Ordered list of steps
  - id: snapshot
    agent:
      prompt: prompts/snapshot.md
```

### Step Types

A step is classified by which key is present: `agent`, `shell`, `loop`, or `gate`.

**Agent step** — runs a prompt through an LLM executor:

```yaml
- id: review
  agent:
    prompt: prompts/review.md        # file path or inline text
    tool: codex                      # optional override (default from defaults)
    model: gpt-4o                    # optional override
    retry: 2                         # optional per-step retry override
    args: ["--sandbox", "read-only"] # optional extra CLI args for executor
```

**Agent shorthand:**

```yaml
- id: task
  agent: prompts/task.md             # prompt-only shorthand
```

**Agent reference** — uses a named agent (from `agents:` section or agent files):

```yaml
- id: review
  agent: "@reviewer"                 # resolves prompt/tool/model/retry from agent def
```

Step-level fields override the agent's values. Only `None`/unset fields inherit from the agent. Merge rule for `args` (same as tool/model/retry): `step.args ?? agent.args ?? defaults.args`.

**Custom script step** — runs a script with prompt as temp file argument:

```yaml
- id: custom-review
  agent:
    tool: custom
    script: ./scripts/review.sh      # required when tool=custom
    prompt: prompts/review.md
```

**Shell step** — runs a command via subprocess:

```yaml
- id: lint
  shell:
    command: python scripts/validate.py {{plan}}
```

Shell shorthand: `shell: npm run lint`

**Gate step** — pauses for user approval:

```yaml
- id: approval
  gate: {}
```

**Loop step** — iterator or convergence:

```yaml
# Iterator loop — iterates over .md files in a folder
- id: dev
  loop:
    over: .pilot/tasks/
    as: TASK                         # file contents injected as {{TASK}}
    order: asc                       # asc (default) or desc
  steps:
    - id: execute
      agent:
        prompt: prompts/execute.md

# Convergence loop — repeats until APPROVE signal
- id: code-review
  loop:
    until: APPROVE
    max_rounds: 3                    # safety limit (default: 5)
  steps:
    - id: review
      agent:
        prompt: prompts/review.md
    - id: fix
      agent:
        prompt: prompts/fix.md
```

Loops can be nested — an iterator loop can contain convergence loops. Child steps inherit parent loop variables.

### Named Agents (`agents.py`)

Agents are reusable bundles of prompt + tool + model + script + retry. They can be defined in two places (in order of priority):

1. **`agents:` section in pilot.yaml** — highest priority, overrides file-based agents of the same name
2. **`.pilot/agents/*.md` files** — project-local agent definitions

Agent `.md` files use YAML frontmatter:

```markdown
---
tool: claude-code
model: claude-sonnet-4
---
Review code for bugs, security issues, and quality problems.
...
```

**Usage in pipeline steps:**

```yaml
# Reference a named agent — agent's prompt/tool/model/retry become the step's base values
- id: review
  agent: "@quality"

# Embed agent prompt content inside another prompt
# In prompts/my-review.md:
# Check using: {{agent:quality}}
```

### Validation

`load_config()` validates:

- Version field exists and is `"1.0"` or `"1"`
- Every step has an `id` field
- No duplicate step IDs (including nested)
- Loop steps have `over` or `until`
- Iterator loops have `as` variable
- Loop steps have at least one child
- `tool: custom` has a `script` path
- Step types are recognized

---

## 3. Data Models (`models.py`)

```python
@dataclass
class AgentStep:
    id: str
    prompt: str                   # prompt file path OR inline text
    tool: str | None = None       # override defaults.agent.tool
    model: str | None = None      # override defaults.agent.model
    script: str | None = None     # custom script path (tool="custom")
    retry: int | None = None      # per-step retry override
    args: list[str] | None = None # extra CLI args for the executor

@dataclass
class ShellStep:
    id: str
    command: str

@dataclass
class GateStep:
    id: str

@dataclass
class LoopStep:
    id: str
    steps: list[Step]

    # Iterator loop:
    over: str | None = None       # folder path
    as_var: str | None = None     # inject file contents as {{AS_VAR}}
    order: str = "asc"            # asc or desc

    # Convergence loop:
    until: str | None = None      # signal name (e.g., "APPROVE")
    max_rounds: int = 5           # safety limit

Step = AgentStep | ShellStep | GateStep | LoopStep

@dataclass
class AgentDef:
    """A reusable named agent definition."""
    name: str
    prompt: str                   # prompt text or file path
    tool: str | None = None
    model: str | None = None
    script: str | None = None
    retry: int | None = None
    args: list[str] | None = None # extra CLI args for the executor

@dataclass
class AgentDefaults:
    tool: str = "claude-code"
    model: str = "claude-sonnet-4"
    retry: int = 0
    args: list[str] = field(default_factory=list)  # default extra CLI args

@dataclass
class PilotConfig:
    version: str
    inputs: dict[str, str]
    defaults: AgentDefaults
    pipeline: list[Step]
    agents: dict[str, AgentDef] = field(default_factory=dict)
    error_patterns: list[str] = field(default_factory=list)
    iteration_delay_ms: int = 2000

@dataclass
class RuntimeContext:
    project_dir: str
    config_dir: str               # directory containing pipeline.yaml (for path resolution)
    default_branch: str
    progress_path: str
    diff_command: str
    round: int = 0
    emissions: dict[str, str] = field(default_factory=dict)  # from <pilot:emit> signals
    questions: list[QAPair] = field(default_factory=list)     # from <pilot:question> signals
    debug: bool = False           # --debug flag or PILOT_DEBUG env var
    debug_truncate: int = 80      # --debug CHARS or PILOT_DEBUG_TRUNCATE env var
```

---

## 4. Template Engine (`templates.py`)

Six tiers of variable expansion, applied in order:

### Tier 1: User-defined inputs

```python
def expand_inputs(text, inputs):
    # Replace {{var_name}} with values from inputs section
```

### Tier 2: Auto-detected runtime variables

| Variable | Source |
|----------|--------|
| `{{default_branch}}` | Git default branch (main, master, etc.) |
| `{{diff}}` | Git diff command (iteration-aware) |
| `{{progress_file_path}}` | Session progress log path |
| `{{round}}` | Current iteration number in loop |

### Tier 3: File injection

```
{{file:path}} → contents of the file at path
```

### Tier 4: Loop-injected variables

| Variable | Source |
|----------|--------|
| `{{TASK}}` | Current item contents (from iterator loop `as`) |
| `{{FEEDBACK}}` | REJECT payload from previous convergence round |

### Tier 5: Emissions

| Variable | Source |
|----------|--------|
| `{{emit.key}}` | Value stored via `<pilot:emit key="key">value</pilot:emit>` signal |

Emissions persist across loop rounds and steps. If a key has not been emitted, `{{emit.key}}` is left unchanged.

### Tier 6: Agent embedding

```
{{agent:name}} → agent's prompt content (inline text or loaded from file)
```

Embeds a named agent's prompt into another prompt. Useful for composing review instructions from reusable agent definitions. If the agent name is not found, `{{agent:name}}` is left unchanged.

### Prompt loading

Prompts can be file paths (`.md` or `.txt` extension) or inline text (multiline or no recognized extension).

---

## 5. Executors (`executors/`)

Each executor wraps a CLI tool as a subprocess. All executors return:

```python
@dataclass
class ExecutorResult:
    output: str                      # full captured text
    exit_code: int                   # process exit code
    error: str | None                # error message if failed
    signals: list[Signal] = field(default_factory=list)  # all detected signals
```

Signals are collected into a list during streaming — no double-parsing in the engine.

### Executor Pool (`executors/__init__.py`)

Routes tool names to executor implementations. Cached per tool (custom executors cached per script path).

| Tool | Executor | Behavior |
|------|----------|----------|
| `claude-code` | `ClaudeExecutor` | JSON stream parsing (`stream-json` format) |
| `codex` | `CodexExecutor` | Split stderr (progress) / stdout (response) |
| `custom` | `CustomExecutor` | Runs script with prompt temp file as argument |
| `shell` | `ShellExecutor` | `subprocess.run` (stateless, not cached) |
| anything else | `GenericExecutor` | Plain-text streaming via `<tool> --model M -p PROMPT` |

Requesting `tool="custom"` without a `script` raises `ValueError`.

### Claude Executor (`executors/claude.py`)

Spawns `claude --dangerously-skip-permissions --output-format stream-json --verbose`. Parses JSON events line-by-line (`assistant`, `content_block_delta`, `message_stop`, `result`), extracts text, detects signals mid-stream. Handles `<pilot:update>` signals immediately (writes file during stream). Filters `ANTHROPIC_API_KEY` from environment.

### Codex Executor (`executors/codex.py`)

Spawns `codex exec --sandbox full-auto` with separate stderr/stdout pipes. Default sandbox is `full-auto` (or `danger-full-access` if `PILOT_DOCKER=1`). stderr is read in a background thread for filtered progress display (header block + bold summaries). stdout is captured entirely as the response. Signals detected from stdout after completion.

### Custom Executor (`executors/custom.py`)

Writes prompt to a temp file, invokes `script <prompt_path>`. Streams stdout line-by-line with signal detection.

### Generic Executor (`executors/generic.py`)

For any CLI tool (opencode, aider, etc.) invoked as `<tool> [--model M] -p PROMPT`. Streams stdout line-by-line with signal detection and `<pilot:update>` handling.

### Shell Executor (`executors/shell.py`)

Simple `subprocess.run` with `shell=True`. Returns stdout, stderr on failure. No signal parsing.

### Error pattern detection

All agent executors accept `error_patterns` (configured in `defaults.error_patterns`). After execution, output is checked case-insensitively for each pattern. A match overrides the error field in the result.

### Process management

All subprocess executors use `start_new_session=True` for process group isolation. Cleanup on `KeyboardInterrupt`: `SIGTERM` → 5s wait → `SIGKILL`.

---

## 6. Signal Protocol (`signals.py`)

Models emit XML signals in their output. Executors detect them during streaming and collect them into `result.signals`.

### Signal Types

**Flow control signals:**

| Signal | XML | Engine Action |
|--------|-----|---------------|
| Approve | `<pilot:approve/>` | Exit convergence loop |
| Reject | `<pilot:reject>findings</pilot:reject>` | Inject as `{{FEEDBACK}}`, continue loop |
| Blocked | `<pilot:blocked>reason</pilot:blocked>` | Halt pipeline with error |
| Skip | `<pilot:skip/>` or `<pilot:skip>reason</pilot:skip>` | In iterator loop: break child steps, file stays in queue. Elsewhere: log warning, ignore |

**Data signals:**

| Signal | XML | Engine Action |
|--------|-----|---------------|
| Emit | `<pilot:emit key="name">value</pilot:emit>` | Store in `runtime.emissions[key]`, available as `{{emit.key}}` in templates |
| Completed | `<pilot:completed/>` or `<pilot:completed>summary</pilot:completed>` | Log completion status (does NOT exit loops) |

**Interaction signals:**

| Signal | XML | Engine Action |
|--------|-----|---------------|
| Question | `<pilot:question>text or json</pilot:question>` | Prompt user for input (accepts plain text or JSON `{"question": "..."}`) |
| Update | `<pilot:update path=".pilot/f">content</pilot:update>` | Write file (path must start with `.pilot/`) |
| Draft | `<pilot:draft label="name">content</pilot:draft>` | Present to user for review/approval |

### Signal Precedence

**Iterator loops:** skip checked first → breaks child loop, file stays in queue
**Convergence loops:** approve (return) → reject (feedback) → blocked (halt) → completed (log) → emit (store) → skip (warn)
**Outside loops:** blocked (halt) → question (prompt) → update (write) → draft (review) → completed (log) → emit (store) → skip (warn)

### Parsing

```python
@dataclass
class Signal:
    type: str                     # approve, reject, blocked, question, update, draft, completed, skip, emit
    payload: str | None = None    # text content
    path: str | None = None       # for update signals
    label: str | None = None      # for draft signals
    key: str | None = None        # for emit signals

def parse_signals(output: str) -> list[Signal]:
    """Extract all pilot:* signals from text using regex."""
```

---

## 7. Pipeline Engine (`engine.py`)

### Initialization

```python
class PipelineEngine:
    def __init__(self, config, runtime, cancel_event=None):
        self.config = config
        self.runtime = runtime
        self.executors = ExecutorPool(error_patterns=config.error_patterns)
        self.progress = ProgressLog(runtime.progress_path)
        self.cancel_event = cancel_event or threading.Event()
```

### Execution flow

1. **`run()`** — iterates pipeline steps sequentially, checks cancellation before each step
2. **`resume_from(step_id)`** — skips steps before the given ID, then executes normally
3. **`run_step()`** — dispatches to the correct handler based on step type

### Agent execution with retry

```python
def run_agent(step, loop_vars):
    max_retries = step.retry ?? config.defaults.retry
    result = _execute_agent(step, loop_vars)
    while result.exit_code != 0 and attempt < max_retries:
        _sleep()
        result = _execute_agent(step, loop_vars)
    return result
```

`_execute_agent()` handles: prompt loading → template expansion → executor resolution (including `script` for custom) → args resolution (`step.args ?? defaults.args`) → execution → signal logging → signal handling.

### Iterator loop

1. Glob `*.md` files in the `over` folder
2. Sort by name (asc/desc)
3. For each file: check cancellation → delay (if not first) → read contents → inject as loop var → run children → move file to `completed/`

### Convergence loop

1. For each round (up to `max_rounds`): check cancellation → delay (if not first) → update `diff_command` (first round: full branch diff, subsequent: uncommitted only) → inject `{{FEEDBACK}}` if present → run children
2. Exit conditions:
   - **APPROVE signal** — logs "approved at round N", returns
   - **No new commits** — if HEAD hash is unchanged after all children complete, logs "converged (no new commits)", returns
   - **BLOCKED signal** — raises `PipelineError`
   - **REJECT signal** — captures payload as feedback for next round
   - **Max rounds reached** — logs warning, returns
3. `diff_command` is restored to its original value in a `finally` block

### Signal handling (non-loop)

`handle_signals()` processes signals from agent steps outside convergence loops:

- **blocked** → raise `PipelineError`
- **question** → parse JSON or plain text, prompt user, log Q&A
- **update** → validate path starts with `.pilot/`, write file
- **draft** → show preview, prompt for approval, write file if approved
- **completed** → log completion summary
- **emit** → store `key=value` in `runtime.emissions`
- **skip** → log warning (ignored outside loops)

### Cancellation

`PipelineEngine` accepts a `threading.Event` as `cancel_event`. The engine checks `_check_cancelled()` before each step, each loop iteration, and each convergence round. If set, raises `PipelineError("Pipeline cancelled")`.

### Delay

`_sleep()` uses `cancel_event.wait(timeout=delay_sec)` — returns immediately if cancelled. Called between: convergence rounds (round > 1), iterator items (i > 1), and retry attempts.

---

## 8. Git Integration (`git.py`)

Read-only — never writes. Three functions:

```python
def get_default_branch() -> str:
    """Detect default branch: origin/HEAD → common names → 'master'."""

def get_head_hash() -> str:
    """Get current HEAD commit hash (empty string if not in a repo)."""

def get_diff_command(default_branch, is_first) -> str:
    """First iteration: 'git diff {branch}...HEAD'
    Subsequent:        'git diff'"""
```

---

## 9. Progress Log (`progress.py`)

Dual-output: plain text to file, colored text to terminal.

### Color rules

| Pattern | Color |
|---------|-------|
| Agent steps (`▸ ... (tool/model)`) | Green |
| Shell steps (`▸ ... (shell)`) | Cyan |
| Loop steps (`▸ ... (loop)`) | Magenta |
| Gate steps (`▸ ... (gate)`) | Yellow |
| Signals (`signal:`) | Blue |
| Non-zero exit code | Red |
| Checkmark (`✓`) | Green |
| Warning (`⚠`) | Yellow |
| Pipeline started/complete | Green |
| Timestamps | Gray |

### Color control

Color is disabled when:
- `NO_COLOR` environment variable is set (respects [no-color.org](https://no-color.org))
- `PILOT_NO_COLOR` environment variable is set
- stdout is not a TTY

The `--no-color` CLI flag sets `PILOT_NO_COLOR=1`.

---

## 10. CLI Interface (`cli.py`)

### Commands

```
pilot run [--config FILE] [--from STEP_ID] [--dry-run] [--no-color] [--debug [CHARS]] [--branch NAME] [--no-branch]
pilot validate [--config FILE]
pilot steps [--config FILE]
pilot init [TEMPLATE] [--list]
pilot agents [--config FILE]
pilot doctor [--config FILE]
```

### `pilot run`

Normal execution: loads config → creates runtime context → resolves branch → registers SIGINT/SIGTERM handlers → creates engine with cancel event → runs pipeline.

### `pilot run --debug [CHARS]`

Prints all template variables and state before each step/substep. Shows:
- Step identity (id + type)
- Prior history (completed steps from session)
- All template vars as `{{name}} = value` (inputs, runtime, emissions, loop vars, questions)
- Step-specific params (tool/model/retry/prompt for agents, command for shell, over/until for loops)

Values are truncated to `CHARS` characters (default: 80). Use `--debug 0` for no truncation. Also enabled via `PILOT_DEBUG=1` env var (truncation via `PILOT_DEBUG_TRUNCATE`).

### `pilot run --dry-run`

Prints config summary and step tree with resolved details:

```
Dry run — steps that would execute:

Inputs:
  input: .pilot/input.md
  plan: .pilot/plan.md
Defaults: tool=claude-code model=claude-sonnet-4 retry=0
Iteration delay: 2000ms

▸ snapshot [agent claude-code/claude-sonnet-4]
    prompt: prompts/snapshot.md (ok)
▸ validate [shell] python validate.py {{plan}}
⏸ approval [gate]
↻ dev [loop over=.pilot/tasks/ as=TASK] (3 files)
  ▸ execute [agent claude-code/claude-sonnet-4]
      prompt: prompts/execute.md (ok)
  ↻ code-review [loop until=APPROVE max=3]
    ▸ review [agent claude-code/claude-sonnet-4]
        prompt: prompts/review.md (ok)
    ▸ fix [agent claude-code/claude-sonnet-4]
        prompt: prompts/fix.md (ok)
```

Shows: resolved tool/model, script path, retry count (if > 0), prompt file existence, loop file counts.

### `pilot validate`

Loads and validates config, reports step count.

### `pilot steps`

Prints step tree with resolved details.

### `pilot init [TEMPLATE]`

Scaffolds a new project from a built-in pipeline template. Copies pipeline config, prompts, agents, and protocol into `.pilot/`. Never overwrites existing files. README.md is copied from `pilot.md` (single source of truth).

```bash
pilot init                           # uses default template (develop)
pilot init develop                   # explicit template name
pilot init --list                    # list available templates
```

### `pilot agents`

Lists all resolved agents (from `agents:` in config + `.pilot/agents/*.md` files). Shows name, tool, model, and source.

### `pilot doctor`

Checks environment: Python version, config validity, agent count, task files, and tool availability (claude-code, codex).

### `pilot run --branch NAME` / `--no-branch`

Controls git branch creation. By default, pilot derives a branch name from `input.md` and checks it out. `--branch` sets an explicit name, `--no-branch` disables branching entirely.

### Signal handling

SIGINT/SIGTERM set the cancel event, which the engine checks at safe points. This provides graceful shutdown instead of an abrupt kill.

---

## 11. Differences from Ralphex

| Aspect | Ralphex (Go) | PILOT (Python) |
|--------|-------------|----------------|
| Config | Custom `key = value` file + CLI flags | YAML pipeline |
| Pipeline | Hardcoded phases (task → review → codex → finalize) | Configurable steps |
| Signals | `<<<RALPHEX:SIGNAL>>>` plain markers | `<pilot:signal>` XML with attributes |
| Signal detection | Two-level: executor + processor | Single-level: XML regex in executors |
| Signal storage | `signal: Signal \| None` (last only) | `signals: list[Signal]` (all collected) |
| Review feedback | `{{CODEX_OUTPUT}}` / `{{CUSTOM_OUTPUT}}` injected | Generic `{{FEEDBACK}}` from REJECT signal |
| Convergence exit | `REVIEW_DONE` signal + git HEAD hash fallback | APPROVE signal + no-commit fallback |
| Executors | Claude + Codex + Custom (hardcoded) | Any tool via `agent.tool` + pool routing |
| Shell steps | Configurable commands only | First-class `shell:` step type |
| User interaction | `QUESTION` signal → re-run with answer in progress file | `gate:` type + `<pilot:question>` signal |
| Error patterns | Configured per executor | Global `defaults.error_patterns` |
| Retry | Not supported | Per-step or global retry with delay |
| Cancellation | Context cancellation | `threading.Event` + SIGINT/SIGTERM |
| Delay | Not configurable | `iteration_delay_ms` with cancel-aware sleep |
| Color output | Monochrome | Pattern-based ANSI colors (respects NO_COLOR) |

---

## 12. Running

### Install

```bash
pip install -e .
```

### Execute

```bash
pilot run                          # run pipeline
pilot run --config custom.yaml     # custom config file
pilot run --from step-id           # resume from a specific step
pilot run --dry-run                # preview steps without executing
pilot run --no-color               # disable colored output
pilot run --debug                  # print state vars before each step
pilot run --debug 0                # debug with no truncation
pilot run --branch my-feature      # explicit branch name
pilot run --no-branch              # disable branch creation
pilot validate                     # validate config
pilot steps                        # list step tree
pilot agents                       # list resolved agents
pilot doctor                       # check environment
python -m pilot run                # alternative invocation
```

### Environment variables

| Variable | Effect |
|----------|--------|
| `NO_COLOR` | Disable ANSI color output |
| `PILOT_NO_COLOR` | Disable ANSI color output |
| `PILOT_DEBUG` | Enable debug state dump before each step |
| `PILOT_DEBUG_TRUNCATE` | Truncation limit for debug values (default: 80, 0=full) |
| `PILOT_DOCKER` | Set to `1` to use `danger-full-access` sandbox for codex |

### Testing

```bash
python -m pytest pilot/tests/ -v   # 237 tests
```
