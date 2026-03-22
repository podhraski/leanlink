//main page for leanlink - lets users run reconcile and suggest queries against the api
import { useState, useCallback } from "react";
import {
  Search,
  Sparkles,
  Eye,
  Loader2,
  GraduationCap,
  Globe,
  Hash,
  Calendar,
  Award,
  CheckCircle2,
  XCircle,
  ArrowUpDown,
  LinkIcon,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip as ReTooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface ReconcileResult {
  id: string;
  name: string;
  score: number;
  match: boolean;
  country?: string;
  type?: { id: string; name: string }[];
}

interface SuggestResult {
  id: string;
  name: string;
  score: number;
}

interface PreviewData {
  id: string;
  name: string;
  country?: string;
  rank?: number | string;
  year?: number | string;
  source?: string;
  overall_score?: number;
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [country, setCountry] = useState("");
  const [topK, setTopK] = useState("5");
  const [reconcileResults, setReconcileResults] = useState<ReconcileResult[]>([]);
  const [suggestResults, setSuggestResults] = useState<SuggestResult[]>([]);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"reconcile" | "suggest">("reconcile");
  const [error, setError] = useState<string | null>(null);

  //show an error toast for 4 seconds then clear it
  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(null), 4000);
  };

  //send a reconcile request to the api and update results state
  const handleReconcile = useCallback(async () => {
    if (!query.trim()) {
      showError("Please enter a query");
      return;
    }
    setLoading(true);
    setActiveTab("reconcile");
    try {
      const payload: any = {
        queries: {
          q0: {
            query: query.trim(),
            limit: parseInt(topK),
            properties: country.trim()
              ? [{ p: "country", v: country.trim() }]
              : [],
          },
        },
      };
      const res = await fetch("/reconcile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Request failed" }));
        throw new Error(err.error || "Request failed");
      }
      const data = await res.json();
      const results = data.q0?.result || [];
      setReconcileResults(results);
      setSuggestResults([]);
    } catch (e: any) {
      showError(e.message);
    } finally {
      setLoading(false);
    }
  }, [query, country, topK]);

  //send a suggest request using the query as a prefix
  const handleSuggest = useCallback(async () => {
    if (!query.trim()) {
      showError("Please enter a prefix");
      return;
    }
    setSuggestLoading(true);
    setActiveTab("suggest");
    try {
      const res = await fetch(`/suggest?prefix=${encodeURIComponent(query.trim())}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Request failed" }));
        throw new Error(err.error || "Request failed");
      }
      const data = await res.json();
      setSuggestResults(data.result || []);
      setReconcileResults([]);
    } catch (e: any) {
      showError(e.message);
    } finally {
      setSuggestLoading(false);
    }
  }, [query]);

  //fetch entity details for the preview modal by id
  const handlePreview = useCallback(async (id: string) => {
    setPreviewLoading(true);
    setPreviewOpen(true);
    setPreviewData(null);
    try {
      const res = await fetch(`/preview?id=${encodeURIComponent(id)}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Not found" }));
        throw new Error(err.error || "Not found");
      }
      const data = await res.json();
      setPreviewData(data);
    } catch (e: any) {
      showError(e.message);
      setPreviewOpen(false);
    } finally {
      setPreviewLoading(false);
    }
  }, []);

  //score helper functions - green above 0.9, yellow above 0.7, grey otherwise
  const scoreColor = (score: number) => {
    if (score >= 0.9) return "text-green-700 dark:text-green-400";
    if (score >= 0.7) return "text-yellow-700 dark:text-yellow-400";
    return "text-muted-foreground";
  };

  const scoreBg = (score: number) => {
    if (score >= 0.9) return "bg-green-100 dark:bg-green-900/30";
    if (score >= 0.7) return "bg-yellow-100 dark:bg-yellow-900/30";
    return "bg-muted";
  };

  const scoreBarColor = (score: number) =>
    score >= 0.9 ? "#22c55e" : score >= 0.7 ? "#eab308" : "#94a3b8";

  //build chart data from current reconcile results
  const pieData = [
    { name: "Matched", value: reconcileResults.filter((r) => r.match).length, color: "#22c55e" },
    { name: "No Match", value: reconcileResults.filter((r) => !r.match).length, color: "#94a3b8" },
  ].filter((d) => d.value > 0);

  const barData = reconcileResults.map((r) => ({
    name: r.name.length > 18 ? r.name.slice(0, 17) + "…" : r.name,
    score: r.score,
  }));

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
        {error && (
          <div className="fixed top-4 right-4 z-50 bg-destructive text-destructive-foreground px-4 py-3 rounded-md shadow-md text-sm">
            {error}
          </div>
        )}

        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <LinkIcon className="h-7 w-7 text-primary" />
            <h1 className="text-3xl font-bold tracking-tight" data-testid="text-title">
              Lean Link
            </h1>
          </div>
          <p className="text-muted-foreground text-sm">
            W3C / OpenRefine-compatible reconciliation service for university rankings
          </p>
        </div>

        <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
          <div className="p-6 pb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Search className="h-4 w-4" />
              Query
            </h2>
          </div>
          <div className="p-6 pt-0 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-[1fr_200px_120px] gap-3 items-end">
              <div className="space-y-1.5">
                <label htmlFor="query-input" className="text-sm font-medium leading-none">
                  Institution name
                </label>
                <input
                  id="query-input"
                  data-testid="input-query"
                  placeholder="e.g. University of Toronto"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleReconcile()}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="country-input" className="text-sm font-medium leading-none">
                  Country (optional)
                </label>
                <input
                  id="country-input"
                  data-testid="input-country"
                  placeholder="e.g. Canada, US, UK"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium leading-none">Top K</label>
                <select
                  data-testid="select-topk"
                  value={topK}
                  onChange={(e) => setTopK(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  <option value="3">3</option>
                  <option value="5">5</option>
                  <option value="10">10</option>
                  <option value="15">15</option>
                  <option value="20">20</option>
                </select>
              </div>
            </div>

            <div className="flex gap-2 flex-wrap">
              <button
                onClick={handleReconcile}
                disabled={loading}
                data-testid="button-reconcile"
                className="inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground text-sm font-medium h-10 px-4 py-2 hover:bg-primary/90 disabled:pointer-events-none disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                ) : (
                  <Search className="h-4 w-4 mr-1.5" />
                )}
                Reconcile
              </button>
              <button
                onClick={handleSuggest}
                disabled={suggestLoading}
                data-testid="button-suggest"
                className="inline-flex items-center justify-center rounded-md border border-input bg-background text-sm font-medium h-10 px-4 py-2 hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
              >
                {suggestLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                ) : (
                  <Sparkles className="h-4 w-4 mr-1.5" />
                )}
                Suggest
              </button>
            </div>
          </div>
        </div>

        {activeTab === "reconcile" && reconcileResults.length > 0 && (
          <div className="grid grid-cols-3 gap-4 items-start">
            {/* Table — 2/3 */}
            <div className="col-span-2 rounded-lg border bg-card text-card-foreground shadow-sm">
              <div className="p-6 pb-3">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <ArrowUpDown className="h-4 w-4" />
                  Reconciliation Results
                  <span className="ml-1 inline-flex items-center rounded-full bg-secondary text-secondary-foreground px-2.5 py-0.5 text-xs font-semibold">
                    {reconcileResults.length}
                  </span>
                </h2>
              </div>
              <div className="p-0 overflow-x-auto">
                <table className="w-full caption-bottom text-sm">
                  <thead className="[&_tr]:border-b">
                    <tr className="border-b transition-colors hover:bg-muted/50">
                      <th className="h-12 px-4 pl-6 text-left align-middle font-medium text-muted-foreground">Name</th>
                      <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Country</th>
                      <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Score</th>
                      <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Match</th>
                      <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">ID</th>
                      <th className="h-12 px-4 w-[70px] align-middle font-medium text-muted-foreground"></th>
                    </tr>
                  </thead>
                  <tbody className="[&_tr:last-child]:border-0">
                    {reconcileResults.map((r, idx) => (
                      <tr key={`${r.id}-${idx}`} data-testid={`row-result-${idx}`} className="border-b transition-colors hover:bg-muted/50">
                        <td className="p-4 pl-6 font-medium align-middle" data-testid={`text-name-${idx}`}>
                          <div className="flex items-center gap-2">
                            <GraduationCap className="h-4 w-4 text-muted-foreground shrink-0" />
                            {r.name}
                          </div>
                        </td>
                        <td className="p-4 align-middle" data-testid={`text-country-${idx}`}>
                          <div className="flex items-center gap-1.5">
                            <Globe className="h-3.5 w-3.5 text-muted-foreground" />
                            {r.country || "—"}
                          </div>
                        </td>
                        <td className="p-4 align-middle" data-testid={`text-score-${idx}`}>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-sm font-mono font-medium ${scoreBg(r.score)} ${scoreColor(r.score)}`}>
                            {r.score.toFixed(4)}
                          </span>
                        </td>
                        <td className="p-4 align-middle" data-testid={`text-match-${idx}`}>
                          {r.match ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-primary text-primary-foreground px-2.5 py-0.5 text-xs font-semibold">
                              <CheckCircle2 className="h-3 w-3" />
                              Yes
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full border text-muted-foreground px-2.5 py-0.5 text-xs font-semibold">
                              <XCircle className="h-3 w-3" />
                              No
                            </span>
                          )}
                        </td>
                        <td className="p-4 align-middle font-mono text-xs text-muted-foreground" data-testid={`text-id-${idx}`}>
                          {r.id}
                        </td>
                        <td className="p-4 align-middle">
                          <button
                            onClick={() => handlePreview(r.id)}
                            data-testid={`button-preview-${idx}`}
                            className="inline-flex items-center justify-center rounded-md h-10 w-10 hover:bg-accent hover:text-accent-foreground"
                          >
                            <Eye className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Charts — 1/3 */}
            <div className="col-span-1 flex flex-col gap-4">
              {/* Pie: Match distribution */}
              <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-4">
                <h3 className="text-sm font-semibold mb-1 text-card-foreground">Match Distribution</h3>
                <p className="text-xs text-muted-foreground mb-3">Matched vs unmatched results</p>
                <ResponsiveContainer width="100%" height={170}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={42}
                      outerRadius={65}
                      dataKey="value"
                      strokeWidth={2}
                    >
                      {pieData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Pie>
                    <ReTooltip
                      formatter={(value: number, name: string) => [value, name]}
                      contentStyle={{ fontSize: "12px", borderRadius: "6px" }}
                    />
                    <Legend iconSize={8} wrapperStyle={{ fontSize: "11px" }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Horizontal bar: score per result */}
              <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-4">
                <h3 className="text-sm font-semibold mb-1 text-card-foreground">Score Confidence</h3>
                <p className="text-xs text-muted-foreground mb-3">Per-result match score (0–1)</p>
                <ResponsiveContainer width="100%" height={Math.max(130, reconcileResults.length * 30)}>
                  <BarChart
                    layout="vertical"
                    data={barData}
                    margin={{ left: 0, right: 14, top: 2, bottom: 2 }}
                  >
                    <XAxis
                      type="number"
                      domain={[0, 1]}
                      tickCount={3}
                      tick={{ fontSize: 10 }}
                      tickFormatter={(v) => v.toFixed(1)}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={95}
                      tick={{ fontSize: 9 }}
                    />
                    <ReTooltip
                      formatter={(value: number) => [value.toFixed(4), "Score"]}
                      contentStyle={{ fontSize: "12px", borderRadius: "6px" }}
                    />
                    <Bar dataKey="score" radius={[0, 3, 3, 0]}>
                      {reconcileResults.map((r, i) => (
                        <Cell key={i} fill={scoreBarColor(r.score)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {activeTab === "suggest" && suggestResults.length > 0 && (
          <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
            <div className="p-6 pb-3">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Sparkles className="h-4 w-4" />
                Suggestions
                <span className="ml-1 inline-flex items-center rounded-full bg-secondary text-secondary-foreground px-2.5 py-0.5 text-xs font-semibold">
                  {suggestResults.length}
                </span>
              </h2>
            </div>
            <div className="p-0">
              <table className="w-full caption-bottom text-sm">
                <thead className="[&_tr]:border-b">
                  <tr className="border-b transition-colors hover:bg-muted/50">
                    <th className="h-12 px-4 pl-6 text-left align-middle font-medium text-muted-foreground">Name</th>
                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Score</th>
                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">ID</th>
                    <th className="h-12 px-4 w-[70px] align-middle font-medium text-muted-foreground"></th>
                  </tr>
                </thead>
                <tbody className="[&_tr:last-child]:border-0">
                  {suggestResults.map((s, idx) => (
                    <tr key={`${s.id}-${idx}`} data-testid={`row-suggest-${idx}`} className="border-b transition-colors hover:bg-muted/50">
                      <td className="p-4 pl-6 font-medium align-middle" data-testid={`text-suggest-name-${idx}`}>
                        <div className="flex items-center gap-2">
                          <GraduationCap className="h-4 w-4 text-muted-foreground shrink-0" />
                          {s.name}
                        </div>
                      </td>
                      <td className="p-4 align-middle" data-testid={`text-suggest-score-${idx}`}>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-sm font-mono font-medium ${scoreBg(s.score)} ${scoreColor(s.score)}`}>
                          {s.score.toFixed(4)}
                        </span>
                      </td>
                      <td className="p-4 align-middle font-mono text-xs text-muted-foreground" data-testid={`text-suggest-id-${idx}`}>
                        {s.id}
                      </td>
                      <td className="p-4 align-middle">
                        <button
                          onClick={() => handlePreview(s.id)}
                          data-testid={`button-suggest-preview-${idx}`}
                          className="inline-flex items-center justify-center rounded-md h-10 w-10 hover:bg-accent hover:text-accent-foreground"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {((activeTab === "reconcile" && reconcileResults.length === 0 && !loading) ||
          (activeTab === "suggest" && suggestResults.length === 0 && !suggestLoading)) &&
          !loading &&
          !suggestLoading && (
            <div className="rounded-lg border border-dashed bg-card text-card-foreground shadow-sm">
              <div className="flex flex-col items-center justify-center py-12 text-center p-6">
                <div className="rounded-full bg-muted p-4 mb-4">
                  <Search className="h-8 w-8 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground text-sm max-w-sm">
                  Enter an institution name and click <strong>Reconcile</strong> to find matches, or <strong>Suggest</strong> for autocomplete suggestions.
                </p>
              </div>
            </div>
          )}

        {(loading || suggestLoading) && (
          <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
            <div className="flex items-center justify-center py-12 p-6">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          </div>
        )}
      </div>

      {previewOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/80" onClick={() => setPreviewOpen(false)} />
          <div className="relative z-50 bg-background rounded-lg shadow-lg w-full max-w-md mx-4 p-6">
            <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
              <Eye className="h-5 w-5" />
              Entity Preview
            </h2>
            {previewLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : previewData ? (
              <div className="space-y-4">
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <GraduationCap className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                    <div>
                      <p className="text-xs text-muted-foreground">Institution</p>
                      <p className="font-medium" data-testid="text-preview-name">{previewData.name}</p>
                    </div>
                  </div>
                  <hr className="border-t" />
                  {previewData.country && (
                    <div className="flex items-start gap-3">
                      <Globe className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                      <div>
                        <p className="text-xs text-muted-foreground">Country</p>
                        <p className="font-medium" data-testid="text-preview-country">{previewData.country}</p>
                      </div>
                    </div>
                  )}
                  {previewData.rank != null && (
                    <>
                      <hr className="border-t" />
                      <div className="flex items-start gap-3">
                        <Award className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                        <div>
                          <p className="text-xs text-muted-foreground">Rank</p>
                          <p className="font-medium" data-testid="text-preview-rank">#{previewData.rank}</p>
                        </div>
                      </div>
                    </>
                  )}
                  {previewData.year != null && (
                    <>
                      <hr className="border-t" />
                      <div className="flex items-start gap-3">
                        <Calendar className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                        <div>
                          <p className="text-xs text-muted-foreground">Year</p>
                          <p className="font-medium" data-testid="text-preview-year">{previewData.year}</p>
                        </div>
                      </div>
                    </>
                  )}
                  {previewData.overall_score != null && (
                    <>
                      <hr className="border-t" />
                      <div className="flex items-start gap-3">
                        <Hash className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                        <div>
                          <p className="text-xs text-muted-foreground">Overall Score</p>
                          <p className="font-medium">{previewData.overall_score}</p>
                        </div>
                      </div>
                    </>
                  )}
                  {previewData.source && (
                    <>
                      <hr className="border-t" />
                      <div className="flex items-start gap-3">
                        <LinkIcon className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                        <div>
                          <p className="text-xs text-muted-foreground">Source</p>
                          <p className="font-medium text-sm">{previewData.source}</p>
                        </div>
                      </div>
                    </>
                  )}
                </div>
                <hr className="border-t" />
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Hash className="h-3 w-3" />
                  <span className="font-mono" data-testid="text-preview-id">{previewData.id}</span>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
