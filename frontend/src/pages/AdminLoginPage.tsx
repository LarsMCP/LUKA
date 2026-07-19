import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminApi } from '../api';
import { useAuth } from '../hooks/useAuth';
import { Card, Button, Input, ErrorMessage } from '../components/ui';

export function AdminLoginPage() {
  const { refreshTeacher } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await adminApi.login(username, password);
      await refreshTeacher();
      navigate('/admin');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login fehlgeschlagen');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4 dark:bg-gray-950">
      <div className="w-full max-w-md">
        <Card>
          <h1 className="mb-4 text-2xl font-bold text-gray-900 dark:text-gray-100">
            LUKA Admin – Anmeldung
          </h1>
          <form onSubmit={handleSubmit}>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Benutzername
            </label>
            <Input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="off"
              required
            />
            <label className="mt-4 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Passwort
            </label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="off"
              required
            />
            <div className="mt-6">
              <Button type="submit" className="w-full justify-center">
                Anmelden
              </Button>
            </div>
            {error && <ErrorMessage message={error} />}
          </form>
        </Card>
      </div>
    </div>
  );
}
