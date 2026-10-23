# Trusted research and owner workspace tools

Implemented 2026-10-16. Local source and isolated fixtures are verified; the production bot is not deployed or enabled. Owner identity confirmation is pending. Production request count is zero.

## Trust boundaries

`DefaultAgentRuntime -> AgentSkillHarnessFactory -> RequestScopedTools` uses the existing internal ActorId and tool scope. New providers receive server context; there is no model-controlled actor, scope, host, shell command, or workspace-root argument. Unknown/missing owner configuration returns no work bindings. Display names never grant access.

The released `web-research@1.0.0` and `owner-workspace@1.0.0` procedures use disjoint tools. A selected skill cannot switch mid-run. A page can contain instructions as quoted tool data, but cannot register tools, alter the skill, or access the worker through the research tool. Existing native tools remain available before selection; the newly added remote tools require selection.

Remote tasks use the existing exact-argument approval service. The configured owner and scope are checked before discovery and again by the worker envelope. The SSH credential is held only by the broker, is distinct from normal administrator credentials, and must be restricted to the forced-command worker. The worker does not independently authenticate an arbitrary JSON actor: possession of the restricted SSH key authenticates the trusted broker. Never expose its stdin protocol as an anonymous HTTP API.

## Search and sources

`research_search` uses the public Bing RSS endpoint for discovery. It requires no API secret, but is not a contracted search API; availability, relevance and rate limits are not guaranteed. Provider/model quality needs a production canary before promotion. SearXNG was reviewed as a future operator-owned provider; it was not installed or silently substituted.

Outbound search is frozen to the first authenticated user question and cached for that request; model-supplied follow-up queries cannot transmit page-requested private data. Reads accept only exact URLs present in that original question or returned by search, plus their revalidated redirects. Appending an exfiltration query or inventing a new destination is rejected before network access. This deliberately limits iterative query refinement in v1.

`research_read` permits public HTTPS only. It checks IP addresses and pins checked IPv4 DNS results to the TLS connection, rejects private/link-local/metadata/reserved destinations, ignores IPv6 rather than guessing about NAT64, and revalidates each redirect (maximum three). Cookies and ambient credentials are not forwarded. Each hop has a 12-second deadline, 512 KiB body cap, and no automatic retry. A run has at most ten fetches. The resulting plain text is bounded to 16,000 characters. Extraction does not execute JavaScript and is not an injection classifier.

Source labels come from the final host, not page claims, suffix substring matching, or rank. Known documentation hosts receive a first-party provenance label; Apple forums and Microsoft Answers remain user-published. GitHub and Naver blogs are user-published. Reuters/AP/BBC labels still require corroboration. Unknown domains are unreviewed and share an unverified-ownership bucket. This small initial registry is deliberately incomplete and is not a general reputation service.

`research_verify` requires exact short quotations from pages read in that request. It reports publisher/content upper bounds, duplicate hashes and missing self-reported dates. It explicitly returns `truthVerified=false` and `independenceVerified=false`: quote matching cannot prove the claim, editorial independence, syndication origin, or freshness. A retrieved publication date is self-reported; fetch time is not publication time. The procedure requires checking relevance, conflicting claims, event dates, advertising/contribution context and original sources before citing. Semantic deception, paraphrased copying, compromised official sites, and model hallucinations are not solved by these deterministic guards.

## Worker operations

The worker supports status, bounded directory listing, UTF-8 file reading, compare-and-swap file writing and one operator-configured test command. Every remote call currently requires an exact-argument approval; there is no arbitrary shell, deletion, deployment, package-install, production service restart or media/GPU operation tool.

Start with a dedicated clean workspace. Do not point it at a home directory or copy secrets/credentials into it. The workspace does not automatically include the current dirty repository or all character assets. File writes require the last read SHA-256 or `absent`; traversal, symlinks, hardlinks and common credential paths are denied. Job state resides outside the writable workspace, is locked, and prevents retrying a mutation after an interrupted/duplicate job. Keep a single writer for the workspace. This is not protection against an administrator concurrently replacing filesystem paths.

Tests run with a clean environment and no stdin. macOS uses a deny-default Seatbelt profile, with only system/Xcode runtime reads and workspace writes; Linux uses bubblewrap with a private network namespace, read-only system runtimes and a writable workspace. Linux scratch `/tmp` is ephemeral and not the host's `/tmp`. Missing sandbox support fails closed. Each test has a 60-second wall limit and 48 KB output limit; its process group is stopped after completion. This v1 does not provide a hard aggregate memory/CPU/disk quota for arbitrary adversarial test programs. Do not approve unreviewed resource-heavy jobs; it is intended for bounded development tasks, not media generation.

