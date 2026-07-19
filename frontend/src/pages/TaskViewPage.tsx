import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { studentApi } from '../api';
import { StudentAppBar } from '../components/ui';

export function TaskViewPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [html, setHtml] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!slug) return;
    studentApi
      .getTaskHtml(slug)
      .then((h) => {
        setHtml(h);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Aufgabe nicht gefunden');
        setLoading(false);
      });
  }, [slug]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
        <StudentAppBar />
        <main className="mx-auto max-w-4xl p-6">
          <p className="text-gray-500">Lade Aufgabe …</p>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
        <StudentAppBar />
        <main className="mx-auto max-w-4xl p-6">
          <div className="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
            {error}
          </div>
          <button
            onClick={() => navigate('/aufgaben')}
            className="mt-4 text-blue-600 hover:underline dark:text-blue-400"
          >
            ← Zurück zu Aufgaben
          </button>
        </main>
      </div>
    );
  }

  // Check if it's a full HTML document (Lernpfad) or fragment
  const isFullDoc = html.trim().startsWith('<!DOCTYPE') || html.includes('<html');

  if (isFullDoc) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
        <StudentAppBar />
        <iframe
          ref={iframeRef}
          srcDoc={html}
          title="Aufgabe"
          className="w-full"
          style={{ height: 'calc(100vh - 56px)', border: 'none' }}
        />
      </div>
    );
  }

  // Fragment: inject into page with luka.js
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <StudentAppBar />
      <main
        className="mx-auto max-w-4xl p-6"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
