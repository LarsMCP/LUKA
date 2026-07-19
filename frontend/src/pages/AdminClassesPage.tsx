import { useEffect, useState } from 'react';
import { adminApi } from '../api';
import { AdminAppBar, Card, Button, Input } from '../components/ui';
import type { Class } from '../types';
import { QrCode, Plus, Trash2, Power } from 'lucide-react';

export function AdminClassesPage() {
  const [classes, setClasses] = useState<Class[]>([]);
  const [newName, setNewName] = useState('');
  const [qrSvg, setQrSvg] = useState<string | null>(null);
  const [qrClass, setQrClass] = useState<Class | null>(null);

  const refresh = () => {
    adminApi.listClasses().then(setClasses);
  };

  useEffect(() => { refresh(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    await adminApi.createClass(newName.trim());
    setNewName('');
    refresh();
  };

  const handleToggle = async (id: number) => {
    await adminApi.toggleClass(id);
    refresh();
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Klasse wirklich löschen? Alle Schüler und Abgaben werden gelöscht.')) return;
    await adminApi.deleteClass(id);
    refresh();
  };

  const showQr = async (klass: Class) => {
    const svg = await adminApi.getQrSvg(klass.id);
    setQrSvg(svg);
    setQrClass(klass);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <AdminAppBar />
      <main className="mx-auto max-w-4xl p-6">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-gray-100">Klassen</h1>

        <Card className="mb-6">
          <form onSubmit={handleCreate} className="flex gap-3">
            <Input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Neuer Klassenname"
            />
            <Button type="submit"><Plus size={18} /> Erstellen</Button>
          </form>
        </Card>

        <div className="grid gap-4">
          {classes.map((klass) => (
            <Card key={klass.id}>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-semibold text-gray-900 dark:text-gray-100">
                    {klass.name}
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Code: <span className="font-mono font-bold">{klass.join_code}</span>
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outlined" size="sm" onClick={() => showQr(klass)}>
                    <QrCode size={16} /> QR
                  </Button>
                  <Button variant="outlined" size="sm" onClick={() => handleToggle(klass.id)}>
                    <Power size={16} /> {klass.active ? 'Deaktivieren' : 'Aktivieren'}
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => handleDelete(klass.id)}>
                    <Trash2 size={16} />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
          {classes.length === 0 && (
            <p className="text-gray-500">Noch keine Klassen erstellt.</p>
          )}
        </div>

        {qrSvg && qrClass && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setQrSvg(null)}>
            <Card className="max-w-sm text-center" >
              <div onClick={(e) => e.stopPropagation()}>
                <h2 className="mb-4 text-xl font-bold">{qrClass.name}</h2>
                <div dangerouslySetInnerHTML={{ __html: qrSvg }} className="mx-auto mb-4" />
                <p className="text-sm text-gray-500">Code: {qrClass.join_code}</p>
                <Button variant="outlined" size="sm" className="mt-4" onClick={() => window.print()}>
                  Drucken
                </Button>
              </div>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}
