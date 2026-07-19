import { useEffect, useState } from 'react';
import { adminApi } from '../api';
import { useAuth } from '../hooks/useAuth';
import { AdminAppBar, Card, Button } from '../components/ui';
import type { Teacher, TeacherInvite } from '../types';
import { UserPlus, Trash2, X } from 'lucide-react';

export function AdminTeachersPage() {
  const { teacher } = useAuth();
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [invites, setInvites] = useState<TeacherInvite[]>([]);

  const refresh = () => {
    adminApi.listTeachers().then((data) => {
      setTeachers(data.teachers);
      setInvites(data.invites);
    });
  };

  useEffect(() => { refresh(); }, []);

  const handleInvite = async (role: string) => {
    await adminApi.createInvite(role);
    refresh();
  };

  const handleRevoke = async (id: number) => {
    await adminApi.revokeInvite(id);
    refresh();
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Lehrer wirklich löschen?')) return;
    await adminApi.deleteTeacher(id);
    refresh();
  };

  if (teacher?.role !== 'admin') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
        <AdminAppBar />
        <main className="mx-auto max-w-4xl p-6">
          <p className="text-gray-500">Nur für Admins verfügbar.</p>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <AdminAppBar />
      <main className="mx-auto max-w-4xl p-6">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-gray-100">Lehrer</h1>

        <Card className="mb-6">
          <h2 className="mb-3 text-lg font-semibold">Einladung erstellen</h2>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => handleInvite('teacher')}>
              <UserPlus size={16} /> Lehrer einladen
            </Button>
            <Button size="sm" variant="outlined" onClick={() => handleInvite('admin')}>
              <UserPlus size={16} /> Admin einladen
            </Button>
          </div>
        </Card>

        {invites.length > 0 && (
          <Card className="mb-6">
            <h2 className="mb-3 text-lg font-semibold">Offene Einladungen</h2>
            <div className="grid gap-2">
              {invites.map((inv) => (
                <div key={inv.id} className="flex items-center justify-between border-b border-gray-100 py-2 dark:border-gray-800">
                  <div>
                    <span className="font-mono font-bold text-gray-900 dark:text-gray-100">{inv.code}</span>
                    <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                      {inv.role}
                    </span>
                    <span className="ml-2 text-sm text-gray-500">
                      gültig bis {new Date(inv.expires_at).toLocaleDateString('de-DE')}
                    </span>
                  </div>
                  <Button variant="outlined" size="sm" onClick={() => handleRevoke(inv.id)}>
                    <X size={14} /> Widerrufen
                  </Button>
                </div>
              ))}
            </div>
          </Card>
        )}

        <div className="grid gap-3">
          {teachers.map((t) => (
            <Card key={t.id} className="flex items-center justify-between py-4">
              <div>
                <span className="font-semibold text-gray-900 dark:text-gray-100">{t.username}</span>
                {t.role === 'admin' && (
                  <span className="ml-2 rounded-full bg-purple-100 px-2 py-0.5 text-xs text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                    Admin
                  </span>
                )}
                <span className="ml-3 text-sm text-gray-500">
                  seit {new Date(t.created_at).toLocaleDateString('de-DE')}
                </span>
              </div>
              {t.id !== teacher.id && (
                <Button variant="danger" size="sm" onClick={() => handleDelete(t.id)}>
                  <Trash2 size={16} />
                </Button>
              )}
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
}
