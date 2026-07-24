# Pipeline.sh REST API

Base URL

```
/api
```

---

# Authentication

## POST

```
/auth/register
```

Register user

---

## POST

```
/auth/login
```

Login user

---

## POST

```
/auth/refresh
```

Refresh JWT

---

## POST

```
/auth/logout
```

Logout

---

# GitHub

## GET

```
/github/repos
```

List repositories

---

## POST

```
/github/repos/sync
```

Synchronize repositories

---

## GET

```
/github/repos/{id}
```

Repository details

---

## GET

```
/github/repos/{id}/branches
```

Repository branches

---

# Workflow

## POST

```
/workflow/analyze
```

Analyze repository

---

## POST

```
/workflow/generate
```

Generate workflow

---

## POST

```
/workflow/preview
```

Preview workflow

---

## POST

```
/workflow/commit
```

Commit workflow

---

# Pipeline

## GET

```
/pipeline/history
```

Execution history

---

## POST

```
/pipeline/trigger
```

Trigger pipeline

---

## POST

```
/pipeline/cancel
```

Cancel execution

---

## POST

```
/pipeline/rerun
```

Rerun pipeline

---

## GET

```
/pipeline/logs/{id}
```

Pipeline logs

---

# Analytics

## GET

```
/analytics/dashboard
```

Dashboard statistics

---

## GET

```
/analytics/repositories
```

Repository statistics

---

## GET

```
/analytics/pipelines
```

Pipeline analytics

---

# Standard Response

```json
{
  "success": true,
  "message": "Operation completed successfully.",
  "data": {}
}
```

---

# Error Response

```json
{
  "success": false,
  "message": "Description of error.",
  "data": null
}
```

---

# HTTP Status Codes

200 OK

201 Created

400 Bad Request

401 Unauthorized

403 Forbidden

404 Not Found

409 Conflict

422 Validation Error

429 Rate Limited

500 Internal Server Error