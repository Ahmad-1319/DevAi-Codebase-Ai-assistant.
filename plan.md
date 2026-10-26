# DevAI: From Learning Project to Portfolio-Ready Application

> Historical planning snapshot. It describes the original starting point and
> is not a checklist of current implementation status. For current features,
> setup, architecture, and outstanding release blockers, see `README.md`,
> `docs/architecture.md`, and `docs/release.md`.

This plan is a build guide, not an instruction to generate the implementation.
Work through it one small task at a time: you write the code, then ask for a
review of the code, design, tests, or error you are working on.

## Project goal

Build a command-line assistant that can answer questions about a codebase by
using explicitly chosen, safe tools to find and read project files. The assistant
should stream its answer, explain which files support the answer, and preserve
conversation context when requested.

The finished project should be:

- useful to run locally from a terminal;
- installable and launchable as a Python package;
- understandable to another developer from the README and documentation;
- tested without requiring a live model or API key for normal test runs;
- safe by default when inspecting files or considering commands;
- easy to review, lint, type-check, and build in continuous integration.

## Working agreement and build rules

- Implement one numbered task at a time; do not try to finish every phase in
  one large change.
- Before changing a module, describe the intended behavior and its inputs,
  outputs, errors, and safety limits.
- Add or update a focused test for each behavior before considering that task
  complete.
- Keep model calls and API credentials out of ordinary unit tests.
- Do not give the model unrestricted shell access.
- Treat file contents as untrusted data, not as instructions to follow.
- Keep `.env` private. If a real API key has been exposed in a commit, screenshot,
  log, or shared output, revoke it and create a replacement.
- Keep dependencies purposeful. Confirm a package is actually needed before
  adding it.
- Update documentation when a behavior, command, configuration setting, or
  architectural decision changes.
- Ask for review when uncertain; review should explain the issue and its reason,
  not silently rewrite the code.

## Current starting point

The repository already has a useful set of folders and some early code:

- `app/main.py` starts the asynchronous CLI.
- `app/cli/interface.py` reads a question, recognizes `exit`/`quit`, and
  streams output from the agent service.
- `app/agent/agent.py` creates a Google Gemini-backed LangChain agent and
  attaches an in-memory checkpointer.
- `app/services/agent_service.py` adapts LangGraph message streaming into text
  chunks.
- `app/services/codebase.py` currently scans only the top level of a hard-coded
  project directory and prints a count. It is an experiment, not yet a reusable
  codebase service.
- `app/tools/` contains outlines for file listing, file reading, searching, and
  command execution. The outlined functions are not implemented yet.
- `app/graph/` contains an outline for a custom workflow, but it is not currently
  connected to the CLI or the agent.
- `tests/` has test folders but little or no test coverage yet.
- `pyproject.toml` declares runtime and development dependencies; review whether
  every declared package is necessary. In particular, Python's `asyncio` is a
  standard-library module and normally should not be declared as an external
  dependency.

Before adding more features, make an inventory of the current behavior and
confirm the project can be installed, launched, and linted in its own virtual
environment. Record current defects separately from new work.

## Recommended target layout

For an installable portfolio project, the recommended destination is a `src/`
layout with a package name that matches the project. Make this migration early,
before many modules and imports depend on the current `app` package.

```text
devai/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
│   ├── architecture.md
│   ├── development.md
│   ├── security.md
│   └── decisions/
├── src/
│   └── devai/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli/
│       ├── agent/
│       ├── tools/
│       ├── graph/
│       ├── core/
│       └── services/
├── tests/
│   ├── unit/
│   │   ├── cli/
│   │   ├── tools/
│   │   ├── services/
│   │   └── agent/
│   ├── integration/
│   └── end_to_end/
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── plan.md
├── pyproject.toml
└── uv.lock
```

