const BASE = '';

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    credentials: 'same-origin',
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiPostForm<T>(
  path: string,
  formData: FormData,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    body: formData,
    credentials: 'same-origin',
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Student API ──────────────────────────────────────────────

export const studentApi = {
  joinStatus: (join_code: string, display_name: string) =>
    apiFetch<import('../types').JoinStatusResponse>('/api/join/status', {
      method: 'POST',
      body: JSON.stringify({ join_code, display_name }),
    }),

  join: (join_code: string, display_name: string, password: string) =>
    apiFetch<import('../types').JoinResponse>('/api/join', {
      method: 'POST',
      body: JSON.stringify({ join_code, display_name, password }),
    }),

  me: () => apiFetch<import('../types').Student>('/api/me'),

  logout: () =>
    apiFetch<{ ok: boolean }>('/api/logout', { method: 'POST' }),

  listTasks: () => apiFetch<import('../types').TaskListItem[]>('/api/tasks'),

  getSubmission: (slug: string) =>
    apiFetch<{ answers: Record<string, unknown> | null; submitted_at: string | null }>(
      `/api/submissions/${encodeURIComponent(slug)}`,
    ),

  submitAnswers: (slug: string, answers: Record<string, unknown>) =>
    apiFetch<{ id: number; submitted_at: string }>('/api/submissions', {
      method: 'POST',
      body: JSON.stringify({ slug, answers }),
    }),

  changePassword: (current_password: string, new_password: string) =>
    apiFetch<{ ok: boolean }>('/api/password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    }),

  getTaskHtml: (slug: string) =>
    fetch(`/api/tasks/${encodeURIComponent(slug)}/html`, {
      credentials: 'same-origin',
    }).then((res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.text();
    }),
};

// ── Admin API ────────────────────────────────────────────────

export const adminApi = {
  login: (username: string, password: string) => {
    const fd = new FormData();
    fd.append('username', username);
    fd.append('password', password);
    return apiPostForm<{ ok: boolean }>('/api/admin/login', fd);
  },

  logout: () =>
    apiFetch<{ ok: boolean }>('/api/admin/logout', { method: 'POST' }),

  me: () => apiFetch<import('../types').Teacher | null>('/api/admin/me'),

  dashboard: () =>
    apiFetch<import('../types').DashboardCounts>('/api/admin/dashboard'),

  listClasses: () =>
    apiFetch<import('../types').Class[]>('/api/admin/classes'),

  createClass: (name: string) => {
    const fd = new FormData();
    fd.append('name', name);
    return apiPostForm<import('../types').Class>('/api/admin/classes', fd);
  },

  toggleClass: (classId: number) =>
    apiFetch<{ ok: boolean }>(`/api/admin/classes/${classId}/toggle`, {
      method: 'POST',
    }),

  deleteClass: (classId: number) =>
    apiFetch<{ ok: boolean }>(`/api/admin/classes/${classId}/delete`, {
      method: 'POST',
    }),

  getQrSvg: (classId: number) =>
    fetch(`/api/admin/classes/${classId}/qr.svg`, {
      credentials: 'same-origin',
    }).then((res) => res.text()),

  listStudents: (classId: number) =>
    apiFetch<import('../types').StudentListItem[]>(
      `/api/admin/students?class_id=${classId}`,
    ),

  renameStudent: (studentId: number, display_name: string) => {
    const fd = new FormData();
    fd.append('display_name', display_name);
    return apiPostForm<{ ok: boolean }>(
      `/api/admin/students/${studentId}/rename`,
      fd,
    );
  },

  resetStudentPassword: (studentId: number) =>
    apiFetch<{ ok: boolean }>(
      `/api/admin/students/${studentId}/reset-password`,
      { method: 'POST' },
    ),

  deleteStudent: (studentId: number) =>
    apiFetch<{ ok: boolean }>(`/api/admin/students/${studentId}/delete`, {
      method: 'POST',
    }),

  listTasks: () => apiFetch<import('../types').Task[]>('/api/admin/tasks'),

  rescanTasks: () =>
    apiFetch<{ ok: boolean }>('/api/admin/tasks/rescan', { method: 'POST' }),

  getSubmissions: (classId: number, taskSlug: string) =>
    apiFetch<{
      rows: import('../types').SubmissionRow[];
      keys: string[];
      pretty_keys: string[];
    }>(`/api/admin/submissions?class_id=${classId}&task_slug=${taskSlug}`),

  getStats: (classId?: number) =>
    apiFetch<{ task_stats: import('../types').TaskStat[] }>(
      `/api/admin/stats${classId ? `?class_id=${classId}` : ''}`,
    ),

  listTeachers: () =>
    apiFetch<{ teachers: import('../types').Teacher[]; invites: import('../types').TeacherInvite[] }>(
      '/api/admin/teachers',
    ),

  createInvite: (role: string) => {
    const fd = new FormData();
    fd.append('role', role);
    return apiPostForm<{ ok: boolean }>('/api/admin/teachers/invite', fd);
  },

  revokeInvite: (inviteId: number) =>
    apiFetch<{ ok: boolean }>(
      `/api/admin/teachers/invites/${inviteId}/revoke`,
      { method: 'POST' },
    ),

  deleteTeacher: (teacherId: number) =>
    apiFetch<{ ok: boolean }>(`/api/admin/teachers/${teacherId}/delete`, {
      method: 'POST',
    }),

  getTaskRepoConfig: () =>
    apiFetch<import('../types').TaskRepoConfig | null>('/api/admin/tasks/repo'),

  saveTaskRepo: (repo_url: string, branch: string, sync_interval_minutes: number) => {
    const fd = new FormData();
    fd.append('repo_url', repo_url);
    fd.append('branch', branch);
    fd.append('sync_interval_minutes', String(sync_interval_minutes));
    return apiPostForm<{ ok: boolean }>('/api/admin/tasks/repo', fd);
  },

  syncTaskRepo: () =>
    apiFetch<{ ok: boolean }>('/api/admin/tasks/repo/sync', { method: 'POST' }),

  disconnectTaskRepo: () =>
    apiFetch<{ ok: boolean }>('/api/admin/tasks/repo/disconnect', {
      method: 'POST',
    }),

  getSubmissionViewHtml: (
    classId: number,
    taskSlug: string,
    studentId: number,
  ) =>
    fetch(
      `/api/admin/submissions/view?class_id=${classId}&task_slug=${taskSlug}&student_id=${studentId}`,
      { credentials: 'same-origin' },
    ).then((res) => res.text()),
};
