import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { studentApi } from '../api';
import { useAuth } from '../hooks/useAuth';
import { Card, Button, Input, Label, ErrorMessage } from '../components/ui';

export function LoginPage() {
  const { student, refreshStudent } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const prefillCode = (searchParams.get('code') || '').toUpperCase();

  const [joinCode, setJoinCode] = useState(prefillCode);
  const [displayName, setDisplayName] = useState('');
  const [mode, setMode] = useState<'new' | 'existing' | null>(null);
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [error, setError] = useState('');
  const [className, setClassName] = useState('');

  if (student) {
    navigate('/aufgaben', { replace: true });
  }

  const handleStep1 = async () => {
    setError('');
    try {
      const res = await studentApi.joinStatus(joinCode, displayName);
      setMode(res.mode);
      setClassName(res.class);
      setPassword('');
      setPasswordConfirm('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prüfung fehlgeschlagen');
    }
  };

  const handleLogin = async () => {
    setError('');
    if (mode === 'new' && password !== passwordConfirm) {
      setError('Die Passwörter stimmen nicht überein.');
      return;
    }
    try {
      await studentApi.join(joinCode, displayName, password);
      await refreshStudent();
      navigate('/aufgaben');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Anmeldung fehlgeschlagen');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === null) handleStep1();
    else handleLogin();
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4 dark:bg-gray-950">
      <div className="w-full max-w-md">
        <Card>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Willkommen bei LUKA
          </h1>
          <form onSubmit={handleSubmit}>
            <Label>Klassen-Code</Label>
            <Input
              type="text"
              value={joinCode}
              onChange={(e) => {
                setJoinCode(e.target.value.toUpperCase());
                if (mode !== null) setMode(null);
              }}
              autoComplete="off"
              required
            />

            <Label>Dein Kürzel (Pseudonym)</Label>
            <Input
              type="text"
              value={displayName}
              onChange={(e) => {
                setDisplayName(e.target.value);
                if (mode !== null) setMode(null);
              }}
              autoComplete="off"
              required
              autoFocus={!!prefillCode}
            />

            {mode !== null && (
              <div className="mt-4">
                <p className="mb-2 text-sm text-gray-600 dark:text-gray-400">
                  {mode === 'new'
                    ? `Lege ein Passwort für dein Kürzel fest. (${className})`
                    : `Bitte gib dein Passwort ein. (${className})`}
                </p>
                <Label>{mode === 'new' ? 'Neues Passwort' : 'Passwort'}</Label>
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="off"
                  autoFocus
                />
                {mode === 'new' && (
                  <>
                    <Label>Passwort wiederholen</Label>
                    <Input
                      type="password"
                      value={passwordConfirm}
                      onChange={(e) => setPasswordConfirm(e.target.value)}
                      autoComplete="off"
                    />
                  </>
                )}
              </div>
            )}

            <div className="mt-6">
              <Button type="submit" className="w-full justify-center">
                {mode === null ? 'Weiter' : 'Anmelden'}
              </Button>
            </div>

            {error && <ErrorMessage message={error} />}
          </form>
          <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
            Bitte keinen echten Namen verwenden, wenn deine Lehrkraft ein
            Pseudonym vorgibt. Merke dir dein Passwort – bei Verlust setzt es
            deine Lehrkraft zurück.
          </p>
        </Card>
        <p className="mt-4 text-center text-sm">
          <a href="/datenschutz" className="text-blue-600 hover:underline dark:text-blue-400">
            Datenschutzhinweise
          </a>
        </p>
      </div>
    </div>
  );
}
