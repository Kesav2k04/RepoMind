# OpenAI Build Week Challenge Rules & Requirements

## Key Information
- **Submission Deadline:** Tuesday, July 21 at 5:00 PM PT.
- **Track:** Developer Tools (Tools for developers, including testing, DevOps, agentic workflows, and security).
- **Core Requirement:** Create a project using Codex with GPT 5.6.

## Submission Checklist
- [ ] **A working project**: Build something with Codex using GPT-5.6.
- [ ] **A category**: Developer Tools.
- [ ] **A project description**: Tell what you created and how it works.
- [ ] **A demo video**: <3-minute public YouTube video showing the project working, audio covering how Codex AND GPT-5.6 were used.
- [ ] **Code Repository URL**: Public or private (shared with testing@devpost.com and build-week-event@openai.com).
- [ ] **README**: Include setup instructions, sample data, clear guidance for running. *Make sure to highlight where Codex accelerated your workflow, where key decisions were made and how GPT-5.6 and Codex were used.*
- [ ] **/feedback Codex Session ID**: Input the session ID where the majority of the core functionality was built.
- [ ] **Dev Tool Specifics**: Include installation instructions, supported platforms, and a way for judges to test without rebuilding (e.g., demo instance).

## Judging Criteria (Equally Weighted)
1. **Technological Implementation**: How thoroughly and skillfully does the project use Codex? Non-trivial implementation.
2. **Design**: Delivers a working/runnable project with a complete product experience, not just a technical POC.
3. **Potential Impact**: Solves a real problem for a real audience.
4. **Quality of the Idea**: Creative, novel, and differs from existing concepts.

## GPT-5.6 Features to Leverage
- **Programmatic Tool Calling**: Writes JavaScript to call eligible tools, pass results, and process intermediate outputs.
- **Multi-agent (beta)**: Coordinate multiple subagents in parallel and synthesize results.
- **Pro mode**: More model work for improved reliability on difficult tasks (`reasoning.mode: "pro"`).
- **Persisted reasoning**: Reuse available reasoning items across turns (`reasoning.context: "all_turns"`).
