# OpenAI Build Week submission requirements

Source: [official OpenAI Build Week rules](https://openai.devpost.com/rules). Verify the live Devpost form and deadline before submitting because event details can change.

## Required submission material

- A working project built using Codex and GPT-5.6.
- A selected category. RepoMind belongs in **Developer Tools**.
- A clear project description that explains the product and how it works.
- A public YouTube video under three minutes. It must show the project working and include audio explaining how both Codex and GPT-5.6 were used.
- A public code repository, or private access shared with `testing@devpost.com` and `build-week-event@openai.com`.
- A README with setup, run, testing, and product guidance. It must disclose how Codex accelerated the work, key decisions, and how Codex and GPT-5.6 were used.
- The Codex `/feedback` session ID where most core functionality was built.
- For a developer tool, installation guidance, supported platforms, and a way for judges to test it without rebuilding.

## Judging criteria

The published criteria are equally weighted:

1. **Technological Implementation:** skillful use of Codex and a working, non-trivial implementation.
2. **Design:** a complete, coherent runnable product experience.
3. **Potential Impact:** a credible solution for a real audience and problem.
4. **Quality of the Idea:** creativity, novelty, and differentiation.

## RepoMind readiness checklist

| Requirement | Current repository evidence | Creator action still required |
| --- | --- | --- |
| Working project | Backend tests, frontend lint, frontend tests, and production build run in [CI](https://github.com/Kesav2k04/RepoMind/actions/workflows/ci.yml). | Keep CI green through submission. |
| Developer Tools category | The product is a cited preflight for coding agents and contributors. | Select Developer Tools in Devpost. |
| Repository access | [GitHub repository](https://github.com/Kesav2k04/RepoMind) is public. | Confirm the public URL opens while signed out. |
| Setup and testing | [README](README.md) covers dashboard, CLI, MCP, runtime modes, and verification. | Keep commands aligned with the release. |
| Codex and GPT-5.6 disclosure | [README](README.md#how-codex-and-gpt-56-contributed) distinguishes development use, Native mode, and deterministic controls. | Add the genuine feedback session ID. |
| Public project page | [Devpost project](https://devpost.com/software/repomind-context-before-code) is the known project URL. | Ensure its title, description, thumbnail, and links match the release. |
| Video proof | A checklist exists in [docs/DEMO_PROOF_CHECKLIST.md](docs/DEMO_PROOF_CHECKLIST.md). | Record and publish the real video. |
| Live testing path | Deployment guidance exists in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). | Publish and verify a judge-accessible URL. |
| Native runtime proof | Native-mode behavior is documented and tested at contract level. | Capture a real Native-mode run with a valid key and supported model. |

## Submission guardrails

- Do not present Evidence Mode, a mocked test, or deterministic output as Native GPT-5.6 proof.
- Do not claim a live deployment, public video, or feedback session until the real artifact is available.
- Keep a public final repository or grant both required judge accounts private access before submitting.
- Use the [submission handoff](docs/SUBMISSION_HANDOFF.md) as the source of truth for final links and proof.
