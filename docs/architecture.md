# DevAI architecture

DevAI is a command-line codebase assistant. The CLI selects a project folder,
passes it to the agent as runtime context, and streams the agent's answer.

## Current request path

1. `app/main.py` starts the asynchronous CLI.
2. `app/cli/input_handler.py` selects and validates the project folder and
   reads questions from the terminal.
3. `app/cli/interface.py` creates `ProjectContext`, creates the agent, and
   coordinates each question.
4. `app/services/agent_service.py` identifies explicit `@path`, recognizable
   unmarked paths, and unique file-name references; it validates them against
   the selected project and directs the agent to read those paths. Search
   requests are handled by the registered code-search tool.
5. `app/cli/interface.py` pauses on an ambiguous basename and asks the user to
   select one of its project-relative matches before invoking the agent.
6. `app/agent/config.py` loads the Gemini API key and model settings from the
   selected project's `.env` file and environment, then validates them.
7. `app/agent/agent.py` constructs the configured model-backed agent and
   registers its tools.
8. `app/agent/prompts.py` defines the assistant's behavior and states the
   current tool limitations.
9. `app/tools/filesystem/list_files.py` provides tools that count eligible
   files by extension or list eligible relative paths.
10. `app/tools/filesystem/read_file.py` provides a bounded UTF-8 file reader
   and an agent tool that reads a requested file from the selected project.
11. `app/tools/search/search_code.py` provides bounded literal search results
   with project-relative paths and line numbers.
12. `app/services/file_edits.py` prepares immutable edit proposals, checks
   whether the original file has changed, and atomically applies approved
   replacements with read-back verification.
13. `app/tools/filesystem/edit_file.py` exposes proposal creation to the agent
   and uses a LangGraph interrupt to pause before any write.
14. `app/core/context.py` defines the application-controlled project root made
   available to tools through LangChain runtime context.

`app/services/codebase.py` contains shared file-exclusion rules and resolves
existing file paths within the selected project. Inventory and future
read/search operations should use these shared rules rather than defining
different path policies.

`AgentConfig` is the single source for the model identifier and temperature.
`DEVAI_MODEL` and `DEVAI_TEMPERATURE` can override their defaults. The
application loads `.env` from the selected project directory after selection;
already-defined environment variables take precedence.

The file-reading tool returns at most 1 MiB of UTF-8 text from a validated
project file. Search is case-insensitive and literal, skips files larger than
1 MiB and non-UTF-8/binary files, and stops after 100 matches.
File edits are complete-file replacements limited to eligible UTF-8 text files
of at most 1 MiB. The agent creates a diff proposal, LangGraph pauses, and the
CLI displays the path, summary, and exact diff. Only an explicit `y` or `yes`
resumes the workflow with approval. Rejection or any other response does not
write. Before applying, the service revalidates the path and original content
fingerprint, then writes through a temporary file in the same directory and
verifies the resulting content.

## Current tool capabilities

The agent can count eligible files by extension and list up to the configured
maximum number of eligible paths. The tools skip configured generated
directories, secret environment files, bytecode files, and symbolic links.

The user may reference a file by project-relative path, basename, or with
optional `@`; paths containing spaces should be quoted. A unique basename is
resolved automatically. If multiple eligible files share that basename, the
CLI asks the user to choose before invoking the agent. Recognized paths are
validated before the agent is called. The agent does not have tools to execute project commands. Do not treat the
presence of placeholder modules for other features as implemented capability.

## Design boundaries

- The CLI handles interaction with the user.
- The application chooses the project root; the model does not choose an
  arbitrary filesystem path.
- The agent decides whether an available tool is useful for the user's
  question.
- Tools perform bounded operations and return results to the agent.
- The application, never the model, collects file-edit approval from the user.
- The service adapts agent streaming for the CLI.

The project also contains placeholder modules for future workflows and tools.
Those modules are not part of the current request path until implemented and
registered.

Command execution is disabled. Its implementation must follow the approval,
allowlist, timeout, output-limit, and project-boundary requirements in
[`security.md`](security.md) before it can be registered as an agent tool.
