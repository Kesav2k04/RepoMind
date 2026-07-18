# Demo proof checklist

This is a recording and verification checklist, not a voiceover script. It protects Build Week credibility by separating observable product behavior from configuration or claims that still need proof.

## Before recording

- [ ] Open the judge-accessible deployment and confirm `GET /health` responds.
- [ ] Verify the prepared public repository URL is reachable and the task names a real change.
- [ ] Run one **Evidence Mode** analysis without an API key. Confirm the UI labels it deterministic, states that no model calls were used, and shows bounded scope when applicable.
- [ ] Run one genuine **GPT-5.6 Native** analysis only when a valid key and supported `OPENAI_MODEL` are configured.
- [ ] In Native mode, capture all four specialist starts, at least one real read-only tool event, firewall totals, the root reconciliation event, and the final mode label.
- [ ] Confirm invalid repository input receives an actionable inline error.
- [ ] Confirm downloads for `AGENTS.md` and `repo-map.md` work.
- [ ] Confirm the CLI or MCP client can retrieve a preflight for the same repository and task.

## Required visible proof

- [ ] Start with the user outcome: a coding agent gets cited context before its first edit.
- [ ] Show a public repository and a meaningful task. Explain that the task focuses the preflight instead of turning RepoMind into generic codebase chat.
- [ ] Show the complete execution path: repository, evidence pack, Architecture, Risk, Testing, History, citation firewall, reconciliation, `AGENTS.md`, and repository map.
- [ ] Open one retained finding and show severity, citation, reason, recommendation, and confidence.
- [ ] Show the task brief: files to inspect, risk boundaries, and observed checks.
- [ ] Show the generated `AGENTS.md` and repository map, then show the CLI or MCP result entering a coding-agent workflow.
- [ ] Explain Codex accurately as a development collaborator.
- [ ] Explain GPT-5.6 accurately: Native mode launches four independent source specialists with read-only tools, while a separate root reconciles only firewall-verified finding IDs.
- [ ] If a Native-mode run cannot be captured, show Evidence Mode honestly and do not imply Native proof.

## Before publishing

- [ ] Upload a public video under three minutes with audio explaining both Codex and GPT-5.6.
- [ ] Replace an external-artifact placeholder only after opening the final link in an unauthenticated browser session.
- [ ] Add the real Codex `/feedback` session ID.
- [ ] Record the model, timestamp, tool trace, and firewall totals from a real Native run in [SUBMISSION_HANDOFF.md](SUBMISSION_HANDOFF.md).
- [ ] Do not label deterministic screenshots, fallback output, or a mocked test as Native GPT proof.