This is a target, not a requirement to move folders immediately. An `app/`
layout is perfectly usable for a local learning project. The reason to consider
`src/devai/` is to make the importable package explicit and ensure tests use the
installed package rather than accidentally importing files from the repository
root. If you choose not to migrate, document the choice and keep imports
consistent.

Do not add empty folders just to match a diagram. Create a folder when a real
module or test belongs there. Avoid maintaining both a second custom graph and
the graph already created internally by LangChain's `create_agent` unless the
project has a clear reason for both.

## Folder and module responsibilities

The current `app/` names below map directly to `src/devai/` if you adopt the
recommended package layout.

### Application entry and command line

- `main.py` (eventually `__main__.py`): parse startup options, initialize
  settings/logging, and start the CLI. Keep business logic out of this file.
- `cli/interface.py`: coordinate the conversation loop; call input, application
  service, and output helpers.
- `cli/input_handler.py`: read and normalize terminal input. Do not put model
  calls or project-file operations here.
- `cli/display.py`: render welcome/help text, streamed output, errors, and exit
  messages consistently.

### Agent and model configuration

- `agent/agent.py`: construct the model-backed agent and attach only the tools
  and checkpointer that are intended to be available.
- `agent/config.py`: describe validated settings such as provider/model,
  temperature, and request limits. Keep secrets out of source files.
- `agent/prompts.py`: hold the system instructions. Explain the assistant's
  limits and explicitly treat repository contents as untrusted data.

### Tools

- `tools/filesystem/list_files.py`: list eligible files beneath a selected
  project root; exclude virtual environments, Git internals, caches, and other
  configured generated folders.
- `tools/filesystem/read_file.py`: read one eligible text file after verifying
  it remains inside the allowed project root and is within size limits.
- `tools/search/search_code.py`: find text or code patterns and report paths
  and line numbers. Define ignored folders, supported encodings, and result
  limits.
- `tools/execution/run_command.py`: optional, high-risk capability. Defer it
  until there is a strong use case and a reviewed permission model. Never
  execute arbitrary model-generated or user-provided shell strings.

Each tool should have a narrow input/output contract, explicit failure behavior,
and direct unit tests. Keep tools deterministic and independent of the language
model wherever possible.

### Workflow, services, and shared support

- `graph/state.py`: typed fields that must travel between workflow steps.
- `graph/nodes/`: small workflow steps, each with a clear input and output.
- `graph/workflow.py`: connect those steps only if a custom workflow is needed.
  Decide whether the LangChain agent itself is sufficient first.
- `services/agent_service.py`: application-facing agent operations such as
  streaming an answer, managing conversation identifiers, and translating
  provider/graph results into a stable interface for the CLI.
- `services/codebase.py`: reusable operations on the selected codebase. It
  should accept a project root rather than contain a machine-specific absolute
  path, and it should not print as a side effect.
- `core/config.py`: application settings and project-level defaults.
- `core/exceptions.py`: application-specific exceptions with useful, safe
  messages.
- `core/logging.py`: one place for logging configuration. Never log API keys,
  complete secrets, or unnecessary source contents.

### Tests, documentation, and project configuration

- `tests/unit/`: quick tests of one function or class, using temporary files,
  fake models, and mocks where appropriate.
- `tests/integration/`: verify components cooperate, usually with fake model or
  checkpoint dependencies.
- `tests/end_to_end/`: optional user-visible workflow checks. Keep tests that
  need a real provider/API key separately marked and opt-in.
- `docs/`: explain architecture, setup, operation, safety, and development.
- `pyproject.toml`: project metadata, supported Python version, dependencies,
  console command, and tool configuration.
- `uv.lock`: exact dependency resolution for reproducible installs; update it
  through the chosen package manager when dependencies change.
- `.env.example`: names and harmless example values for required settings.
- `.env`: local secrets only; ignored by Git and never included in examples.
- `.gitignore`: ignore secrets, environments, caches, and build artifacts.
- `README.md`: the short project front page, user quick-start, features, and
  links to deeper guides.
