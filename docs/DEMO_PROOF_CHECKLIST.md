# Demo proof checklist

This is an operational recording checklist, not a voiceover script. It protects the credibility of the Build Week demo by separating what is visible from what is merely configured.

## Before recording

- [ ] Open the judge-accessible deployment and confirm `GET /health` responds.
- [ ] Verify the prepared public repository URL is reachable and the task text is meaningful.
- [ ] Run one **Evidence Mode** analysis with no API key. Confirm the UI labels it deterministic and shows bounded scope if applicable.
- [ ] Run one genuine **GPT-5.6 Native** analysis only if a valid key and supported `OPENAI_MODEL` are configured.
- [ ] In Native mode, capture all four specialist starts, at least one real read-only tool event, each firewall total, the root reconciliation event, and the final mode label.
- [ ] Confirm an invalid URL returns an actionable inline error.
- [ ] Confirm downloads for `AGENTS.md` and `repo-map.md` work.
- [ ] Confirm the CLI or MCP client can retrieve a preflight from the same repository.

## In the public video

- [ ] Keep the video under three minutes and include audio.
- [ ] Lead with the problem: coding agents make a blind first edit in an unfamiliar repository.
- [ ] Paste a repository and a real task; explain that the task scopes the preflight rather than turning RepoMind into a codebase chat tool.
- [ ] Show the complete execution path: repository -> evidence pack -> Architecture / Risk / Testing / History -> citation firewall -> root reconciliation -> `AGENTS.md` + risk map.
- [ ] Point to a visible tool event and explain that specialists read bounded source through tools rather than guessing from filenames.
- [ ] Point to the firewall counts and explain that uncited claims are withheld.
- [ ] Open one retained finding and show its severity, citation, reason, recommendation, and confidence.
- [ ] Show the generated `AGENTS.md` and risk map, then show the CLI or MCP tool handing the result to a coding agent.
- [ ] Explain that Codex accelerated the build and validation.
- [ ] Explain GPT-5.6 accurately: four independent source specialists use read-only tools; a separate root reconciles only firewall-verified finding IDs.
- [ ] If Native mode cannot be captured, show Evidence Mode honestly and do not imply a native demonstration.

## Before publishing

- [ ] Upload the video publicly and paste its final URL into README, Devpost, and [submission handoff](SUBMISSION_HANDOFF.md).
- [ ] Replace every required external-artifact placeholder only after opening the link in an unauthenticated browser session.
- [ ] Add the real Codex `/feedback` session ID.
- [ ] Record the model, timestamp, tool trace, and firewall totals from a real Native run in the handoff.
- [ ] Do not label deterministic screenshots, fallback output, or a mocked test as native GPT proof.
