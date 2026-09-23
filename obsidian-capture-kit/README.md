# Obsidian Capture Kit

A lightweight capture-and-review flow for feeding interesting ideas into the brain, with a manual promotion path when you actually act on one.

## Folder layout

- `00-Inbox` - new captures land here first
- `10-Active` - promoted notes you are actively moving on
- `20-Shipped` - finished/shipped items
- `90-Reviews` - weekly/periodic review notes

## Quick Capture template

See `templates/Quick Capture.md`. Every new capture defaults to:

- `status: seed`
- `tags: [interesting]`
- `loop_cycle: long`

## Long vs short loop

- **long** - default. Reviewed on the weekly Sunday audit cadence.
- **short** - manual upgrade only. When you take a significant, evidence-backed action on an idea (a ClickUp task, a commit, money spent, a call booked), flip that note's `loop_cycle` to `short` in its frontmatter. Short-loop notes get reviewed every 2-3 days instead of waiting for Sunday.

This upgrade is intentionally manual, not automatic. The scanner surfaces the split; you decide when an idea earned the shorter leash.

## Scanner

`scan_vault.py` is a read-only scanner that walks the vault, groups notes into `long` and `short` buckets by `loop_cycle` frontmatter, sorts each bucket newest-first by `created`, and skips `.obsidian` and other system directories. Supports plain text or JSON output.

```
python3 scan_vault.py /path/to/vault
python3 scan_vault.py /path/to/vault --json
```

## Umbra handoff boundary

This kit is local-first: capture and scanning happen in Obsidian on your machine. Nothing here auto-writes to Umbra/Shade Brain or ClickUp. Promotion (long -> short) is always a manual edit you make in the note itself.
