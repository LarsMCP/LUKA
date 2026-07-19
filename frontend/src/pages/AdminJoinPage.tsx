import { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Card, Button, Input, ErrorMessage } from '../components/ui';

export function AdminJoinPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const prefillCode = searchParams.get('code') || '';
  const [code, setCode] = useState(prefillCode);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirm) {
      setError('Die Passwörter stimmen nicht überein.');
      return;
    }
    if (password.length < 8) {
      setError('Passwort muss mindestens 8 Zeichen haben.');
      return;
    }
    try {
      const fd = new FormData();
      fd.append('code', code);
      fd.append('username', username);
      fd.append('password', password);
      fd.append('password_confirm', confirm);
      const res = await fetch('/api/admin/join', {
        method: 'POST',
        body: fd,
        credentials: 'same-origin',
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Registrierung fehlgeschlagen');
      }
      navigate('/admin');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4 dark:bg-gray-950">
      <div className="w-full max-w-md">
        <Card>
          <h1 className="mb-4 text-2xl font-bold text-gray-900 dark:text-gray-100">
            Lehrer-Registrierung
          </h1>
          <form onSubmit={handleSubmit}>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Einladungscode</label>
            <Input type="text" value={code} onChange={(e) => setCode(e.target.value)} required />
            <label className="mt-4 block text-sm font-medium text-gray-700 dark:text-gray-300">Benutzername</label>
            <Input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required />
            <label className="mt-4 block text-sm font-medium text-gray-700 dark:text-gray-300">Passwort</label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            <label className="mt-4 block text-sm font-medium text-gray-700 dark:text-gray-300">Passwort wiederholen</label>
            <Input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
            <div className="mt-6">
              <Button type="submit" className="w-full justify-center">Registrieren</Button>
            </div>
            {error && <ErrorMessage message={error} />}
          </form>
        </Card>
      </div>
    </div>
  );
}
