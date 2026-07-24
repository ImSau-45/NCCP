const WorkflowBuilder = () => {
  return (
    <div className="space-y-6">
      <div className="glow-card p-6">
        <h1 className="text-2xl font-semibold">Workflow Builder</h1>
        <p className="mt-2 text-slate-400">Create and customize GitHub Actions workflows with AI recommendations.</p>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="glow-card p-6">
          <h2 className="text-xl font-semibold">Auto-generated workflow</h2>
          <pre className="mt-4 rounded-3xl bg-slate-950 p-4 text-sm text-slate-200">{`name: pipeline-sh-ci
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest`}</pre>
        </div>
        <div className="glow-card p-6">
          <h2 className="text-xl font-semibold">Workflow recommendations</h2>
          <ul className="mt-4 space-y-3 text-slate-300">
            <li>Enable cache for dependencies</li>
            <li>Deploy only on protected branches</li>
            <li>Run linting and tests in parallel</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default WorkflowBuilder
