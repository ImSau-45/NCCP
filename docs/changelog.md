# Changelog

All notable changes to Pipeline.sh will be documented here.

---

## [Unreleased]

### Added

- Workflow Engine
- Repository Synchronization
- YAML Generation
- Git Branch creation and Pull Request helpers in `GitHubService`
- Endpoint `POST /api/projects/:id/publish` for direct commits and PR creation
- Frontend page `PrConfirmPage` to choose direct commit or PR workflow publishing
- Dynamic metrics binding in `Analytics.jsx`

### Changed

- Refactored workflow routes
- Improved service layer
- Centralized GitHub logic
- Refactored `AIService` to support OpenAI v1 SDK and OpenRouter configuration

### Fixed

- Blueprint registration
- Import issues
- Duplicate workflow generation
- Invalid SQL join query in `/api/pipelines/history`
- Corrected database migrations and setup initialization steps
- Registered all new views and route paths correctly in `App.jsx` and `Sidebar.jsx`
- Fixed `ModuleNotFoundError: No module named 'backend'` inside Docker container by adding `PYTHONPATH=/app` to Dockerfile.
- Added `numpy>=1.24.0` to `backend/requirements.txt` to resolve startup crash `ModuleNotFoundError: No module named 'numpy'` in container.
- Added `COPY migrations/ ./migrations/` to `Dockerfile` to ensure migration scripts are present inside the container.
- Configured Vite dev server proxy target to dynamically use `VITE_PROXY_TARGET` environment variable (resolving `500 Internal Server Error` proxy failures inside Docker network).
- Fixed Flask `RuntimeError: Working outside of application context` error in background scheduler tasks by wrapping inside `app_context`.
- Resolved GitHub OAuth redirect URI host resolution issue by introducing configurable `BACKEND_URL` for `redirect_uri` generation (preventing mismatches with registered GitHub application settings).
- Fixed a `422 Unprocessable Entity` error during GitHub publishing where `author.name` would evaluate to `None` for users without public names set on GitHub (added display name fallbacks and error logging).
- Added `workflow` to the requested GitHub OAuth scope list in `auth.py` (solving `404 Not Found` errors when attempting to commit files inside `.github/workflows/` directory).

---

## [v0.2.0]

### Added

- GitHub OAuth
- JWT Authentication
- Repository Dashboard

---

## [v0.1.0]

Initial Project

- Flask Backend
- React Frontend
- PostgreSQL
- Redis
- Docker