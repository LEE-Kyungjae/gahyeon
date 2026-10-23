---
name: gahyeon-nas-archive
description: Reconnect Gahyeon's existing NAS, archive inactive 3D experiments with verified local cleanup, restore archived files, and locate land character sources. Use for NAS storage cleanup and archive recovery in gahyeonbot.
---

# Gahyeon NAS archive

Repository: `/Users/ze/work/gahyeonbot`.
Configuration: `config/storage/nas-archive.json`.
CLI: `python3 tools/nas_archive/harness.py ACTION` from the repository.
MCP server: `gahyeon-nas-archive`; tools `nas_status`, `nas_connect`, `nas_plan`, `nas_execute`, `nas_restore`.

## Existing connection

The existing SMB share is `192.168.2.9/data`, mounted at
`/Users/ze/mnt/dataground-nas`. Reuse the configured mount helper through
`nas_connect` or CLI `connect`. Credentials stay in the existing Dataground
configuration: do not copy them into this skill, manifests, logs, or MCP config.
The harness rejects an absent or wrong mount rather than writing to local disk.

## Archive and recover

1. Read `config/canonical-character-runtime.json` and the NAS allowlist. Keep the
   canonical Unreal project, source code, Git-tracked files and active land
   sources local. Version numbering alone does not prove an asset is unused.
2. Create a unique plan: `plan --name NAME`. Inspect its paths, total size and
   exclusions in `artifacts/storage/NAME.plan.json`.
3. For a user-authorized archive/space-cleanup task, use
   `execute --name NAME --prune`. Without cleanup authorization, omit `--prune`.
   This user's explicit archive-and-cleanup request is sufficient authorization;
   do not ask again for each verified file.
4. The harness copies, fsyncs and SHA-256 verifies each file before removing its
   local original. It refuses changed sources, archive conflicts and symlinks.
   Stop on an integrity error. Resume the same plan after correcting the cause;
   do not reset receipts or overwrite a conflicting archive.
5. Restore an exact file with `restore --name NAME --path RELATIVE_PATH`.
   Changed local files are never overwritten. Metadata and receipts remain on
   both local disk and NAS. Verify a representative restore before completion.

NAS layout: `gahyeonbot-archive/NAME/{files,receipts,plan.json,result.json}`.
Progress: `artifacts/storage/NAME.progress.log` when the CLI is redirected there.
Only one mutating harness process can run at a time. MCP calls serialize with
that same lock. Long archives are better run through the CLI to avoid client
timeouts; use receipts/logs to inspect progress.

## Land source direction

Read `config/storage/land-character-sources.json` for the verified source
inventory and local candidate paths. Keep original files on `ssh land` intact.
The user's selected direction is land-created characters, with the current
Diana runtime retained as fallback until a land candidate passes rendering,
transparency, animation and integration review. Do not mark an imported FBX or
Blender file as service-ready. Never launch retired Electron.

## Validation

`python3 -m unittest discover -s tools/nas_archive -p 'test_*.py' -v`

The 2026-10-11 migration is `legacy-3d-20261011`; consult its actual result and
receipts before reporting completion. Preserve unrelated worktree changes.
