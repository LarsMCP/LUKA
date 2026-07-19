export interface Student {
  id: number;
  display_name: string;
  class_id: number;
}

export interface Teacher {
  id: number;
  username: string;
  role: 'admin' | 'teacher';
  created_at: string;
}

export interface Class {
  id: number;
  name: string;
  join_code: string;
  owner_teacher_id: number | null;
  active: boolean;
  created_at: string;
}

export interface Task {
  slug: string;
  title: string;
  subject: string | null;
  hash: string | null;
  solutions_json: string | null;
  discovered_at: string;
}

export interface Assignment {
  id: number;
  class_id: number;
  task_slug: string;
  active: boolean;
}

export interface Submission {
  id: number;
  student_id: number;
  task_slug: string;
  answers_json: string;
  submitted_at: string;
}

export interface TaskListItem {
  slug: string;
  title: string;
  subject: string | null;
  submitted: boolean;
}

export interface SubmissionRow {
  student: string;
  student_id: number;
  submitted_at: string | null;
  answers: Record<string, unknown> | null;
}

export interface JoinStatusResponse {
  mode: 'new' | 'existing';
  class: string;
}

export interface JoinResponse {
  student_id: number;
  display_name: string;
  class: string;
}

export interface DashboardCounts {
  classes: number;
  tasks: number;
  students: number;
  submissions: number;
}

export interface StudentListItem {
  id: number;
  display_name: string;
  submissions: number;
  has_password: boolean;
}

export interface TaskStat {
  slug: string;
  title: string;
  class_name: string;
  student_count: number;
  submitted_count: number;
  has_solutions: boolean;
  submission_pct: number;
  fill_pct: number;
  error_pct: number;
  hotspots: Hotspot[];
}

export interface Hotspot {
  field: string;
  pretty: string;
  correct: number;
  wrong: number;
  empty: number;
  total: number;
  error_pct: number;
}

export interface TeacherInvite {
  id: number;
  code: string;
  role: 'admin' | 'teacher';
  created_at: string;
  expires_at: string;
  used_at: string | null;
  used_by_teacher_id: number | null;
}

export interface TaskRepoConfig {
  id: number;
  repo_url: string;
  branch: string;
  sync_interval_minutes: number;
  last_synced_at: string | null;
  last_sync_status: string | null;
  last_sync_error: string | null;
}
