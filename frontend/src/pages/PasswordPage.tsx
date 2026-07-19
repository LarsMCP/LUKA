import { useState } from 'react';
import { studentApi } from '../api';
import { StudentAppBar, Card, Button, Input, Label, ErrorMessage } from '../components/ui';

export function PasswordPage() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);
    if (newPassword !== confirmPassword) {
      setError('Die neuen Passwörter stimmen nicht überein.');
      return;
    }
    try {
      await studentApi.changePassword(currentPassword, newPassword);
      setSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Ändern');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <StudentAppBar />
      <main className="mx-auto max-w-md p-6">
        <Card>
          <h1 className="mb-4 text-xl font-bold text-gray-900 dark:text-gray-100">
            Passwort ändern
          </h1>
          {success && (
            <div className="mb-4 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-900/20 dark:text-green-400">
              Passwort erfolgreich geändert.
            </div>
          )}
          <form onSubmit={handleSubmit}>
            <Label>Aktuelles Passwort</Label>
            <Input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="off"
              required
            />
            <Label>Neues Passwort</Label>
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="off"
              required
            />
            <Label>Neues Passwort wiederholen</Label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="off"
              required
            />
            <div className="mt-6">
              <Button type="submit" className="w-full justify-center">
                Passwort ändern
              </Button>
            </div>
            {error && <ErrorMessage message={error} />}
          </form>
        </Card>
      </main>
    </div>
  );
}
