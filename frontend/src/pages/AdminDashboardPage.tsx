import { useEffect, useState } from 'react';
import { adminApi } from '../api';
import { AdminAppBar, Card } from '../components/ui';
import type { DashboardCounts } from '../types';

export function AdminDashboardPage() {
  const [counts, setCounts] = useState<DashboardCounts | null>(null);

  useEffect(() => {
    adminApi.dashboard().then(setCounts);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <AdminAppBar />
      <main className="mx-auto max-w-4xl p-6">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-gray-100">
          Übersicht
        </h1>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {counts ? (
            <>
              <StatCard label="Klassen" value={counts.classes} />
              <StatCard label="Aufgaben" value={counts.tasks} />
              <StatCard label="Schüler" value={counts.students} />
              <StatCard label="Abgaben" value={counts.submissions} />
            </>
          ) : (
            <p className="text-gray-500">Lade …</p>
          )}
        </div>
      </main>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Card className="text-center">
      <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
        {value}
      </div>
      <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
        {label}
      </div>
    </Card>
  );
}
