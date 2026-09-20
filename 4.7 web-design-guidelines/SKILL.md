---
name: web-design-guidelines
description: Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices". In website-to-html this is 3.2 (after Emil, before 3.4).
metadata:
  author: vercel
  version: "1.0.0"
  argument-hint: <file-or-pattern>
---

# Web Interface Guidelines

Review files for compliance with Web Interface Guidelines.

## FIDELITY LOCK — when called from `website-to-html` 3.2

If the parent is **website-to-html** polish (or the target is a Paper-exported rebuild):

1. Target is the QA polish file only: `rebuild/index-polish.html` plus its `css/` and `js/`. Never write the 2.4 lock `rebuild/index.html` (Pitfall #203). Write the receipt to `qa/web-design-guidelines.md`.
2. Fetch fresh guidelines from the source URL below **before** the review.
3. **Audit first.** Apply only fixes that do not swap fonts, change font-size, invent motion, rename Design Library classes, or add chrome Paper never painted. **Do not** restore Paper text-align, gaps, or icons — that is 2.3 only (Pitfall #196 / `polish-visual-restore.md`).
4. **Do not invent skip-links**, skip-to-content, back-to-top, dark-mode toggles, or i18n chrome (Pitfall #81). `:focus-visible` on existing controls is fine. A painted hamburger opening the same desktop links stacked is **not** new chrome — `author-nav-drawer.py` already authors it; do not skip that row for Capture Tool (Pitfall #208).
5. Many remote rules are **n-a** on a static homepage rebuild (virtualization, locale, theme-color, deep-linking). Mark them `n-a` with why. Do not implement them to “pass” the list.
6. A pass is not done because the skill was mentioned. Receipt lists every finding: `applied` / `skipped` / `n-a`. `render-polish-report.py` shows that file on its own card and `verify-polish-passes.py` fails without it (Pitfall #215).

## How It Works

1. Fetch the latest guidelines from the source URL below
2. Read the specified files (or `rebuild/index-polish.html` when run as 3.2)
3. Check against all rules in the fetched guidelines
4. Output findings in the terse `file:line` format, then the receipt

## Guidelines Source

Fetch fresh guidelines before each review:

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

Use WebFetch to retrieve the latest rules. The fetched content contains all the rules and output format instructions.

## Usage

When a user provides a file or pattern argument:
1. Fetch guidelines from the source URL above
2. Read the specified files
3. Apply all rules from the fetched guidelines (fidelity lock if this is a Paper rebuild)
4. Output findings using the format specified in the guidelines

If no files specified and this is not 3.2, ask which files to review.
