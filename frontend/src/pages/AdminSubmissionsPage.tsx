import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { adminApi } from '../api';
import { AdminAppBar, Card, Button, Select } from '../components/ui';
import type { Class, Task, SubmissionRow } from '../types';
import { Download, Eye } from 'lucide-react';

export function AdminSubmissionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const classId = searchParams.get('class_id');
  const taskSlug = searchParams.get('task_slug');

  const [classes, setClasses] = useState<Class[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [rows, setRows] = useState<SubmissionRow[]>([]);
  const [keys, setKeys] = useState<string[]>([]);
  const [prettyKeys, setPrettyKeys] = useState<string[]>([]);

  useEffect(() => {
    adminApi.listClasses().then(setClasses);
  }, []);

  useEffect(() => {
    if (classId) {
      adminApi.listTasks().then((allTasks) => {
        setTasks(allTasks);
      });
    }
  }, [classId]);

  useEffect(() => {
    if (classId && taskSlug) {
      adminApi.getSubmissions(Number(classId), taskSlug).then((data) => {
        setRows(data.rows);
        setKeys(data.keys);
        setPrettyKeys(data.pretty_keys);
      });
    } else {
      setRows([]);
      setKeys([]);
      setPrettyKeys([]);
    }
  }, [classId, taskSlug]);

  const updateParam = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  };

  const handleCsv = () => {
    if (classId && taskSlug) {
      window.location.href = `/api/admin/submissions.csv?class_id=${classId}&task_slug=${taskSlug}`;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <AdminAppBar />
      <main className="mx-auto max-w-5xl p-6">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-gray-100">Ergebnisse</h1>

        <Card className="mb-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Klasse</label>
              <Select value={classId ?? ''} onChange={(e) => updateParam('class_id', e.target.value)}>
                <option value="">– wählen –</option>
                {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Aufgabe</label>
              <Select value={taskSlug ?? ''} onChange={(e) => updateParam('task_slug', e.target.value)} disabled={!classId}>
                <option value="">– wählen –</option>
                {tasks.map((t) => <option key={t.slug} value={t.slug}>{t.title}</option>)}
              </Select>
            </div>
          </div>
          {classId && taskSlug && (
            <div className="mt-4">
              <Button variant="outlined" size="sm" onClick={handleCsv}>
                <Download size={16} /> CSV-Export
              </Button>
            </div>
          )}
        </Card>

        {rows.length > 0 && (
          <div className="grid gap-3">
            {rows.map((row) => (
              <Card key={row.student_id} className="py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-gray-900 dark:text-gray-100">{row.student}</span>
                    {row.submitted_at && (
                      <span className="ml-3 text-sm text-gray-500">
                        {new Date(row.submitted_at).toLocaleString('de-DE')}
                      </span>
                    )}
                  </div>
                  {row.answers && classId && taskSlug && (
                    <a href={`/admin/submissions/view?class_id=${classId}&task_slug=${taskSlug}&student_id=${row.student_id}`}>
                      <Button variant="outlined" size="sm">
                        <Eye size={16} /> Ansehen
                      </Button>
                    </a>
                  )}
                </div>
                {row.answers && (
                  <details className="mt-3">
                    <summary className="cursor-pointer text-sm text-gray-500">Antworten anzeigen</summary>
                    <div className="mt-2 grid gap-1 text-sm">
                      {keys.map((key, i) => (
                        <div key={key} className="flex gap-2 border-b border-gray-100 py-1 dark:border-gray-800">
                          <span className="w-48 text-gray-500">{prettyKeys[i]}</span>
                          <span className="font-medium text-gray-900 dark:text-gray-100">
                            {formatAnswer(row.answers?.[key])}
                          </span>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
                {!row.answers && (
                  <p className="mt-2 text-sm text-gray-400">Keine Abgabe</p>
                )}
              </Card>
            ))}
          </div>
        )}
        {classId && taskSlug && rows.length === 0 && (
          <p className="text-gray-500">Keine Abgaben für diese Aufgabe.</p>
        )}
      </main>
    </div>
  );
}

function formatAnswer(value: unknown): string {
  if (Array.isArray(value)) return value.join('; ');
  if (value === null || value === undefined) return '—';
  return String(value);
}
