# CCAR-P resources

Collected 2026-10-09. Only the official guide (`official-exam-guide.md`) is authoritative. Everything else is third-party; check every format claim against the official guide.

## Official (Anthropic Partner Academy, needs partner login)

- Learning path: https://anthropic-partners.skilljar.com/path/claude-certified-architect-professional
- Certification page (exam guide, prep, registration): https://anthropic-partners.skilljar.com/claude-certified-architect-professional-certification#ccarf-prep
- Certifications FAQ: https://anthropic-partners.skilljar.com/page/faq-certifications

## Official docs (recommended by the Reddit poster and by the exam guide)

- Claude & API docs: https://docs.claude.com
- Claude Code docs: https://code.claude.com/docs/en/overview
- MCP spec/docs: https://modelcontextprotocol.io
- Claude API reference: https://platform.claude.com/docs/en/home
- Anthropic Cookbook: https://github.com/anthropics/anthropic-cookbook
- Prompt engineering guide: https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview
- Anthropic Academy: https://www.anthropic.com/learn/build-with-claude
- Engineering blog ("Building Effective Agents", context engineering): https://www.anthropic.com/engineering

## Practice exams and guides (third-party)

- Timo Labs free mock (20 questions): https://www.timolabs.dev/mock-exams/ccar-p
- claudearchitectguide.com practice exam (unofficial): https://claudearchitectguide.com/ccar-p
- Udemy CCAR-P Exam Prep: https://www.udemy.com/course/ccar-p-exam-prep/?couponCode=KEEPLEARNING
- Preporato complete guide: https://preporato.com/blog/claude-certified-architect-professional-complete-guide-2026
- claudecertificationguide.com blueprint: https://claudecertificationguide.com/blog/claude-certified-architect-professional-exam-guide

**Quality warning.** The Reddit poster below says most cheat sheets and practice exams are visibly Claude-generated and drift from the blueprint. They dropped a Udemy practice exam halfway for that reason. Use mocks for timing and question-style practice. Do not trust their "facts" without the official guide.

## First-hand report: Reddit r/Anthropic

URL: https://www.reddit.com/r/Anthropic/comments/1vrlals/passed_the_claude_certified_architect/

Only first-hand CCAR-P report found as of 2026-10-09. One person; 4–5 years with AI systems, daily Claude Code use in production. Summary:

- **Difficulty:** "Moderately easy." Noticeably easier than CCAR-F. Less depth than Foundations. Advice: if you passed Foundations, go straight for it.
- **Split:** ~40% of questions are immediate; ~60% need a careful read of the scenario paragraph and trade-off reasoning.
- **Trap:** some questions ask "what at this step" and then "what before this process". The process under discussion is stated only in the first line. Read the setup line twice.
- **Frequent topics:**
  - MCP and tool integration trade-offs; call an API directly vs wrap it
  - Agentic orchestration vs single-shot execution
  - Few-shot vs single-shot prompting (some nuanced cases)
  - System decomposition (a lot)
  - Prompt design for production: structure and maintenance at scale
  - AI governance applied in practice, not definitions
  - Architecture trade-offs for highly secure or regulated environments
- **What to study:** governance and security trade-off scenarios. The poster says these are less intuitive than the tooling questions.

Note: the poster mentions "scenario paragraphs". The official guide does not describe a scenario bank. These are probably standalone items with a short scenario stem, like the official samples.
