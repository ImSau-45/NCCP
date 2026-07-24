# SPRINT_GUIDE.md

# Pipeline.sh Sprint Execution Guide

Version: 1.0

---

# Purpose

This document defines the engineering workflow for every sprint.

Every developer and AI coding agent must follow this guide.

---

# Sprint Lifecycle

Planning

↓

Implementation

↓

Verification

↓

Code Review

↓

Bug Fixes

↓

Merge

↓

Documentation Update

↓

Next Sprint

---

# Before Every Sprint

Read:

- AI_AGENT_RULES.md
- PROJECT_SRS.md
- ARCHITECTURE.md
- DATABASE_SCHEMA.md
- ROADMAP.md
- API.md
- TASKS.md
- implementation.md

Never start implementation without understanding the current sprint.

---

# Sprint Template

Sprint Number

Sprint Goal

Requirements

Acceptance Criteria

Files Expected to Change

Files That Must NOT Change

Definition of Done

---

# Prompt Template

Read:

AI_AGENT_RULES.md

implementation.md

TASKS.md

ARCHITECTURE.md

Sprint:

<Objective>

Requirements

...

Deliverables

...

---

# Development Rules

Implement only the current sprint.

Never implement future sprint features.

Never redesign architecture.

Reuse existing services.

Routes must stay thin.

Business logic belongs in services.

---

# Verification Checklist

Before finishing:

- Project builds
- Imports resolve
- Docker starts
- Database connects
- Redis connects
- Routes registered
- APIs callable
- No placeholder code
- No TODOs
- Logging works
- Error handling works

---

# Review Checklist

Reviewer checks:

- Architecture
- Naming
- Duplication
- Error handling
- Logging
- Performance
- Security
- API consistency
- Database impact

---

# Merge Checklist

Before merge:

- Code reviewed
- Smoke tested
- implementation.md updated
- TASKS.md updated
- CHANGELOG.md updated

---

# Definition of Done

A sprint is DONE only if:

✓ Feature implemented

✓ Verified

✓ Reviewed

✓ Documented

✓ No blockers remain

Otherwise:

Status = In Progress

---

# Bug Fix Sprint

If bugs exist:

No new features.

Fix bugs first.

Verify again.

Only then continue.

---

# Git Workflow

main

↓

development

↓

feature/<name>

↓

Pull Request

↓

Review

↓

Merge

---

# Daily Workflow

Pull latest development

↓

Create feature branch

↓

Implement

↓

Verify

↓

Commit

↓

Push

↓

Review

↓

Merge

↓

Update docs

---

# AI Agent Rules

AI must:

Implement code.

Not write proposals.

Not write pseudo-code.

Not leave placeholders.

Not claim verification without running checks.

Stop if blocked and explain why.

---

# Engineering Philosophy

Working software is more valuable than additional features.

Stability is more valuable than quantity.

Every sprint should improve the project without increasing technical debt.