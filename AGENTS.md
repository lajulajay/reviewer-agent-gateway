# Agent instructions

## Shell discipline

- Run one shell command per tool call. Do not join commands with `&&`, `;`, `||`, or pipes, or put multiple commands in one shell invocation.
- Set the working directory through the tool's `workdir` option. If the tool uses a persistent shell without that option, run `cd <dir>` as its own call.