- `LICENSE`: choose a license only after deciding how others may use the work.

## End-to-end request workflow

The intended normal request should travel through the application like this:

1. **Startup** — the package entry point loads validated configuration,
   configures logging, and starts the CLI.
2. **Input** — the CLI reads a question, handles empty input and commands such
   as `help`, `clear`, and `exit`, and assigns or reuses the selected
   conversation ID.
3. **Application service** — the CLI calls a service method with the question,
   conversation ID, project root, and any relevant options. The CLI does not
   know provider-specific details.
4. **Agent/workflow** — the service invokes the configured agent asynchronously
   and streams events. Use a custom graph only if the required steps cannot be
   expressed cleanly through the selected agent API.
5. **Tool selection** — when useful, the agent may request a registered tool.
   The program validates tool arguments and permissions before running it.
6. **Codebase inspection** — the tool checks path boundaries and exclusions,
   performs a bounded operation, and returns concise structured evidence such
   as relative path, line numbers, and excerpts.
7. **Answer generation** — the model uses the question and tool results to
   produce an answer that distinguishes observed evidence from uncertainty and
   cites relevant project paths.
8. **Streaming/output** — the service converts provider events to the app's
   stable text/event format; the CLI displays text as it arrives and reports
   completion or failure.
9. **Memory/checkpoint** — conversation state is associated with a stable,
   non-secret conversation ID. In-memory state is lost when the program exits;
   persistent storage is a later opt-in feature with retention and privacy
   decisions.
10. **Errors and cleanup** — expected provider, configuration, filesystem, and
    cancellation errors become understandable messages. Unexpected exceptions
    are logged with safe context and are not disguised as successful answers.

Keep the boundaries clear: CLI handles people, services coordinate operations,
agents reason, tools perform bounded actions, and core modules provide shared
support.

## Phased implementation plan

### Phase 0 — Define scope and capture the baseline

- [ ] Write a one-sentence product definition and name the first intended user.
- [ ] Choose the initial supported operating system(s) and Python versions.
- [ ] Define a small first release: ask about a local codebase, search/read
      eligible files, stream an answer, and quit cleanly.
- [ ] Decide whether to migrate from `app/` to `src/devai/` now. If yes, do it
      before adding many imports; if no, record why and keep the current layout.
- [ ] Choose one primary orchestration approach: LangChain `create_agent` with
      tools, or an explicitly custom LangGraph workflow. Avoid duplicate
      orchestration until requirements justify it.
- [ ] Run the current application and record exact startup/runtime errors.
- [ ] Record the existing behavior of streaming and memory; distinguish
      in-memory checkpointing from durable conversation storage.
- [ ] Review declared dependencies and remove unneeded packages through the
      package manager; regenerate the lock file rather than editing it by hand.
- [ ] Confirm `.env` is ignored and no real key is tracked. If a key has been
      exposed, revoke it.

**Exit check:** the project runs in its selected environment, the known
limitations are documented, and the package/workflow direction is decided.

### Phase 1 — Reliable project foundation

- [ ] Finalize package layout and import conventions.
- [ ] Configure packaging metadata and a user-facing command in
      `pyproject.toml`.
- [ ] Make project root and model settings configurable rather than
      machine-specific.
- [ ] Validate required environment variables at startup and produce a clear
      missing-key message without displaying the key.
- [ ] Separate runtime dependencies from development dependencies.
- [ ] Pin supported Python versions and confirm the chosen dependencies support
      that range.
- [ ] Configure formatting/linting, tests, and type checking with consistent
      settings.
- [ ] Add a minimal smoke test proving the package imports without making a
      network call.

**Exit check:** a clean environment can install the package and run its help or
startup path without relying on the developer's global Python installation.

### Phase 2 — Friendly CLI and service boundary

