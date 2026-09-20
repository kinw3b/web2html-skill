# Computed roles → source tokens

Computed tools infer token roles from rendered frequency. Treat those labels as
hints; source CSS variables and authored styles are the source of truth.

| Computed label | Verify against |
|---|---|
| `colors.primary` / `accent` | Source color variables and actual component use |
| `colors.background` | Page and section background declarations |
| heading/body fonts | Font-face rules and authored typography styles |
| spacing/radius/shadows | Inline styles plus CSS rules |

Never store a customer/site name, URL, Paper file ID, or site-generated UUID in
this reference. Project-specific mappings belong in that project's ignored
working directory.