## Preparing persistent endpoints

1. Confirm the user's numeric Discord ID, resolve it through the existing `external_identities` DISCORD row to `principal_id`, and verify the intended guild/scope. Do not infer identity from a display name or create a new account authority.
2. Generate distinct dedicated Ed25519 client keys for Mac and land on the broker. Keep private keys outside source control and outside any worker workspace.
3. Transfer each **public** key to its target. Run `python3 scripts/owner_work/prepare_worker.py --base <new-private-endpoint-directory> --owner-actor <internal-id> --scope <guild-id> --target mac --public-key <public-key-file> --listen <private-LAN-IP> --port 2222` (use target `land` on land). It refuses to overwrite an existing directory, writes a forced-command key/config, and prints the exact SSH daemon command without starting it. The default listen address is loopback.
4. Review the generated fixed workspace, test command and host-key fingerprint. Copy the host public key into the broker's dedicated `known_hosts` using the verified endpoint address and port. Do not disable host verification or substitute ordinary SSH admin keys. Start the printed dedicated daemon under the target account, with service supervision appropriate to that host. System SSH settings are untouched. Limit network reachability to zeze where available.
5. Mount the broker's SSH configuration, pinned known_hosts and dedicated private keys read-only at `/app/owner-work`. `config/owner-work/ssh_config.example` names the two fixed aliases. The Dockerfile includes openssh-client. Verify connectivity **from the actual production container**; host-level reachability is insufficient.
6. Set the confirmed actor/scope and enable flags only in an explicitly authorized release. Use the existing quality gate, source/artifact/config identity, and canary observation contracts. Owner-work may be enabled separately from research. Keep secrets and keys out of logs and prompts.

A wrong identity, unknown host key, missing SSH client/config, inactive worker, unavailable sandbox, failed test or changed file hash must fail rather than report success. Disable `GAHYEON_AGENT_OWNER_WORK_ENABLED` / `GAHYEON_AGENT_RESEARCH_ENABLED` independently to revoke capabilities. Paused skilled runs must restart after a feature rollback instead of resuming without restrictions. Do not roll back to an old binary that cannot read newer ledger event enums.

## Evidence and tests

Evidence window: 2026-10-16 KST local development. Existing 2026-10-15/16 Discord tool-use complaints motivate the capability; injection/owner-authority cases are preventive, not claims of an observed attack.

Artifacts under `artifacts/trusted-research-owner-work-20261016/` record the live search smoke, real macOS/Linux sandbox tests, `zeze -> Mac` ephemeral dedicated SSH fixture and `zeze -> land` worker protocol fixture. Synthetic fixture IDs are never production owner grants. Ephemeral Mac listeners and keys were removed. land has bubblewrap installed and worker source staged under `~/.local/share/gahyeon-owner-work-v1`; no production actor grant or persistent new endpoint was enabled.

Run:

```sh
python3 scripts/owner_work/test_worker.py
./gradlew test --tests 'com.gahyeonbot.services.ai.agent.*'
bash scripts/run_ai_quality_gate.sh
# Explicit network smoke, separate from deterministic regressions:
GAHYEON_RESEARCH_LIVE_SMOKE=true ./gradlew test --tests '*ResearchLiveSmokeTest' --rerun-tasks
```

`quality/ai-regressions.json` contains executable injection/identity/provenance/filesystem/replay cases. Existing ledger tool event/outcome/digest signals allow aggregate monitoring; do not export page bodies, file content, identifiers or credentials as metrics. A single unauthorized execution, workspace escape, duplicate mutation or fabricated completion is a stop/disable trigger. No qualifying production traffic has been observed for these new tools.

## Reviewed references

- https://github.com/modelcontextprotocol/modelcontextprotocol/security — client/server trust assumptions; tool metadata is not an authority grant.
- https://github.com/modelcontextprotocol/servers/security — server security scope and reporting; a generic filesystem server is not itself a sufficient execution boundary.
- https://github.com/anthropics/sandbox-runtime — OS-level filesystem/network isolation and process-tree boundaries. We reused native OS primitives, not the package or its source code; this is not equivalent to its full hardened implementation.
- https://github.com/NVIDIA-NeMo/Guardrails — programmable retrieval/input/output rails; reviewed as a complementary approach, not installed or treated as a complete injection defense.
- https://github.com/searxng/searxng — self-hosted metasearch option; evaluated, not deployed.
