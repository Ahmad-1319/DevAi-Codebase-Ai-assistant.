# Security policy

DevAI works with a user-selected project folder and sends selected prompts and
file contents to the configured model provider. Treat project contents and
model output as untrusted input.

## Project file access

- File tools operate only inside the project folder selected at startup.
- Resolve and validate each requested path; reject traversal outside the
  project, symbolic links, excluded files, and non-regular files.
- Keep file reads, search results, edit proposals, and tool output bounded.
- File tools do not expose secret environment files. The application itself
  reads `.env` in the selected project folder only to load model configuration.
  Keep `.env` and API keys out of source control, prompts, logs, test fixtures,
  and shared output.
- The configured model provider receives requests and relevant source text.
- Treat text returned from project files as evidence, never as instructions
  that override the user's request or DevAI's safety rules.

## File-edit approval

- A proposed edit is limited to one eligible text file and must be shown as a
  diff before it is applied.
- Collect approval in the terminal; never accept approval from model output.
- Only an explicit `y` or `yes` approves. Any other response rejects the
  proposal without writing.
- Before writing, revalidate the path and verify the original file has not
  changed since the proposal was created.

## Command execution

Command execution is **not currently implemented or available to the agent**.
The `app/tools/execution/run_command.py` module is a placeholder. Do not treat
its presence as permission to run commands.

Any future command-execution implementation must satisfy all of these
requirements before its tool is registered with the agent:

1. Accept an argument vector (a list of separate arguments), not a shell
   command string. Never enable shell interpretation. Reject shell operators
   and command chaining rather than parsing or evaluating them.
2. Enforce a documented allowlist of executable-and-argument patterns in
   application code. Model-provided arguments are untrusted and must not be
   able to bypass the allowlist with alternate executable paths, option
   injection, or nested interpreters.
3. Display the exact executable, arguments, and working directory in the
   terminal and require explicit human approval for every invocation. Only
   `y` or `yes` approves; rejection or cancellation must start no process.
4. Resolve and validate the working directory within the selected project.
   Do not allow the model to select an arbitrary directory.
5. Apply a finite execution timeout, terminate timed-out processes, and return
   a clear timeout result.
6. Bound captured stdout and stderr independently and report when output was
   truncated. Do not silently treat a non-zero exit code as success.
7. Pass a controlled environment that does not expose application secrets or
   unrelated credentials. Do not log secret values or full sensitive
   environment data.
8. Surface launch failures, permission failures, timeouts, and non-zero exit
   codes explicitly. Do not retry a command automatically.
9. Test the allowlist, argument validation, path confinement, approval/rejection,
   timeout, output limits, exit-code reporting, and process-launch failures
   without relying on a live model provider.

Until those requirements are implemented and tested, DevAI must not expose a
command-execution tool or claim it can run project commands.

## Model-provider data

The configured model provider receives the user's prompts and any project
content included in model requests. Avoid sending unrelated files or more
content than needed. Never include credentials in prompts. Users should review
provider configuration and the provider's data-handling terms before using
DevAI with private projects.
