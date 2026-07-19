import { useEffect, useState } from 'react';
import { adminApi } from '../api';
import { AdminAppBar, Card, Button, Input } from '../components/ui';
import type { Task, TaskRepoConfig } from '../types';
import { RefreshCw, Link2, Unlink } from 'lucide-react';

export function AdminTasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [repoConfig, setRepoConfig] = useState<TaskRepoConfig | null>(null);
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [interval, setInterval] = useState(15);

  const refresh = () => {
    adminApi.listTasks().then(setTasks);
    adminApi.getTaskRepoConfig().then((c) => {
      setRepoConfig(c);
      if (c) {
        setRepoUrl(c.repo_url);
        setBranch(c.branch);
        setInterval(c.sync_interval_minutes);
      }
    });
  };

  useEffect(() => { refresh(); }, []);

  const handleRescan = async () => {
    await adminApi.rescanTasks();
    refresh();
  };

  const handleSaveRepo = async (e: React.FormEvent) => {
    e.preventDefault();
    await adminApi.saveTaskRepo(repoUrl, branch, interval);
    refresh();
  };

  const handleSync = async () => {
    await adminApi.syncTaskRepo();
    refresh();
  };

  const handleDisconnect = async () => {
    if (!confirm('Repo-Verbindung trennen?')) return;
    await adminApi.disconnectTaskRepo();
    refresh();
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <AdminAppBar />
      <main className="mx-auto max-w-4xl p-6">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Aufgaben</h1>
          <Button variant="outlined" onClick={handleRescan}>
            <RefreshCw size={18} /> Neu scannen
          </Button>
        </div>

        <Card className="mb-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
            Externes Aufgaben-Repo
          </h2>
          {repoConfig && repoConfig.repo_url && (
            <div className="mb-4 rounded-lg bg-blue-50 p-3 text-sm dark:bg-blue-900/20">
              <p><strong>Verbunden:</strong> {repoConfig.repo_url} ({repoConfig.branch})</p>
              <p className="text-gray-500">Sync-Intervall: {repoConfig.sync_interval_minutes} Min.</p>
              {repoConfig.last_synced_at && (
                <p className="text-gray-500">Letzter Sync: {repoConfig.last_synced_at}</p>
              )}
              <div className="mt-2 flex gap-2">
                <Button variant="outlined" size="sm" onClick={handleSync}>
                  <RefreshCw size={14} /> Sync
                </Button>
                <Button variant="danger" size="sm" onClick={handleDisconnect}>
                  <Unlink size={14} /> Trennen
                </Button>
              </div>
            </div>
          )}
          <form onSubmit={handleSaveRepo} className="grid gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Repo-URL</label>
              <Input type="text" value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} placeholder="https://github.com/..." />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Branch</label>
                <Input type="text" value={branch} onChange={(e) => setBranch(e.target.value)} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Sync-Intervall (Min.)</label>
                <Input type="number" value={interval} onChange={(e) => setInterval(Number(e.target.value))} />
              </div>
            </div>
            <Button type="submit"><Link2 size={18} /> Speichern & Sync</Button>
          </form>
        </Card>

        <div className="grid gap-3">
          {tasks.map((task) => (
            <Card key={task.slug} className="py-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">{task.title}</h3>
                  <p className="text-sm text-gray-500">{task.slug}</p>
                  {task.subject && <p className="text-sm text-gray-400">{task.subject}</p>}
                </div>
                {task.solutions_json && (
                  <span className="rounded-full bg-green-100 px-3 py-1 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400">
                    mit Lösungen
                  </span>
                )}
              </div>
            </Card>
          ))}
          {tasks.length === 0 && <p className="text-gray-500">Keine Aufgaben gefunden.</p>}
        </div>
      </main>
    </div>
  );
}
