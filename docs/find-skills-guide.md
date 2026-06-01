# Find Skills — Complete Guide

The **Find Skills** workflow helps you discover, evaluate, and install agent skills from the open agent skills ecosystem. Skills extend agent capabilities with specialized knowledge, workflows, and tools for specific domains.

---

## Table of Contents

1. [What Are Skills?](#what-are-skills)
2. [The Skills CLI](#the-skills-cli)
3. [When to Use This Skill](#when-to-use-this-skill)
4. [Step-by-Step Workflow](#step-by-step-workflow)
5. [Common Skill Categories](#common-skill-categories)
6. [Search Tips](#search-tips)
7. [Installing Skills](#installing-skills)
8. [When No Skills Are Found](#when-no-skills-are-found)

---

## What Are Skills?

Skills are modular packages that extend agent capabilities. They bundle:

- **Specialized instructions** — domain-specific workflows and best practices
- **Reference material** — curated docs, examples, templates
- **Scripts and tools** — automation for common tasks

Skills live in the open ecosystem at [skills.sh](https://skills.sh/) and are installed via the Skills CLI (`npx skills`).

### How Skills Differ From General Chat

| Without a Skill | With a Skill |
|---|---|
| Agent guesses best practices | Agent follows battle-tested workflows |
| Agent may hallucinate tool usage | Tool usage is explicitly scripted |
| Each session starts from scratch | Consistent, repeatable behavior |
| No structured output formats | Pre-defined templates and schemas |

---

## The Skills CLI

The Skills CLI (`npx skills`) is the package manager for agent skills.

### Commands

| Command | Purpose |
|---|---|
| `npx skills find [query]` | Search for skills by keyword |
| `npx skills add <package>` | Install a skill from GitHub or other sources |
| `npx skills remove <package>` | Uninstall a skill |
| `npx skills list` | List installed skills |
| `npx skills check` | Check for skill updates |
| `npx skills update` | Update all installed skills |
| `npx skills init` | Scaffold a new skill project |

### Global vs Local Installation

- **Global** (`-g`): Installed at the user level, available across all projects
- **Local**: Project-specific, lives in the project directory

---

## When to Use This Skill

Use the Find Skills workflow when you (the user) ask for help with something that might have an existing skill.

### Triggers

| User Says | Translation |
|---|---|
| "How do I do X?" | There might be a skill for domain X |
| "Find a skill for X" | Search the ecosystem for X |
| "Is there a skill that can X?" | Check if X is a known capability |
| "Can you do X?" | Maybe — let me check if a skill exists |
| "I wish I had help with X" | X might be a skill you can install |

### Anti-Patterns

- Do **not** search for skills when the task is trivial (single file edit, simple question)
- Do **not** search for skills when the user explicitly says "don't use a skill"
- Do **not** skip the verification step (install count, source reputation)

---

## Step-by-Step Workflow

### Step 1: Understand the Need

Identify three things:

1. **Domain** — e.g. React, testing, deployment, design
2. **Specific task** — e.g. writing tests, reviewing PRs, creating animations
3. **Commonality** — Is this something many people do? If yes, a skill likely exists.

**Examples:**

| User Says | Domain | Task |
|---|---|---|
| "Make my React app faster" | React | Performance optimization |
| "Help me review this PR" | Code review | PR review workflow |
| "Create a changelog" | Documentation | Changelog generation |

### Step 2: Check the Leaderboard

Before running a CLI search, check [skills.sh](https://skills.sh/) for the leaderboard. The leaderboard ranks skills by total installs.

**Top skills** (as of 2026):

| Skill | Source | Installs |
|---|---|---|
| React | `vercel-labs/agent-skills` | 100K+ |
| Next.js | `vercel-labs/agent-skills` | 100K+ |
| UX/Frontend Design | `anthropics/skills` | 100K+ |
| Document Processing | `anthropics/skills` | 100K+ |

A leaderboard hit means you can skip the search and go straight to presenting options.

### Step 3: Search for Skills

If the leaderboard doesn't cover the need, use the CLI:

```bash
npx skills find <query>
```

**Query tips:**

- Use specific keywords: `react testing` > just `testing`
- Try alternatives: `deploy` → `deployment` → `ci-cd`
- Combine terms: `pr review` better than `pr`

**Example searches:**

```bash
# Search for React performance skills
npx skills find react performance

# Search for PR review skills
npx skills find pr review

# Search for changelog automation
npx skills find changelog

# Search for testing skills
npx skills find jest playwright
```

### Step 4: Verify Quality

**Never recommend a skill based solely on search results.** Always verify:

1. **Install count** — Prefer 1K+ installs. Be cautious under 100.
2. **Source reputation** — `vercel-labs`, `anthropics`, `microsoft` are trusted. Unknown authors need scrutiny.
3. **Repository stars** — Check the source GitHub repo. <100 stars = skepticism.

**Red flags:**

- Zero or very few installs
- Unknown author with no repo history
- Description is vague or mismatched
- Last updated more than 6 months ago

### Step 5: Present Options

When you find relevant skills, present them with:

1. **Name and description** — What the skill does
2. **Install count and source** — Evidence of quality
3. **Install command** — Exact command to run
4. **Link to learn more** — skills.sh URL

**Example response:**

```
I found a skill that might help! The "react-best-practices" skill provides
React and Next.js performance optimization guidelines from Vercel Engineering.
(185K installs)

To install it:
npx skills add vercel-labs/agent-skills@react-best-practices

Learn more: https://skills.sh/vercel-labs/agent-skills/react-best-practices
```

### Step 6: Install (on request)

Only install if the user explicitly asks. Use:

```bash
npx skills add <owner/repo@skill> -g -y
```

- `-g` — Global (user-level) installation
- `-y` — Skip confirmation prompts

---

## Common Skill Categories

| Category | Example Queries |
|---|---|
| **Web Development** | react, nextjs, typescript, css, tailwind |
| **Testing** | testing, jest, playwright, e2e |
| **DevOps** | deploy, docker, kubernetes, ci-cd |
| **Documentation** | docs, readme, changelog, api-docs |
| **Code Quality** | review, lint, refactor, best-practices |
| **Design** | ui, ux, design-system, accessibility |
| **Productivity** | workflow, automation, git |

---

## Search Tips

1. **Be specific** — `react testing library` > `testing`
2. **Use domain jargon** — `e2e` > `end to end`
3. **Iterate** — If `deploy` returns nothing, try `deployment` or `ci-cd`
4. **Check popular sources** — Many skills come from:
   - `vercel-labs/agent-skills`
   - `anthropics/skills`
   - `ComposioHQ/awesome-claude-skills`
5. **Browse the ecosystem** — Visit [skills.sh](https://skills.sh/) to explore

---

## Installing Skills

### Install a specific skill from a package

```bash
npx skills add owner/repo@skill-name -g -y
```

### Install an entire package

```bash
npx skills add vercel-labs/agent-skills -g -y
```

### Verify installation

```bash
npx skills list
```

### Update skills

```bash
npx skills check   # Check for updates
npx skills update  # Apply updates
```

---

## When No Skills Are Found

If no relevant skill exists:

1. **Acknowledge** — No matching skill was found
2. **Offer direct help** — The agent can still assist using general capabilities
3. **Suggest creating a skill** — If the task is repeated often:

```bash
npx skills init my-custom-skill
```

**Example response:**

```
I searched for skills related to "xyz" but didn't find any matches.
I can still help you with this task directly! Would you like me to proceed?

If this is something you do often, you could create your own skill:
npx skills init my-xyz-skill
```

---

## Summary

```
User asks "how do I do X?"
  │
  ├── Is X on the skills.sh leaderboard?
  │     └── Yes → Present top option
  │
  ├── No → Run: npx skills find X
  │     └── Results?
  │           ├── Yes → Verify quality → Present → Install?
  │           └── No  → Offer direct help + suggest custom skill
  │
  └── User requests install
        └── Run: npx skills add <package> -g -y
```
