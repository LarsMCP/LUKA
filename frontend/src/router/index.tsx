import { createBrowserRouter, Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { lazy, Suspense, type ReactNode } from 'react';

const LoginPage = lazy(() => import('../pages/LoginPage').then(m => ({ default: m.LoginPage })));
const TasksPage = lazy(() => import('../pages/TasksPage').then(m => ({ default: m.TasksPage })));
const TaskViewPage = lazy(() => import('../pages/TaskViewPage').then(m => ({ default: m.TaskViewPage })));
const PasswordPage = lazy(() => import('../pages/PasswordPage').then(m => ({ default: m.PasswordPage })));
const DatenschutzPage = lazy(() => import('../pages/DatenschutzPage').then(m => ({ default: m.DatenschutzPage })));
const AdminLoginPage = lazy(() => import('../pages/AdminLoginPage').then(m => ({ default: m.AdminLoginPage })));
const AdminDashboardPage = lazy(() => import('../pages/AdminDashboardPage').then(m => ({ default: m.AdminDashboardPage })));
const AdminClassesPage = lazy(() => import('../pages/AdminClassesPage').then(m => ({ default: m.AdminClassesPage })));
const AdminStudentsPage = lazy(() => import('../pages/AdminStudentsPage').then(m => ({ default: m.AdminStudentsPage })));
const AdminTasksPage = lazy(() => import('../pages/AdminTasksPage').then(m => ({ default: m.AdminTasksPage })));
const AdminSubmissionsPage = lazy(() => import('../pages/AdminSubmissionsPage').then(m => ({ default: m.AdminSubmissionsPage })));
const AdminSubmissionViewPage = lazy(() => import('../pages/AdminSubmissionViewPage').then(m => ({ default: m.AdminSubmissionViewPage })));
const AdminStatsPage = lazy(() => import('../pages/AdminStatsPage').then(m => ({ default: m.AdminStatsPage })));
const AdminTeachersPage = lazy(() => import('../pages/AdminTeachersPage').then(m => ({ default: m.AdminTeachersPage })));
const AdminJoinPage = lazy(() => import('../pages/AdminJoinPage').then(m => ({ default: m.AdminJoinPage })));

function PageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
    </div>
  );
}

function ProtectedRoute({
  children,
  requireStudent,
  requireTeacher,
}: {
  children: ReactNode;
  requireStudent?: boolean;
  requireTeacher?: boolean;
}) {
  const { student, teacher, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (requireStudent && !student) return <Navigate to="/" replace />;
  if (requireTeacher && !teacher) return <Navigate to="/admin/login" replace />;
  return <>{children}</>;
}

function withSuspense(element: ReactNode) {
  return <Suspense fallback={<PageLoader />}>{element}</Suspense>;
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: withSuspense(<LoginPage />),
  },
  {
    path: '/datenschutz',
    element: withSuspense(<DatenschutzPage />),
  },
  {
    path: '/aufgaben',
    element: withSuspense(
      <ProtectedRoute requireStudent>
        <TasksPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/task/:slug',
    element: withSuspense(
      <ProtectedRoute requireStudent>
        <TaskViewPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/passwort',
    element: withSuspense(
      <ProtectedRoute requireStudent>
        <PasswordPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/admin/login',
    element: withSuspense(<AdminLoginPage />),
  },
  {
    path: '/admin/join',
    element: withSuspense(<AdminJoinPage />),
  },
  {
    path: '/admin',
    element: withSuspense(
      <ProtectedRoute requireTeacher>
        <AdminDashboardPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/admin/classes',
    element: withSuspense(
      <ProtectedRoute requireTeacher>
        <AdminClassesPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/admin/students',
    element: withSuspense(
      <ProtectedRoute requireTeacher>
        <AdminStudentsPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/admin/tasks',
    element: withSuspense(
      <ProtectedRoute requireTeacher>
        <AdminTasksPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/admin/submissions',
    element: withSuspense(
      <ProtectedRoute requireTeacher>
        <AdminSubmissionsPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/admin/submissions/view',
    element: withSuspense(
      <ProtectedRoute requireTeacher>
        <AdminSubmissionViewPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/admin/stats',
    element: withSuspense(
      <ProtectedRoute requireTeacher>
        <AdminStatsPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/admin/teachers',
    element: withSuspense(
      <ProtectedRoute requireTeacher>
        <AdminTeachersPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
], {
  basename: '/app',
});
