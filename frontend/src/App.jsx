import { Navigate, Route, Routes, useLocation } from "react-router-dom"
import { useAuth } from "./hooks/AuthContext"
import Header from "./components/Header"
import Sidebar from "./components/Sidebar"
import LoginPage from "./pages/LoginPage"
import RegisterPage from "./pages/RegisterPage"
import Dashboard from "./pages/Dashboard"
import NewProject from "./pages/NewProject"
import ProjectsPage from "./pages/ProjectsPage"
import ProjectDetail from "./pages/ProjectDetail"
import ReviewPage from "./pages/ReviewPage"
import WorkflowPage from "./pages/WorkflowPage"
import Settings from "./pages/Settings"
import GitHubSuccess from "./pages/GitHubSuccess"
import PrConfirmPage from "./pages/PrConfirmPage"
import Analytics from "./pages/Analytics"
import LogsViewer from "./pages/LogsViewer"
import AutoFixHistory from "./pages/AutoFixHistory"

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}

function AppShell({ children }) {
  return (
    <div className="flex h-screen overflow-hidden bg-bg text-white">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}

const App = () => {
  const { user } = useAuth()

  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={user ? <Navigate to="/dashboard" replace /> : <LoginPage />}
      />
      <Route
        path="/register"
        element={user ? <Navigate to="/dashboard" replace /> : <RegisterPage />}
      />
      <Route path="/auth/github/success" element={<GitHubSuccess />} />

      {/* Protected routes inside app shell */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <AppShell><Dashboard /></AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/new"
        element={
          <ProtectedRoute>
            <AppShell><NewProject /></AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects"
        element={
          <ProtectedRoute>
            <AppShell><ProjectsPage /></AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:id"
        element={
          <ProtectedRoute>
            <AppShell><ProjectDetail /></AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:id/review"
        element={
          <ProtectedRoute>
            <AppShell><ReviewPage /></AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:id/workflow"
        element={
          <ProtectedRoute>
            <AppShell><WorkflowPage /></AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:id/pr"
        element={
          <ProtectedRoute>
            <AppShell><PrConfirmPage /></AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/analytics"
        element={
          <ProtectedRoute>
            <AppShell><Analytics /></AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/pipelines/:pipelineId/logs"
        element={
          <ProtectedRoute>
            <AppShell><LogsViewer /></AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <AppShell><Settings /></AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="/projects/:id/autofix"
        element={
          <ProtectedRoute>
            <AppShell><AutoFixHistory /></AppShell>
          </ProtectedRoute>
        }
      />
      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default App
