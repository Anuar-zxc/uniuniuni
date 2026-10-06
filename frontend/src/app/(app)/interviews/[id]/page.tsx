"use client";

import { Mic, Square, Volume2, VolumeX } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { ErrorNote, Loading } from "@/components/ui/states";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import type { SessionState } from "@/lib/types";
import { cn } from "@/lib/utils";
import { createRecognizer, speak, stopSpeaking } from "@/lib/voice";

function useElapsed(startedAt: string | null, running: boolean) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [running]);
  if (!startedAt) return "0:00";
  const s = Math.max(0, Math.floor((now - new Date(startedAt).getTime()) / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export default function InterviewRoom() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { t, tx } = useI18n();
  const { data: state, setData, error: loadError, loading } = useApi<SessionState>(`/interviews/sessions/${id}`);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [listening, setListening] = useState(false);
  const [readAloud, setReadAloud] = useState(false);
  const recRef = useRef<ReturnType<typeof createRecognizer>>(null);
  const answerStart = useRef<number>(Date.now());
  const bottomRef = useRef<HTMLDivElement>(null);
  const elapsed = useElapsed(state?.started_at ?? null, state?.status === "in_progress");

  const qid = state?.current_question?.id;
  useEffect(() => {
    answerStart.current = Date.now();
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    if (readAloud && state?.current_question) speak(state.current_question.text, state.language);
  }, [qid]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => { recRef.current?.stop(); stopSpeaking(); }, []);

  if (loading) return <Loading />;
  if (loadError || !state) return <ErrorNote error={loadError} />;

  const submit = async () => {
    if (!answer.trim() || busy) return;
    recRef.current?.stop();
    setBusy(true);
    setError(null);
    try {
      const next = await api.post<SessionState>(`/interviews/sessions/${id}/answer`, {
        text: answer.trim(), duration_seconds: Math.round((Date.now() - answerStart.current) / 1000),
      });
      setData(next);
      setAnswer("");
      if (next.status === "completed") router.push(`/interviews/${id}/report`);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const finish = async () => {
    if (!window.confirm(t("iv.finishConfirm"))) return;
    setBusy(true);
    const next = await api.post<SessionState>(`/interviews/sessions/${id}/finish`).catch((e) => { setError(e); return null; });
    setBusy(false);
    if (next) {
      setData(next);
      if (next.status === "completed") router.push(`/interviews/${id}/report`);
    }
  };

  const toggleVoice = () => {
    if (listening) {
      recRef.current?.stop();
      return;
    }
    const rec = createRecognizer(state.language);
    if (!rec) {
      setError(new Error(t("iv.voiceUnsupported")));
      return;
    }
    rec.onresult = (e) => {
      let chunk = "";
      for (let i = e.resultIndex; i < e.results.length; i++) if (e.results[i].isFinal) chunk += e.results[i][0].transcript;
      if (chunk) setAnswer((a) => (a ? `${a} ${chunk.trim()}` : chunk.trim()));
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recRef.current = rec;
    rec.start();
    setListening(true);
  };

  const p = state.progress;
  const cq = state.current_question;
  const done = state.status !== "in_progress";
  const questionNo = Math.min(p.planned_main, p.main_done + (cq?.kind === "main" ? 1 : 0)) || 1;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="sticky top-[57px] z-10 -mx-4 border-b border-line bg-paper/95 px-4 py-3 backdrop-blur sm:-mx-8 sm:px-8 lg:top-0">
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1">
            <span className="font-medium">{t("iv.question")} {questionNo} {t("iv.of")} {p.planned_main}</span>
            {state.stage && <span className="text-muted">{t("iv.stage")}: <span className="text-ink">{tx(`cat.${state.stage}`, state.stage)}</span></span>}
            <span className="text-muted">{t("iv.diff")}: <span className="tabular-nums text-ink">{state.difficulty}/5</span></span>
            <span className="text-muted">{t("iv.timer")}: <span className="tabular-nums text-ink">{elapsed}</span></span>
          </div>
          <div className="flex items-center gap-1">
            <button type="button" onClick={() => { setReadAloud(!readAloud); if (readAloud) stopSpeaking(); }} aria-pressed={readAloud}
              className="rounded-lg p-2 text-muted hover:bg-line/50 hover:text-ink" aria-label="Read questions aloud">
              {readAloud ? <Volume2 size={18} /> : <VolumeX size={18} />}
            </button>
            {!done && <Button variant="ghost" size="sm" onClick={finish} disabled={busy}>{t("iv.finish")}</Button>}
          </div>
        </div>
        <div className="mt-2 flex h-1 gap-[2px]" aria-hidden>
          {Array.from({ length: p.planned_main }).map((_, i) => (
            <div key={i} className={cn("h-1 flex-1 rounded-full", i < p.main_done ? "bg-ink" : "bg-line")} />
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-5 py-6" aria-live="polite">
        {state.transcript.map((m, i) => {
          const isCurrent = m.role === "interviewer" && m.question_id === cq?.id;
          return m.role === "interviewer" ? (
            <div key={i} className={cn("max-w-[92%]", !isCurrent && "opacity-80")}>
              {m.kind === "followup" && <p className="mb-1 text-xs text-muted">{t("iv.followup")}</p>}
              <div className={cn("whitespace-pre-wrap rounded-panel rounded-tl-sm border bg-raised px-4 py-3", isCurrent ? "border-ink text-[17px]" : "border-line")}>{m.text}</div>
            </div>
          ) : (
            <div key={i} className="ml-auto max-w-[85%] whitespace-pre-wrap rounded-panel rounded-tr-sm bg-line/60 px-4 py-3">{m.text}</div>
          );
        })}
        {busy && <p className="text-sm text-muted">{t("iv.thinking")}</p>}
        <div ref={bottomRef} />
      </div>

      {done ? (
        <div className="flex flex-wrap items-center gap-3 border-t border-line py-6">
          <p className="font-medium">{t("iv.completed")}</p>
          {state.status === "completed" && <Link href={`/interviews/${id}/report`} className={buttonVariants()}>{t("iv.viewReport")}</Link>}
        </div>
      ) : (
        <div className="sticky bottom-0 -mx-4 border-t border-line bg-paper px-4 pb-4 pt-3 sm:-mx-8 sm:px-8">
          <label htmlFor="answer" className="sr-only">{t("iv.answer")}</label>
          <Textarea id="answer" rows={4} value={answer} disabled={busy} placeholder={t("iv.answerHint")}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); void submit(); } }} />
          <div className="mt-2 flex items-center justify-between gap-3">
            <Button type="button" variant="outline" size="sm" onClick={toggleVoice} aria-pressed={listening}>
              {listening ? <><Square size={14} /> {t("iv.voiceStop")}</> : <><Mic size={14} /> {t("iv.voice")}</>}
            </Button>
            <Button onClick={submit} disabled={busy || !answer.trim()}>{t("iv.send")}</Button>
          </div>
          <div className="mt-2"><ErrorNote error={error} /></div>
        </div>
      )}
    </div>
  );
}