- [ ] Keep input, output, and request coordination in their designated modules.
- [ ] Add `help`, `exit`/`quit`, empty-input handling, and graceful Ctrl+C
      behavior.
- [ ] Make streamed output readable, including errors and a final newline.
- [ ] Move static conversation configuration out of the CLI loop.
- [ ] Generate or accept a conversation ID; do not use one constant ID for all
      users/sessions.
- [ ] Define a small application-service interface for asking and streaming a
      question.
- [ ] Add unit tests for command parsing and display behavior.

**Exit check:** the CLI behaves correctly with a fake service and requires no
provider credentials in unit tests.

### Phase 3 — Agent and conversation behavior

- [ ] Put model name/provider and other supported options in validated
      configuration.
- [ ] Keep system instructions separate from construction code.
- [ ] Define exactly which message/event types the streaming service exposes.
- [ ] Handle normal completion, provider failures, cancellation, empty responses,
      and malformed event content explicitly.
- [ ] Test the service with a fake agent; verify chunks and conversation config
      are passed through correctly.
- [ ] Test conversation isolation: two IDs must not share memory accidentally.
- [ ] Document that the current in-memory checkpointer loses data at process
      exit.
- [ ] Add real-provider smoke checks only as optional tests that require
      explicit configuration.

**Exit check:** the model can be replaced with a fake in tests, and the CLI can
stream a response without coupling to provider implementation details.

### Phase 4 — Safe codebase context and tools

- [ ] Accept a project root from validated configuration or a CLI option; do
      not hard-code a developer-specific directory.
- [ ] Resolve and validate the root before inspecting it.
- [ ] Define default exclusions (virtual environments, `.git`, caches, build
      outputs, dependency folders) and allow safe user configuration.
- [ ] Decide how symlinks are handled and prevent traversal outside the allowed
      root.
- [ ] Add maximum file size, result count, and text excerpt limits.
- [ ] Detect or handle binary files and text decoding errors explicitly.
- [ ] Implement file listing and test nested paths, exclusions, symlinks, and
      empty directories.
- [ ] Implement file reading and test missing files, directories, large files,
      encoding errors, and path traversal attempts.
- [ ] Implement search with relative file paths, line numbers, result caps, and
      tests for no matches and excluded folders.
- [ ] Register tools only after their contracts and tests are ready.
- [ ] Return structured tool results so the model can give evidence-based
      answers with file references.
- [ ] Tell the agent that repository text is untrusted and must not override
      system instructions.

**Exit check:** a test project in a temporary directory can be safely listed,
searched, and read; attempts to escape the root are rejected.

### Phase 5 — Workflow and answer quality

- [ ] Decide whether the create-agent tool loop already meets the product need.
- [ ] If a custom graph is needed, define typed state, node contracts, routing,
      error edges, and termination conditions before connecting nodes.
- [ ] Avoid keeping unused placeholder graph modules if the agent abstraction
      fully handles orchestration.
- [ ] Require answers to identify relevant file paths and distinguish facts
      found in source from suggestions or uncertainty.
- [ ] Bound the amount of source text and tool output sent to the model.
- [ ] Add integration tests for question → tool use → evidence → streamed answer
      using a fake model/tool layer.
- [ ] Add regression examples for common codebase questions.

**Exit check:** the full workflow can be exercised without calling a paid
provider, and answers can be traced to bounded tool results.

### Phase 6 — Security, errors, and privacy

- [ ] Create `docs/security.md` covering secrets, local file access, model
      providers, data sent to the provider, and command execution policy.
- [ ] Keep API keys out of code, logs, prompts, test fixtures, and Git history.
- [ ] Use least privilege: register only the tools the user needs.
- [ ] Treat model output as untrusted; validate tool arguments independently.
- [ ] Keep command execution disabled in the first release unless a clear,
      approved design includes an allowlist, no implicit shell, timeouts,
      working-directory limits, output limits, and user confirmation.
- [ ] Avoid sending unnecessary file content to external model providers; make
      provider data flow clear to users.
