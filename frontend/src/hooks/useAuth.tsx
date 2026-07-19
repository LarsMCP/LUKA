import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from 'react';
import { studentApi, adminApi } from '../api';
import type { Student, Teacher } from '../types';

interface AuthState {
  student: Student | null;
  teacher: Teacher | null;
  loading: boolean;
}

interface AuthContextValue extends AuthState {
  refreshStudent: () => Promise<void>;
  refreshTeacher: () => Promise<void>;
  clearStudent: () => void;
  clearTeacher: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    student: null,
    teacher: null,
    loading: true,
  });

  useEffect(() => {
    Promise.all([
      studentApi.me().catch(() => null),
      adminApi.me().catch(() => null),
    ]).then(([student, teacher]) => {
      setState({ student, teacher, loading: false });
    });
  }, []);

  const refreshStudent = async () => {
    try {
      const student = await studentApi.me();
      setState((s) => ({ ...s, student }));
    } catch {
      setState((s) => ({ ...s, student: null }));
    }
  };

  const refreshTeacher = async () => {
    try {
      const teacher = await adminApi.me();
      setState((s) => ({ ...s, teacher }));
    } catch {
      setState((s) => ({ ...s, teacher: null }));
    }
  };

  const clearStudent = () => setState((s) => ({ ...s, student: null }));
  const clearTeacher = () => setState((s) => ({ ...s, teacher: null }));

  return (
    <AuthContext.Provider
      value={{ ...state, refreshStudent, refreshTeacher, clearStudent, clearTeacher }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
