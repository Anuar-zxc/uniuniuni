"use client";

import { Check } from "lucide-react";
import { useState } from "react";
import { useMe } from "@/components/me-context";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Panel } from "@/components/ui/panel";
import { Empty, ErrorNote, Loading } from "@/components/ui/states";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import type { TrainingPlan, TrainingTask } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function TrainingPage() {
  const { t } = useI18n();
  const { data: plan, setData, loading } = useApi<TrainingPlan | null>("/training");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const generate = async () => {
    setBusy(true);
    try {
      setData(await api.post<TrainingPlan>("/training/generate"));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  const updateTask = (task: TrainingTask) => plan && setData({ ...plan, tasks: plan.tasks.map((x) => (x.id === task.id ? task : x)) });

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1>{t("tr.title")}</h1>
        {plan && <Button variant="outline" onClick={generate} disabled={busy}>{t("tr.generate")}</Button>}
      </div>
      <p className="mt-3 max-w-prose text-muted">{t("tr.lead")}</p>
      <div className="mt-8">
        <ErrorNote error={error} />
        {loading || busy ? <Loading /> : !plan ? (
          <Empty action={<Button onClick={generate}>{t("tr.generate")}</Button>}>{t("tr.empty")}</Empty>
        ) : (
          <ol className="flex flex-col gap-6">
            {plan.tasks.map((task) => <TaskCard key={task.id} task={task} onUpdate={updateTask} />)}
          </ol>
        )}
      </div>
    </div>
  );
}

function TaskCard({ task, onUpdate }: { task: TrainingTask; onUpdate: (t: TrainingTask) => void }) {
  const { t, tx } = useI18n();
  const { reload } = useMe();
  const [open, setOpen] = useState(task.status !== "completed");
  const done = task.status === "completed";
  return (
    <li id={`task-${task.id}`} className="grid gap-4 md:grid-cols-[96px_1fr]">
      <div className="flex items-baseline gap-2 md:flex-col md:gap-0">
        <span className="text-sm text-muted">{t("tr.day")}</span>
        <span className="font-display text-3xl font-semibold leading-none">{task.day}</span>
      </div>
      <Panel className={cn("p-5", done && "bg-transparent")}>
        <button type="button" onClick={() => setOpen(!open)} className="flex w-full flex-wrap items-baseline justify-between gap-3 text-left" aria-expanded={open}>
          <div>
            <h3 className="text-lg">{task.topic}</h3>
            <p className="text-sm text-muted">{tx(`cat.${task.category}`, task.category)} · {task.questions.length} {task.kind === "case" ? t("tr.case") : t("tr.questions")}</p>
          </div>
          {done ? (
            <span className="inline-flex items-center gap-1.5 text-sm"><Check size={16} /> {t("tr.done")} · <span className="font-display tabular-nums">{Math.round(task.score ?? 0)}</span></span>
          ) : <span className="text-sm text-muted">{task.answers.length}/{task.questions.length}</span>}
        </button>
        {open && (
          <div className="mt-5 flex flex-col gap-6">
            {task.questions.map((q, i) => (
              <QuestionItem key={i} task={task} index={i} onUpdate={(nt) => { onUpdate(nt); if (nt.status === "completed") void reload(); }} />
            ))}
          </div>
        )}
      </Panel>
    </li>
  );
}

function QuestionItem({ task, index, onUpdate }: { task: TrainingTask; index: number; onUpdate: (t: TrainingTask) => void }) {
  const { t } = useI18n();
  const q = task.questions[index];
  const ans = task.answers.find((a) => a.index === index);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      onUpdate(await api.post<TrainingTask>(`/training/tasks/${task.id}/answer`, { index, text }));
      setText("");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="border-t border-line pt-4 first:border-t-0 first:pt-0">
      <p className="font-medium">{index + 1}. {q.text}</p>
      {ans ? (
        <div className="mt-3 grid gap-3 text-[15px] md:grid-cols-[1fr_auto]">
          <div>
            <p className="text-muted">“{ans.text}”</p>
            {ans.feedback && <p className="mt-2"><span className="font-medium">{t("tr.feedback")}:</span> {ans.feedback}</p>}
            {ans.missing_points.length > 0 && <p className="mt-1"><span className="font-medium">{t("rep.missed")}:</span> {ans.missing_points.join("; ")}</p>}
          </div>
          <span className="font-display text-2xl tabular-nums">{Math.round(ans.score)}</span>
        </div>
      ) : (
        <div className="mt-3 flex flex-col gap-2">
          <Textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} aria-label={t("tr.yourAnswer")} disabled={busy} />
          <ErrorNote error={error} />
          <Button size="sm" className="self-start" onClick={submit} disabled={busy || !text.trim()}>{t("tr.submit")}</Button>
        </div>
      )}
    </div>
  );
}