- [ ] Add request, file, and response limits to reduce accidental resource
      exhaustion.
- [ ] Define safe, actionable errors for invalid configuration, inaccessible
      files, provider failure, and cancellation.
- [ ] Review logs to ensure useful diagnostics do not reveal credentials or
      private source contents.

**Exit check:** documented threat assumptions and tests cover critical path
boundaries, invalid tool inputs, and secret handling.

### Phase 7 — Quality gates and continuous integration

- [ ] Add focused unit tests for core configuration, CLI behavior, services,
      and each tool.
- [ ] Add integration tests for agent/service/CLI collaboration with fakes.
- [ ] Keep live-provider tests optional and clearly marked.
- [ ] Add a supported formatter/linter and run it in CI.
- [ ] Add static type checking and resolve new errors rather than hiding them
      with broad ignores.
- [ ] Run the test suite across the supported Python versions and operating
      systems that the project claims to support.
- [ ] Add CI steps for dependency installation, lint, type checking, tests, and
      package build.
- [ ] Keep coverage focused on meaningful behavior; do not optimize only for a
      percentage.
- [ ] Ensure the lock file is checked and reproducible.

**Exit check:** CI from a clean checkout passes without secrets and produces a
buildable package.

### Phase 8 — Documentation and portfolio presentation

- [ ] Write a concise README summary explaining the problem and what DevAI does.
- [ ] Document prerequisites, setup, configuration, run command, supported
      features, known limitations, and troubleshooting.
- [ ] Add a short demo transcript or screenshot that contains no secrets or
      private project data.
- [ ] Explain the architecture and request workflow in `docs/architecture.md`.
- [ ] Explain local setup, tests, lint/type-check commands, and contribution
      workflow in `docs/development.md`.
- [ ] Explain file access, provider data flow, and command safety in
      `docs/security.md`.
- [ ] Add architecture decision notes for major choices (package layout,
      orchestration, persistence, and provider).
- [ ] Add a license only after choosing terms intentionally.
- [ ] Include a roadmap and clearly label incomplete features; never imply a
      placeholder is a working feature.
- [ ] Make the first-run path easy to copy and verify.

**Exit check:** a new developer can understand, install, configure, run, test,
and evaluate the project using only the repository documentation.

### Phase 9 — Release readiness

- [ ] Review every public command, option, environment variable, and error
      message.
- [ ] Test install and execution from a fresh virtual environment.
- [ ] Check package contents so `.env`, `.venv`, caches, and unrelated files are
      not included.
- [ ] Check Git history for accidentally committed secrets; rotate any exposed
      credentials.
- [ ] Verify version metadata, release notes, license, and repository topics.
- [ ] Tag a small version only after CI and documentation gates pass.
- [ ] Gather feedback from someone who did not build the project and fix
      onboarding problems.

**Exit check:** the release is reproducible, documented, tested, safe within its
stated limits, and honestly describes what it can and cannot do.

## Definition of done for each task

A task is done when:

1. its behavior and limits are clear;
2. the implementation is in the correct module;
3. relevant tests pass, including the edge cases for the behavior;
4. linting and type checks pass for changed code;
5. errors are visible and useful rather than silently ignored;
6. documentation is updated if users or maintainers need to know about it; and
7. the change is small enough to review and explain.

## First recommended tasks

Start with these in order:

1. Confirm the current project runs and record any errors without changing
   unrelated files.
2. Choose whether to migrate to `src/devai/` before implementing more features.
3. Choose whether the first version uses LangChain's agent/tool workflow alone
   or also needs a custom graph.
4. Remove machine-specific behavior and verify configuration/secrets handling.
5. Add tests with fake model responses before expanding tool access.
6. Implement one safe codebase tool at a time, with tests and review after each.

The goal is not to make the folder tree look large. The goal is to make every
module necessary, understandable, tested, and safe.
