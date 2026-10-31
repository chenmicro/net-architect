# Commit policy

Read this before committing. The agent does not commit autonomously — all file edits
are left uncommitted unless the user explicitly asks. When asked to commit:

- Commit author identity must come from the active `git config` (`git config
  user.name` / `git config user.email` — repo-local config takes precedence over
  global) at the time of the commit. Never source author name/email from any other
  signal (session/environment metadata, chat context, memory, or guesswork). If
  `git config` has no name/email set (locally or globally), stop and ask rather
  than filling one in from elsewhere.
- Every commit must carry a `Co-authored-by` trailer identifying the LLM that
  performed the write, and a `Signed-off-by` trailer attributed to the author
  identity resolved from the active `git config`.
- Commit messages must conform to the [Conventional Commits](https://www.conventionalcommits.org/)
  specification.
- **Use `.git/COMMIT_MSG` for multi-line messages.** Never pass a multi-line
  commit message with `git commit -m` — shell quoting fails on mixed quotes and
  special characters. Heredocs are also prohibited. Instead, write the message to
  `.git/COMMIT_MSG` using your file-writing tool (VS Code excludes `.git/` from file
  watchers, so no save prompt) and commit with `git commit -F .git/COMMIT_MSG`.
  Single-line messages are safe with `-m`. Do not use `/tmp/` paths — they trigger
  VS Code save prompts.
