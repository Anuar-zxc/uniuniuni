"use client";

import { useState } from "react";
import { useMe } from "@/components/me-context";
import { Button } from "@/components/ui/button";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { Panel } from "@/components/ui/panel";
import { ErrorNote, Loading } from "@/components/ui/states";
import { api } from "@/lib/api";
import type { DictKey } from "@/lib/dict";
import { useApi } from "@/lib/hooks";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

type Row = Record<string, unknown>;
const TABS: [string, DictKey][] = [
  ["overview", "admin.overview"], ["users", "admin.users"], ["ai", "admin.ai"], ["failures", "admin.failures"],
  ["prompts", "admin.prompts"], ["questions", "admin.questions"], ["plans", "admin.plans"], ["payments", "admin.payments"],
];

export default function AdminPage() {
  const { t } = useI18n();
  const { me } = useMe();
  const [tab, setTab] = useState("overview");
  if (!me) return <Loading />;
  if (me.user.role !== "admin") return <ErrorNote error={new Error("403")} />;
  return (
    <div>
      <h1>{t("admin.title")}</h1>
      <div className="mt-6 flex flex-wrap gap-1 border-b border-line" role="tablist">
        {TABS.map(([k, label]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={cn("-mb-px border-b-2 px-3 py-2 text-sm", tab === k ? "border-ink font-medium" : "border-transparent text-muted hover:text-ink")}>
            {t(label)}
          </button>
        ))}
      </div>
      <div className="pt-6">
        {tab === "overview" && <Overview />}
        {tab === "users" && <Users />}
        {tab === "ai" && <AIUsage />}
        {tab === "failures" && <Failures />}
        {tab === "prompts" && <Prompts />}
        {tab === "questions" && <Questions />}
        {tab === "plans" && <Table path="/admin/plans" cols={["code", "name", "prices", "limits", "is_active"]} />}
        {tab === "payments" && <Table path="/admin/payments" cols={["id", "user_id", "provider", "amount", "currency", "status", "created_at"]} />}
      </div>
    </div>
  );
}

const fmt = (v: unknown) => (v === null || v === undefined ? "—" : typeof v === "object" ? JSON.stringify(v) : String(v));

