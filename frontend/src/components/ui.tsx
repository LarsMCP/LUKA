import { type ReactNode } from 'react';
import { Sun, Moon, LogOut } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';
import { useAuth } from '../hooks/useAuth';
import { Link } from 'react-router-dom';
import { adminApi, studentApi } from '../api';

interface AppBarProps {
  title: string;
  nav?: ReactNode;
}

export function AppBar({ title, nav }: AppBarProps) {
  const { theme, toggle } = useTheme();

  return (
    <header className="sticky top-0 z-50 flex items-center gap-4 border-b border-gray-200 bg-white/95 px-4 py-3 backdrop-blur dark:border-gray-700 dark:bg-gray-900/95">
      <span className="text-lg font-bold text-gray-900 dark:text-gray-100">
        {title}
      </span>
      <nav className="flex flex-1 items-center gap-1 overflow-x-auto">
        {nav}
      </nav>
      <button
        onClick={toggle}
        className="rounded-lg p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
        aria-label="Farbschema wechseln"
      >
        {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
      </button>
    </header>
  );
}

export function AdminAppBar() {
  const { teacher, clearTeacher } = useAuth();
  const nav = teacher ? (
    <>
      <NavLink to="/admin">Start</NavLink>
      <NavLink to="/admin/classes">Klassen</NavLink>
      <NavLink to="/admin/students">Schüler</NavLink>
      <NavLink to="/admin/tasks">Aufgaben</NavLink>
      <NavLink to="/admin/submissions">Ergebnisse</NavLink>
      <NavLink to="/admin/stats">Statistik</NavLink>
      {teacher.role === 'admin' && <NavLink to="/admin/teachers">Lehrer</NavLink>}
      <button
        onClick={async () => {
          await adminApi.logout();
          clearTeacher();
        }}
        className="ml-2 flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
      >
        <LogOut size={16} /> abmelden
      </button>
    </>
  ) : null;

  return <AppBar title="LUKA Admin" nav={nav} />;
}

export function StudentAppBar() {
  const { student, clearStudent } = useAuth();
  const nav = student ? (
    <>
      <NavLink to="/aufgaben">Aufgaben</NavLink>
      <NavLink to="/passwort">Passwort</NavLink>
      <button
        onClick={async () => {
          await studentApi.logout();
          clearStudent();
        }}
        className="ml-2 flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
      >
        <LogOut size={16} /> abmelden
      </button>
    </>
  ) : null;

  return <AppBar title="LUKA" nav={nav} />;
}

function NavLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link
      to={to}
      className="whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
    >
      {children}
    </Link>
  );
}

export function Card({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900 ${className}`}
    >
      {children}
    </div>
  );
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  ...props
}: {
  children: ReactNode;
  variant?: 'primary' | 'outlined' | 'danger';
  size?: 'sm' | 'md';
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const base =
    'inline-flex items-center gap-2 rounded-full font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-5 py-2.5 text-base',
  };
  const variants = {
    primary:
      'bg-blue-600 text-white hover:bg-blue-700 shadow-sm',
    outlined:
      'border border-gray-300 text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800',
    danger:
      'bg-red-600 text-white hover:bg-red-700 shadow-sm',
  };

  return (
    <button
      className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
      {...props}
    />
  );
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
      {...props}
    />
  );
}

export function Label({ children }: { children: ReactNode }) {
  return (
    <label className="mt-4 block text-sm font-medium text-gray-700 dark:text-gray-300">
      {children}
    </label>
  );
}

export function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
      {message}
    </div>
  );
}
