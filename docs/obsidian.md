# Obsidian — Optional Vault Viewer

goldfish writes your agent's knowledge to plain markdown files in `~/.goldfish/vaults/{project}/`. You can read these with `cat`, search them with `grep`, and version them with `git`.

If you have [Obsidian](https://obsidian.md) installed, you can also open the vault folder for a visual graph view. This is entirely optional — goldfish works identically whether Obsidian is open, closed, or not installed.

## How to open the vault in Obsidian

1. Install Obsidian from [obsidian.md](https://obsidian.md) (free)
2. Open Obsidian → **Open folder as vault**
3. Select `~/.goldfish/vaults/{your-project-name}/`
4. That's it

No plugins. No API key. No configuration.

## What you'll see

Vault notes contain `[[wikilinks]]` in the `related:` frontmatter field. Obsidian renders these as graph edges in the **Graph View** (`Ctrl+G`). You'll see decisions linked to specs, tasks linked to sessions, and lessons linked to errors.

The `_context/wake-up.md` file is regenerated every session — it's the most recently written note and shows what goldfish briefed Claude at the start of the last session.

## Notes on superseded content

Notes that have been superseded set `superseded_by: <id>` in their frontmatter. These notes remain in the vault (they're historical record) but Semble excludes them from search results. In Obsidian they're still visible — useful for understanding how a decision evolved.

## No bidirectional sync

The vault is a **derived index** — it's generated from Claude Code JSONL transcripts and OMEGA memory. Editing vault files in Obsidian will not update OMEGA. If you want to add a spec or decision manually, create a new note in `Specs/` or `Memory/Decisions/` — Semble will index it automatically.
