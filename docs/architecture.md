# ARCHITECTURE.md

# Pipeline.sh Architecture Documentation

Version: 1.0

---

# Purpose

This document describes the architecture of Pipeline.sh.

It is the primary technical reference for developers and AI coding agents.

All implementations must follow this architecture unless explicitly approved.

---

# High-Level Architecture

                    +---------------------+
                    |     React Client    |
                    |  (Tailwind + Vite)  |
                    +----------+----------+
                               |
                               |
                               ▼
                    +----------------------+
                    |      Flask API       |
                    | Authentication Layer |
                    +----------+-----------+
                               |
               +---------------+----------------+
               |               |                |
               ▼               ▼                ▼
        GitHub Service   Workflow Engine   Analytics Service
               |               |                |
               +---------------+----------------+
                               |
                               ▼
                     Business Service Layer
                               |
               +---------------+----------------+
               |               |                |
               ▼               ▼                ▼
          PostgreSQL        Redis          OpenAI (Future)
               |
               ▼
          Docker Environment

---

# Project Structure

```

backend/
routes/
services/
models.py
config.py
db.py

frontend/
pages/
components/
hooks/

scripts/
docker/
nginx/
docs/

```

Purpose

backend

Business logic

frontend

React UI

scripts

Deployment

docs

Engineering documentation

---

# Backend Architecture

Request

↓

Route

↓

Service

↓

Database / GitHub API / Cache

↓

Response

Routes should never contain business logic.

Business logic belongs inside Services.

---

# Service Layer

Every major feature has its own service.

Current services

GitHubService

Repository synchronization

WorkflowEngine

Workflow generation

DeploymentService

Deployment orchestration

AnalyticsService

Dashboard analytics

CacheService

Redis caching

Future services

AIService

NotificationService

AuditService

---

# Frontend Architecture

React

↓

Pages

↓

Components

↓

API Layer

↓

Backend

State Flow

User Action

↓

API Request

↓

Loading

↓

Success / Error

↓

UI Update

---

# Authentication Flow

User

↓

Login

↓

JWT Authentication

↓

Access Token

↓

Protected API

↓

GitHub OAuth

↓

GitHub Access Token

↓

Repository Access

---

# GitHub Integration Flow

GitHub OAuth

↓

Access Token

↓

Repository Sync

↓

Repository Database

↓

Workflow Engine

↓

GitHub Actions

↓

Workflow Execution

---

# Workflow Engine Flow

Repository

↓

Repository Analysis

↓

Tech Stack Detection

↓

Workflow Template

↓

YAML Generation

↓

Validation

↓

Preview

↓

Commit to GitHub

↓

Workflow Execution

---

# Pipeline Execution Flow

GitHub Actions

↓

Workflow Trigger

↓

Execution

↓

Logs

↓

Status

↓

Dashboard

---

# Dashboard Flow

Repository Data

↓

Analytics Service

↓

REST API

↓

React Dashboard

↓

Charts

↓

Live Statistics

---

# Database Architecture

Main Entities

User

GitHubAccount

Repository

Branch

Workflow

GeneratedWorkflow

PipelineExecution

BuildLog

Deployment

Relationships

User

↓

Repositories

↓

Branches

↓

Workflows

↓

Pipeline Executions

↓

Logs

---

# Redis Usage

Repository Cache

Workflow Cache

Analytics Cache

Session Cache

Never store

Passwords

JWT Secrets

GitHub Tokens

OpenAI Keys

AWS Credentials

---

# Error Handling

Every Route

↓

Validation

↓

Service

↓

Exception

↓

Global Handler

↓

JSON Response

Response Format

{
"success": false,
"message": "...",
"data": null
}

---

# Logging

Application Logs

GitHub Logs

Deployment Logs

Workflow Logs

Error Logs

Never log

Passwords

Secrets

Tokens

---

# Docker Architecture

React

↓

Nginx

↓

Flask API

↓

PostgreSQL

↓

Redis

---

# Deployment Architecture

Current

Docker Compose

Future

AWS EC2

↓

Docker

↓

Nginx

↓

Flask

↓

PostgreSQL

↓

Redis

---

# AI Module (Future)

Pipeline Logs

↓

OpenAI

↓

Failure Analysis

↓

Suggested Fixes

↓

Workflow Improvement

---

# Design Principles

Always follow

SOLID

DRY

KISS

REST

Separation of Concerns

Single Responsibility

Thin Controllers

Fat Services

---

# Coding Standards

Routes

Only

Validate Requests

Call Services

Return Responses

Never

Business Logic

Services

Should

Contain Business Logic

Communicate with Database

Communicate with GitHub

Communicate with Cache

Database

Never queried directly from routes.

---

# Module Dependencies

Frontend

↓

API

↓

Routes

↓

Services

↓

Models

↓

Database

Services may communicate with

GitHub API

Redis

OpenAI

AWS

Routes must never communicate with external services directly.

---

# Development Workflow

Feature Branch

↓

Implementation

↓

Verification

↓

Code Review

↓

Merge into Development

↓

Testing

↓

Merge into Main

---

# Definition of Architecture Success

The architecture is considered successful when

✓ Every route is thin.

✓ Every service has a single responsibility.

✓ No duplicated business logic exists.

✓ Frontend never contains business logic.

✓ Database access is centralized.

✓ APIs are reusable.

✓ AI modules can be added without modifying existing services.

✓ Deployment can be replaced without affecting business logic.

---

# Future Scalability

The architecture should support

Multi-user organizations

Multiple GitHub accounts

Multi-cloud deployment

Kubernetes

Plugin architecture

AI-powered recommendations

Enterprise authentication

without major architectural changes.

---

# Architecture Rules for AI Agents

Every AI coding agent MUST

Read

AI_AGENT_RULES.md

PROJECT_SRS.md

ROADMAP.md

API.md

TASKS.md

ARCHITECTURE.md

implementation.md

before modifying the project.

Never violate the architecture.

If a requested feature requires changing the architecture,

stop

and explain why before making changes.

---

# Golden Rule

The architecture is more important than the implementation.

Features can evolve.

Architecture should remain stable.