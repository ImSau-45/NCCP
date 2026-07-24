# Graph Report - Natural_cicd  (2026-05-21)

## Corpus Check
- 45 files · ~4,864 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 152 nodes · 176 edges · 21 communities (17 shown, 4 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 16 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 20|Community 20]]

## God Nodes (most connected - your core abstractions)
1. `Pipeline.sh` - 7 edges
2. `GitHubService` - 6 edges
3. `DeploymentService` - 6 edges
4. `CacheService` - 6 edges
5. `TFPredictor` - 6 edges
6. `Dashboard()` - 5 edges
7. `AIService` - 5 edges
8. `scripts` - 4 edges
9. `dashboard_metrics()` - 4 edges
10. `connect_repository()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `connect_repository()` --calls--> `Repository`  [INFERRED]
  backend/routes/github.py → backend/models.py
- `analyze_pipeline()` --calls--> `AIService`  [INFERRED]
  backend/routes/pipeline.py → backend/services/ai_service.py
- `create_app()` --calls--> `configure_scheduler()`  [INFERRED]
  backend/app.py → backend/tasks.py
- `CacheService` --uses--> `Config`  [INFERRED]
  backend/services/cache_service.py → backend/config.py
- `register()` --calls--> `User`  [INFERRED]
  backend/routes/auth.py → backend/models.py

## Communities (21 total, 4 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.10
Nodes (3): links, LandingPage(), WorkflowBuilder()

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (20): dependencies, axios, react, react-dom, react-router-dom, recharts, devDependencies, autoprefixer (+12 more)

### Community 2 - "Community 2"
Cohesion: 0.18
Nodes (4): Pipeline, analyze_pipeline(), trigger_pipeline(), AIService

### Community 3 - "Community 3"
Cohesion: 0.31
Nodes (4): connect_repository(), generate_workflow(), list_repositories(), GitHubService

### Community 4 - "Community 4"
Cohesion: 0.14
Nodes (11): AIPrediction, Analytics, CloudDeployment, Deployment, DeploymentServer, ErrorReport, Notification, Repository (+3 more)

### Community 5 - "Community 5"
Cohesion: 0.31
Nodes (4): useAuth(), LoginPage(), api, setAuthToken()

### Community 8 - "Community 8"
Cohesion: 0.33
Nodes (3): User, github_callback(), register()

### Community 10 - "Community 10"
Cohesion: 0.29
Nodes (4): ChartCard(), PipelineCard(), Dashboard(), ReposPage()

### Community 20 - "Community 20"
Cohesion: 0.20
Nodes (9): code:bash (docker compose up --build), code:bash (docker compose exec backend flask db upgrade), Deployment, Development, Features, Notes, Pipeline.sh, Project Structure (+1 more)

## Knowledge Gaps
- **35 isolated node(s):** `name`, `version`, `private`, `type`, `dev` (+30 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Analytics` connect `Community 4` to `Community 6`?**
  _High betweenness centrality (0.210) - this node is a cross-community bridge._
- **Why does `Repository` connect `Community 4` to `Community 3`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `connect_repository()` connect `Community 3` to `Community 4`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `GitHubService` (e.g. with `list_repositories()` and `connect_repository()`) actually correct?**
  _`GitHubService` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `version`, `private` to the rest of the system?**
  _35 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.09956709956709957 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._