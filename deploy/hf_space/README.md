---
title: CodeMigrate
emoji: 🔧
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# CodeMigrate

Evidence-grounded detection of breaking API changes when upgrading Django.
Source: https://github.com/Adithyasai3/CodeMigrate

Runs the offline pipeline by default. To use Gemini, add `GEMINI_API_KEY` (and
optionally `LLM_PROVIDER=gemini`) under Space settings → Variables and secrets.
Also set `JWT_SECRET` there. Accounts and scans are stored in SQLite and reset
whenever the Space restarts.
