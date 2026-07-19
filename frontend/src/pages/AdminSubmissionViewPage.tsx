import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { adminApi } from '../api';
import { AdminAppBar } from '../components/ui';

export function AdminSubmissionViewPage() {
  const [searchParams] = useSearchParams();
  const classId = searchParams.get('class_id');
  const taskSlug = searchParams.get('task_slug');
  const studentId = searchParams.get('student_id');
  const [html, setHtml] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (classId && taskSlug && studentId) {
      adminApi
        .getSubmissionViewHtml(Number(classId), taskSlug, Number(studentId))
        .then((h) => {
          setHtml(h);
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, [classId, taskSlug, studentId]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <AdminAppBar />
      {loading ? (
        <main className="mx-auto max-w-4xl p-6">
          <p className="text-gray-500">Lade Schüler-Ansicht …</p>
        </main>
      ) : (
        <iframe
          srcDoc={html}
          title="Schüler-Ansicht"
          className="w-full"
          style={{ height: 'calc(100vh - 56px)', border: 'none' }}
        />
      )}
    </div>
  );
}
