---
name: scaffold-memory
description: Copy the product-ops memory/ knowledge-base scaffold (product, patterns, templates, decisions, feedback, stakeholders) into the current project. Use once per project to bootstrap the directory layout that initiative-breakdown, product-spec, and the agent suite expect.
---

# Scaffold Memory

Bootstrap the `memory/` knowledge base in the current project.

The product-ops plugin ships an empty starter scaffold at `${CLAUDE_PLUGIN_ROOT}/memory/`. This skill copies that scaffold into the user's current working directory so the user can fill it in over time.

## Usage

```
/scaffold-memory                # copies into ./memory/ (refuses to overwrite)
/scaffold-memory --force        # overwrites existing files
/scaffold-memory --target docs  # copies to ./docs/memory/ instead
```

## What it does

1. Resolve the plugin root: `echo "$CLAUDE_PLUGIN_ROOT"` (Bash)
2. Read the source scaffold tree at `${CLAUDE_PLUGIN_ROOT}/memory/`
3. Confirm the target path with the user (default: `./memory/`)
4. Refuse to copy if the target exists and `--force` was not passed
5. Copy:
   - `MEMORY.md` — empty index file with example entries (commented out)
   - `README.md` — explainer of what each subdirectory holds
   - `product/`, `patterns/`, `templates/`, `decisions/`, `feedback/`, `stakeholders/` — empty directories with `.gitkeep` placeholders
6. Print a summary of what was copied and a suggested next step:
   - "Open `memory/README.md` to see how each directory feeds the skills"
   - "Start with `memory/product/context.md` — one page describing this product"

## Safe-by-default rules

- Never overwrite without `--force`
- Always print the target path before copying
- After copying, do NOT modify or write further into `memory/` — the user owns the content from this point on

## After scaffolding

Add this to your project's top-level `CLAUDE.md` (or equivalent) so future Claude sessions know the scaffold exists:

```markdown
## Memory

This project uses the product-ops memory scaffold. See `memory/README.md` for the directory layout.
Skills like `/product-ops:initiative-breakdown` and `/product-ops:product-spec` expect this structure.
```

## Why

The product-ops plugin's skills and agents read from `memory/` for product context, patterns, templates, and decisions. Without this scaffold, every skill invocation has to ask the user where context lives, or fall back to plugin defaults that may not match team conventions.

Running this skill once per project is faster than creating the structure by hand and ensures the layout matches what the other skills expect.
