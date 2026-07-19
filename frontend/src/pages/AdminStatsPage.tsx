import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { adminApi } from '../api';
import { AdminAppBar, Card, Select } from '../components/ui';
import type { Class, TaskStat } from '../types';

export function AdminStatsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const classId = searchParams.get('class_id');
  const [classes, setClasses] = useState<Class[]>([]);
  const [stats, setStats] = useState<TaskStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi.listClasses().then(setClasses);
  }, []);

  useEffect(() => {
    setLoading(true);
    adminApi
      .getStats(classId ? Number(classId) : undefined)
      .then((data) => {
        setStats(data.task_stats);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [classId]);

  const updateClass = (value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set('class_id', value);
    else next.delete('class_id');
    setSearchParams(next);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <AdminAppBar />
      <main className="mx-auto max-w-4xl p-6">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-gray-100">Statistik</h1>

        <Card className="mb-6">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Klasse</label>
          <Select value={classId ?? ''} onChange={(e) => updateClass(e.target.value)}>
            <option value="">– alle –</option>
            {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
        </Card>

        {loading ? (
          <p className="text-gray-500">Lade Statistiken …</p>
        ) : stats.length === 0 ? (
          <p className="text-gray-500">Keine Aufgaben mit Abgaben in den ausgewählten Klassen.</p>
        ) : (
          <div className="grid gap-4">
            {stats.map((ts) => (
              <Card key={`${ts.slug}:${ts.class_name}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <strong className="text-gray-900 dark:text-gray-100">{ts.title}</strong>
                    <span className="ml-2 text-sm text-gray-500">{ts.class_name}</span>
                  </div>
                  <a href={`/admin/submissions?class_id=${classId ?? ''}&task_slug=${ts.slug}`}>
                    <span className="text-sm text-blue-600 hover:underline dark:text-blue-400">Ergebnisse</span>
                  </a>
                </div>

                <div className="mt-4 flex flex-wrap gap-6">
                  <StatBar label="Abgaben" value={`${ts.submitted_count}/${ts.student_count}`} pct={ts.submission_pct} color="#2563eb" />
                  {ts.has_solutions ? (
                    <>
                      <StatBar label="Richtig" value={`${ts.fill_pct}%`} pct={ts.fill_pct} color="#16a34a" />
                      <StatBar
                        label="Fehlerquote"
                        value={`${ts.error_pct}%`}
                        pct={ts.error_pct}
                        color={ts.error_pct > 50 ? '#dc2626' : '#f59e0b'}
                      />
                    </>
                  ) : (
                    <div>
                      <div className="text-xs text-gray-500">Auswertung</div>
                      <div className="text-sm text-gray-400">Keine Lösungen hinterlegt</div>
                    </div>
                  )}
                </div>

                {ts.has_solutions && ts.hotspots.length > 0 && (
                  <details className="mt-3">
                    <summary className="cursor-pointer text-sm font-semibold text-gray-500">
                      Fehler-Hotspots (Top {ts.hotspots.length})
                    </summary>
                    <div className="mt-2 text-sm">
                      {ts.hotspots.map((spot) => (
                        <div
                          key={spot.field}
                          className="flex items-center justify-between border-b border-gray-100 py-1 dark:border-gray-800"
                        >
                          <span className="text-gray-600 dark:text-gray-400">{spot.pretty}</span>
                          <span>
                            <span className="text-green-600">{spot.correct} richtig</span>
                            {' · '}
                            <span className="text-red-600">{spot.wrong} falsch</span>
                            {' · '}
                            <span className="text-gray-400">{spot.empty} leer</span>
                            {' · '}
                            <strong style={{ color: spot.error_pct > 50 ? '#dc2626' : '#f59e0b' }}>
                              {spot.error_pct}%
                            </strong>
                          </span>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function StatBar({ label, value, pct, color }: { label: string; value: string; pct: number; color: string }) {
  return (
    <div>
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-lg font-semibold" style={{ color }}>{value}</div>
      <div className="mt-1 h-1.5 w-32 rounded-full bg-gray-200 dark:bg-gray-700">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}