function Table({ path, cols, actions }: { path: string; cols: string[]; actions?: (r: Row, reload: () => void) => React.ReactNode }) {
  const { data, loading, error, reload } = useApi<Row[]>(path);
  if (loading) return <Loading />;
  if (error) return <ErrorNote error={error} />;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="border-b border-line text-muted">
          <tr>{cols.map((c) => <th key={c} className="py-2 pr-4 font-medium">{c}</th>)}{actions && <th />}</tr>
        </thead>
        <tbody className="divide-y divide-line">
          {(data ?? []).map((r, i) => (
            <tr key={i} className="align-top">
              {cols.map((c) => <td key={c} className="max-w-[320px] truncate py-2 pr-4" title={fmt(r[c])}>{fmt(r[c])}</td>)}
              {actions && <td className="py-2 text-right">{actions(r, reload)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Overview() {
  const { data, loading } = useApi<Row>("/admin/overview");
  if (loading || !data) return <Loading />;
  const funnel = data.funnel as Record<string, number>;
  const stats = Object.entries(data).filter(([, v]) => typeof v === "number") as [string, number][];
  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <div>
        <h2 className="mb-4 text-lg">Funnel</h2>
        <ol className="flex flex-col gap-2">
          {Object.entries(funnel).map(([k, v]) => {
            const max = Math.max(1, funnel.signed_up);
            return (
              <li key={k} className="grid grid-cols-[180px_1fr_48px] items-center gap-3 text-sm">
                <span>{k}</span>
                <div className="h-2 rounded-full bg-line"><div className="h-2 rounded-full bg-primary" style={{ width: `${(v / max) * 100}%` }} /></div>
                <span className="text-right tabular-nums">{v}</span>
              </li>
            );
          })}
        </ol>
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-4 text-sm">
        {stats.map(([k, v]) => (
          <div key={k}><dt className="text-muted">{k}</dt><dd className="font-display text-xl tabular-nums">{v}</dd></div>
        ))}
        <div><dt className="text-muted">revenue</dt><dd className="font-display text-xl">{fmt(data.revenue)}</dd></div>
      </dl>
    </div>
  );
}

function Users() {
  const { t } = useI18n();
  return (
    <Table path="/admin/users" cols={["id", "email", "name", "role", "is_active", "created_at"]} actions={(r, reload) => (
      <div className="flex justify-end gap-2">
        {r.role !== "admin" && <Button size="sm" variant="outline" onClick={async () => { await api.patch(`/admin/users/${r.id}`, { role: "admin" }); reload(); }}>{t("admin.makeAdmin")}</Button>}
        <Button size="sm" variant="ghost" onClick={async () => { await api.patch(`/admin/users/${r.id}`, { is_active: !r.is_active }); reload(); }}>
          {r.is_active ? t("admin.disable") : t("admin.enable")}
        </Button>
      </div>
    )} />
  );
}

function AIUsage() {
  const { data, loading } = useApi<{ by_task: Row[]; by_status: Record<string, number> }>("/admin/ai/usage");
  if (loading || !data) return <Loading />;
  const cols = ["task", "provider", "model", "requests", "input_tokens", "output_tokens", "cost_usd", "avg_latency_ms"];
  return (
    <div>
      <p className="mb-4 text-sm text-muted">{Object.entries(data.by_status).map(([k, v]) => `${k}: ${v}`).join("   ")}</p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="border-b border-line text-muted"><tr>{cols.map((c) => <th key={c} className="py-2 pr-4 font-medium">{c}</th>)}</tr></thead>
          <tbody className="divide-y divide-line">
            {data.by_task.map((r, i) => <tr key={i}>{cols.map((c) => <td key={c} className="py-2 pr-4 tabular-nums">{fmt(r[c])}</td>)}</tr>)}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Failures() {
  const { t } = useI18n();
  return (
    <Table path="/admin/ai/failures" cols={["id", "task", "status", "error", "response_excerpt", "created_at"]} actions={(r, reload) => (
      <Button size="sm" variant="outline" onClick={async () => { await api.post(`/admin/ai/failures/${r.id}/review`); reload(); }}>{t("admin.markReviewed")}</Button>
    )} />
  );
}

function Prompts() {
  const { t } = useI18n();
  const { data, loading, reload } = useApi<{ keys: string[]; versions: Row[] }>("/admin/prompts");
  const [key, setKey] = useState("");
  const [draft, setDraft] = useState({ system: "", user_template: "" });
  const [error, setError] = useState<unknown>(null);
  if (loading || !data) return <Loading />;
  const k = key || data.keys[0];
  const versions = data.versions.filter((v) => v.key === k);
  const active = versions.find((v) => v.is_active);
  const startEdit = (v: Row | undefined) => setDraft({ system: String(v?.system ?? ""), user_template: String(v?.user_template ?? "") });
  return (
    <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
      <ul className="flex flex-col gap-1">
        {data.keys.map((x) => (
          <li key={x}><button onClick={() => { setKey(x); startEdit(data.versions.find((v) => v.key === x && v.is_active)); }}
            className={cn("w-full rounded-lg px-3 py-2 text-left text-sm", x === k ? "bg-ink text-paper" : "hover:bg-line/50")}>{x}</button></li>
        ))}
      </ul>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-2">
          {versions.map((v) => (
            <Panel key={String(v.id)} className="flex items-center gap-3 px-3 py-2 text-sm">
              <button onClick={() => startEdit(v)}>v{String(v.version)}</button>
              {v.is_active ? <span className="text-muted">active</span> : (
                <Button size="sm" variant="ghost" onClick={async () => { await api.post(`/admin/prompts/${v.id}/activate`); await reload(); }}>{t("admin.activate")}</Button>
              )}
            </Panel>
          ))}
        </div>
        {!draft.system && active && <Button variant="outline" size="sm" className="self-start" onClick={() => startEdit(active)}>Edit v{String(active.version)}</Button>}
        <div><Label htmlFor="sys">system</Label><Textarea id="sys" rows={8} className="font-mono text-xs" value={draft.system} onChange={(e) => setDraft({ ...draft, system: e.target.value })} /></div>
        <div><Label htmlFor="usr">user_template</Label><Textarea id="usr" rows={10} className="font-mono text-xs" value={draft.user_template} onChange={(e) => setDraft({ ...draft, user_template: e.target.value })} /></div>
        <ErrorNote error={error} />
        <Button className="self-start" disabled={!draft.system} onClick={async () => {
          try { await api.post("/admin/prompts", { key: k, ...draft, activate: true }); await reload(); } catch (e) { setError(e); }
        }}>{t("admin.newVersion")}</Button>
      </div>
    </div>
  );
}

function Questions() {
  const { t } = useI18n();
  const [form, setForm] = useState({ category: "technical", topic: "", role_family: "any", difficulty: "3", text: "", ideal_points: "" });
  const [ver, setVer] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const add = async () => {
    try {
      await api.post("/admin/questions", { ...form, difficulty: Number(form.difficulty), ideal_points: form.ideal_points.split("\n").map((s) => s.trim()).filter(Boolean) });
      setForm({ ...form, topic: "", text: "", ideal_points: "" });
      setVer(ver + 1);
    } catch (e) {
      setError(e);
    }
  };
  return (
    <div className="flex flex-col gap-8">
      <Panel className="grid gap-3 p-4 sm:grid-cols-4">
        <div><Label>category</Label><Select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
          {["technical", "coding", "system_design", "behavioral", "hr", "project_deep_dive", "debugging", "architecture"].map((c) => <option key={c}>{c}</option>)}
        </Select></div>
        <div><Label>topic</Label><Input value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} /></div>
        <div><Label>role_family</Label><Select value={form.role_family} onChange={(e) => setForm({ ...form, role_family: e.target.value })}>
          {["any", "frontend", "backend", "ml", "data", "devops", "qa", "product"].map((c) => <option key={c}>{c}</option>)}
        </Select></div>
        <div><Label>difficulty</Label><Select value={form.difficulty} onChange={(e) => setForm({ ...form, difficulty: e.target.value })}>{[1, 2, 3, 4, 5].map((d) => <option key={d}>{d}</option>)}</Select></div>
        <div className="sm:col-span-2"><Label>text</Label><Textarea rows={3} value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} /></div>
        <div className="sm:col-span-2"><Label>ideal_points (one per line)</Label><Textarea rows={3} value={form.ideal_points} onChange={(e) => setForm({ ...form, ideal_points: e.target.value })} /></div>
        <div className="sm:col-span-4"><ErrorNote error={error} /><Button size="sm" onClick={add} disabled={!form.topic || form.text.length < 10}>{t("admin.add")}</Button></div>
      </Panel>
      <Table key={ver} path="/admin/questions" cols={["id", "category", "topic", "role_family", "difficulty", "text", "is_active"]} />
    </div>
  );
}
