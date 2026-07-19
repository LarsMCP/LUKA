import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { studentApi } from '../api';
import { useAuth } from '../hooks/useAuth';
import { StudentAppBar, Card } from '../components/ui';
import type { TaskListItem } from '../types';

export function TasksPage() {
  const { student } = useAuth();
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    studentApi.listTasks().then((t) => {
      setTasks(t);
      setLoading(false);
    });
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <StudentAppBar />
      <main className="mx-auto max-w-4xl p-6">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-gray-100">
          Hallo {student?.display_name}!
        </h1>
        {loading ? (
          <p className="text-gray-500">Lade Aufgaben …</p>
        ) : tasks.length === 0 ? (
          <Card>
            <p className="text-gray-500 dark:text-gray-400">
              Dir sind noch keine Aufgaben freigeschaltet.
            </p>
          </Card>
        ) : (
          <div className="grid gap-4">
            {tasks.map((task) => (
              <Link
                key={task.slug}
                to={`/task/${task.slug}`}
                className="block rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition hover:shadow-md dark:border-gray-700 dark:bg-gray-900"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="font-semibold text-gray-900 dark:text-gray-100">
                      {task.title}
                    </h2>
                    {task.subject && (
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {task.subject}
                      </p>
                    )}
                  </div>
                  {task.submitted && (
                    <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
                      abgegeben
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
