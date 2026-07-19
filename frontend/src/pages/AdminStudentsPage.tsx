import { useEffect, useState } from 'react';
import { adminApi } from '../api';
import { AdminAppBar, Card, Button, Select } from '../components/ui';
import type { Class, StudentListItem } from '../types';
import { KeyRound, Trash2, Edit3 } from 'lucide-react';

export function AdminStudentsPage() {
  const [classes, setClasses] = useState<Class[]>([]);
  const [selClass, setSelClass] = useState<number | null>(null);
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');

  useEffect(() => {
    adminApi.listClasses().then((cs) => {
      setClasses(cs);
      if (cs.length > 0 && selClass === null) setSelClass(cs[0].id);
    });
  }, []);

  useEffect(() => {
    if (selClass !== null) {
      adminApi.listStudents(selClass).then(setStudents);
    }
  }, [selClass]);

  const handleRename = async (id: number) => {
    if (!editName.trim()) return;
    await adminApi.renameStudent(id, editName.trim());
    setEditingId(null);
    if (selClass !== null) adminApi.listStudents(selClass).then(setStudents);
  };

  const handleReset = async (id: number) => {
    if (!confirm('Passwort wirklich zurücksetzen?')) return;
    await adminApi.resetStudentPassword(id);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Schüler wirklich löschen? Alle Abgaben werden gelöscht.')) return;
    await adminApi.deleteStudent(id);
    if (selClass !== null) adminApi.listStudents(selClass).then(setStudents);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <AdminAppBar />
      <main className="mx-auto max-w-4xl p-6">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-gray-100">Schüler</h1>

        <Card className="mb-6">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Klasse</label>
          <Select value={selClass ?? ''} onChange={(e) => setSelClass(Number(e.target.value))}>
            <option value="">– wählen –</option>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </Select>
        </Card>

        <div className="grid gap-3">
          {students.map((s) => (
            <Card key={s.id} className="flex items-center justify-between py-4">
              <div className="flex-1">
                {editingId === s.id ? (
                  <input
                    className="rounded-lg border border-gray-300 px-3 py-1 dark:border-gray-600 dark:bg-gray-800"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleRename(s.id)}
                    autoFocus
                  />
                ) : (
                  <>
                    <span className="font-medium text-gray-900 dark:text-gray-100">{s.display_name}</span>
                    <span className="ml-3 text-sm text-gray-500">{s.submissions} Abgaben</span>
                    {s.has_password && (
                      <span className="ml-2 rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400">
                        Passwort gesetzt
                      </span>
                    )}
                  </>
                )}
              </div>
              <div className="flex gap-2">
                {editingId === s.id ? (
                  <Button size="sm" onClick={() => handleRename(s.id)}>Speichern</Button>
                ) : (
                  <Button variant="outlined" size="sm" onClick={() => { setEditingId(s.id); setEditName(s.display_name); }}>
                    <Edit3 size={16} />
                  </Button>
                )}
                <Button variant="outlined" size="sm" onClick={() => handleReset(s.id)}>
                  <KeyRound size={16} />
                </Button>
                <Button variant="danger" size="sm" onClick={() => handleDelete(s.id)}>
                  <Trash2 size={16} />
                </Button>
              </div>
            </Card>
          ))}
          {students.length === 0 && selClass !== null && (
            <p className="text-gray-500">Keine Schüler in dieser Klasse.</p>
          )}
        </div>
      </main>
    </div>
  );
}
