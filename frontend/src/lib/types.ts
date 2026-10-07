export type ReadinessStatus = "READY" | "ALMOST_READY" | "NEEDS_WORK" | "NOT_READY";

export interface User { id: number; email: string; name: string | null; role: string; locale: "ru" | "en" | "kk"; organization_id: number | null }
export interface Profile {
  desired_role: string | null; role_family: string | null; level: string | null; stack: string[];
  target_company: string | null; interview_date: string | null; language: "ru" | "en" | "kk";
  interview_type: string | null; onboarding_completed: boolean; active_job_id: number | null;
}
export interface Me { user: User; profile: Profile | null; plan: { code: string; name: string; features: string[] }; usage: Record<string, { used: number; limit: number }> }

export interface ResumeAnalysis {
  candidate_name?: string | null; headline?: string | null; seniority: string; years_experience: number; domain?: string | null;
  role_family?: string | null; technologies: string[]; projects: { name: string; summary: string; technologies: string[] }[];
  achievements: string[]; education: string[]; weak_areas: string[]; missing_information: string[]; suspicious_claims: string[];
  measurable_impact: string[]; technical_depth?: string | null; communication_signals: string[];
  scores: { ats: number; technical: number; impact: number; clarity: number; experience: number };
  overall: number; likely_questions: { bullet: string; questions: string[] }[];
}
export interface Resume { id: number; filename: string; status: string; overall_score: number | null; analysis: ResumeAnalysis; is_primary: boolean; created_at: string }

export interface Blueprint { family: string; level: string; weights: Record<string, number>; topics: { topic: string; category: string; probability: number; source: string }[] }
export interface Match { score: number; strong: string[]; weak: string[]; missing: string[]; nice_to_have_matched: string[]; level_gap: number; expected_difficulty: number; likely_stages: string[]; potential_topics: string[] }
export interface Job {
  id: number; title: string; company_name: string | null; level: string | null; description: string; interview_date: string | null;
  status: string; analysis: { must_have?: string[]; nice_to_have?: string[]; likely_stages?: string[]; interview_topics?: string[]; expected_difficulty?: number; notes?: string | null };
  match: Partial<Match>; match_score: number | null; blueprint: Partial<Blueprint>; created_at: string;
}

export interface TranscriptItem { role: "interviewer" | "candidate"; text: string; question_id: number; kind?: string; category?: string; topic?: string }
export interface SessionState {
  session_id: number; interview_id: number; title: string; mode: string; language: string; status: "in_progress" | "completed" | "abandoned";
  difficulty: number; started_at: string | null; finished_at: string | null; progress: { main_done: number; planned_main: number };
  stage: string | null; current_question: { id: number; text: string; kind: string; category: string; topic: string } | null;
  transcript: TranscriptItem[]; overall_score: number | null;
}
export interface SessionSummary { session_id: number; interview_id: number; title: string; mode: string; status: string; overall_score: number | null; started_at: string | null; finished_at: string | null }

export interface Example { question: string; answer: string; score: number; missing_points?: string[] }
export interface Report {
  session_id: number; interview_id: number; title: string; mode: string; overall: number; summary: string; top_recommendations: string[];
  category_scores: Record<string, number>; dimensions: { key: string; score: number; strengths: string[]; weaknesses: string[]; recommendations: string[]; examples: { best?: Example; worst?: Example } }[];
  topics: { topic: string; category: string; score: number; followups: number; retest: boolean }[];
  readiness: { score: number; status: ReadinessStatus }; previous_overall: number | null; transcript: TranscriptItem[];
  attempts: { session_id: number; score: number | null; category_scores: Record<string, number>; finished_at: string | null }[];
  training_plan_id: number; difficulty: { start: number; end: number };
}

export interface Weakness {
  id: number; topic: string; category: string; severity: "low" | "medium" | "high" | "critical"; original_answer: string; question_text: string;
  correct_concept: string; why_weak: string; recommended_exercise: string; status: "open" | "improving" | "resolved"; attempts: number;
  first_score: number; current_score: number; best_score: number; history: { at: string; score: number; source: string }[]; next_retest_at: string | null;
}
export interface TrainingTask {
  id: number; day: number; topic: string; category: string; kind: string; questions: { text: string; ideal_points: string[] }[];
  answers: { index: number; text: string; score: number; feedback: string; missing_points: string[]; correct_concept: string }[];
  status: string; score: number | null; weakness_id: number | null;
}
export interface TrainingPlan { id: number; status: string; starts_on: string; days: number; tasks: TrainingTask[] }

export interface Risk { type: string; title: string; category: string; detail: string; impact: number }
export interface Dashboard {
  readiness: { score: number; status: ReadinessStatus; risks: Risk[]; confidence: string | null; categories: Record<string, { score: number; weight: number; evidence: number; confidence: string }> } | null;
  target: { job_id: number; title: string; company: string | null; match_score: number | null } | null;
  upcoming_interview: { date: string; days_left: number } | null;
  latest_interview: { session_id: number; score: number | null; finished_at: string | null } | null;
  weakest: { id: number; topic: string; severity: string; current_score: number; first_score: number; status: string }[];
  progress: { at: string; score: number }[];
  recommended_training: { id: number; day: number; topic: string; category: string; status: string }[];
  applications: Record<string, number>;
  resolved_weaknesses: number;
  next_best_action: { action: string; href: string; mode?: string; topic?: string };
}
export interface Plan { code: string; name: string; prices: Record<string, number>; interval: string; limits: Record<string, number>; features: string[] }
