# Obsidian capture kit

A deliberately small intake lane for Shade Brain/Umbra. It is a local vault
pattern and scanner, **not** a running service and not an automatic task
creator. The default is intentionally low-pressure: capture it, mark it
`interesting`, and let the weekly Sunday Calendar & Energy Audit decide whether
it deserves more attention.

## What is in here

```text
obsidian-capture-kit/
├── templates/
│   └── Quick Capture.md       # Obsidian template for a new idea or observation
├── vault/                     # optional starter folders; copy into a real vault
│   ├── 00-Inbox/
│   ├── 10-Active/
│   ├── 20-Shipped/
│   └── 90-Reviews/
└── scan_vault.py              # read-only long/short loop report
```

The folder names are optional organization, not state. A note's frontmatter is
the source of truth. Keep quick captures in `00-Inbox` if that is useful; move
notes later without changing their loop behavior.

## Set up the capture flow

1. Copy `templates/Quick Capture.md` into your vault's template folder (for
   example, `.obsidian/templates/`) and set Obsidian's Templates plug-in to use
   that folder.
2. Copy the optional `vault/` folders into the vault if you want the starter
   layout. Do not copy the kit's own `README.md` or scanner into the note area
   unless you want them searchable in Obsidian.
3. On iPad or desktop, create a note with **Quick Capture**. Give it a plain
   title, type the idea, and leave it alone. The template sets `tags:
   [interesting]` and `loop_cycle: long` by default.
4. Run the scanner before the Sunday audit or a morning planning session:

   ```bash
   python3 /path/to/obsidian-capture-kit/scan_vault.py "/path/to/Your Vault"
   ```

New captures are `seed` notes on the long loop: they are reviewed in the weekly
Sunday audit, not repeatedly poked at during the day. That protects the early
5-9am deep-work window from every passing thought turning into a priority.

## Frontmatter contract

Every new capture starts with these fields:

```yaml
status: seed                 # seed | active | shipped
created: "2026-09-23"       # Obsidian fills this from the template
source: "quick capture"     # where the thought came from
tags:
  - interesting
loop_cycle: long             # long = weekly Sunday audit
significance: "unrated"
```

Use `source` for context that helps later: `pre-dawn iPad`, `client call`,
`grant research`, `code review`, or a link. `significance` is intentionally a
human judgment, such as `unrated`, `worth tracking`, or `significant`.

## Upgrade: long loop -> short loop

Do **not** promote an idea because it is merely exciting. Promote it only after
there is concrete movement tied to the note:

- a ClickUp task was created;
- code was committed;
- money was spent; or
- James explicitly marked it significant.

Then make the manual, reviewable change in that note's frontmatter:

```yaml
loop_cycle: short
significance: "significant"
```

Also add a one-line receipt in **Evidence / movement**, for example:

```md
- 2026-09-23: created ClickUp task TES-184 for site estimate follow-up.
```

A short-loop item is eligible for a daily or every-2-3-day check-in. It is not
a command to create, change, pay for, or send anything. For Shade Brain/Umbra
and any agent, this is the approval-gated contract: the agent may read and
surface the promotion; only an explicit action/evidence or direct mark permits
changing `loop_cycle` from `long` to `short`.

When the work is done, set `status: shipped`. Move the file to `20-Shipped` if
that helps navigation; it can retain either loop setting until the next review.

## Scanner

`scan_vault.py` recursively reads Markdown notes, ignores `.obsidian`, `.trash`,
`.git`, and `node_modules`, and prints two lists sorted newest-first by
`created`: short-loop items first, then long-loop items. It never edits notes.

```bash
# Human-readable weekly report
python3 scan_vault.py "/path/to/Your Vault"

# Export a machine-readable report for a local, approval-gated Umbra review job
python3 scan_vault.py "/path/to/Your Vault" --format json --output /tmp/capture-loops.json
```

The scanner uses PyYAML when it is installed. With a plain Python install, it
falls back to the simple scalar/list YAML form emitted by `Quick Capture.md`,
so this kit has no required package install. Malformed frontmatter becomes a
warning; it does not stop the rest of the vault from being surfaced.

## Umbra handoff, without pretending this is deployed

A future local Shade Brain job can run the JSON command above during the Sunday
review, use `long_loop` as the interesting backlog, and use `short_loop` as the
check-in queue. It should preserve the same boundary: ingestion is read-only
and interesting-by-default; changing a note's state or loop is a visible,
evidence-backed, approval-gated action. No daemon, sync, ClickUp integration,
or background watcher is installed by this repository.
