# Personal Skills Repo

Single source of truth for reusable skills shared across Codex and Claude Code.

## Layout

- `skills/<skill-name>/SKILL.md`: canonical skill instructions
- `skills/<skill-name>/agents/openai.yaml`: optional Codex metadata
- `skills/<skill-name>/references/`: optional examples
- `scripts/skills.sh`: full wrapper for `npx skills` (all commands)
- `scripts/install-skills.sh`: deprecated compatibility shim

Current skills:
- `jenny-tv-srt-tools`

## Wrapper Philosophy

`scripts/skills.sh` is designed to be interchangeable with `npx skills`.
- Same commands (`add`, `remove`, `list`, `find`, `check`, `update`, etc.)
- Same argument semantics
- Adds preflight checks and clearer error hints

It forwards to:

```bash
npx --yes skills@latest <your-args>
```

Pin CLI version if needed:

```bash
SKILLS_CLI_VERSION=0.5.1 ./scripts/skills.sh list
```

## Prerequisites

- Node.js + `npx`
- Internet access (for first-time `npx` package fetch)

If `npx` is missing, wrapper shows install guidance and on macOS can prompt to install Node via Homebrew.

## Quick Start

Install all skills in this repo to Codex + Claude Code globally:

```bash
cd /Users/xcv58/work/skills
./scripts/skills.sh add /Users/xcv58/work/skills -s '*' -a codex claude-code -g -y
```

## Common Commands

List available skills from this repo source:

```bash
./scripts/skills.sh add /Users/xcv58/work/skills --list
```

List installed global skills:

```bash
./scripts/skills.sh list -g
```

Install only one skill:

```bash
./scripts/skills.sh add /Users/xcv58/work/skills -s jenny-tv-srt-tools -a codex claude-code -g -y
```

Install to Codex only:

```bash
./scripts/skills.sh add /Users/xcv58/work/skills -s '*' -a codex -g -y
```

Install to Claude Code only:

```bash
./scripts/skills.sh add /Users/xcv58/work/skills -s '*' -a claude-code -g -y
```

Copy mode (instead of symlink):

```bash
./scripts/skills.sh add /Users/xcv58/work/skills -s '*' -a codex claude-code -g -y --copy
```

Check updates:

```bash
./scripts/skills.sh check
```

Update all installed skills:

```bash
./scripts/skills.sh update
```

Remove one skill globally from both adapters:

```bash
./scripts/skills.sh remove -s jenny-tv-srt-tools -a codex claude-code -g -y
```

## Troubleshooting

- `npx: command not found`
  - Install Node.js (includes `npx`) and rerun.
- Network/DNS errors (`ENOTFOUND`, `EAI_AGAIN`, `ETIMEDOUT`)
  - Check internet/proxy and retry.
- Permission errors (`EACCES`)
  - Use non-global/project mode where applicable or fix npm permissions.
- No skills found
  - Verify source path and `--skill` filter; ensure `SKILL.md` exists.

## Notes

After installing/updating skills:
- Restart Codex to reload skills.
- Start a new Claude Code session (or restart current one).
