import { useState } from "react";
import { Loader2, Search, Database, ExternalLink } from "lucide-react";
import * as api from "@/lib/api";
import { USING_MOCK } from "@/lib/api";
import type { CorpusHit } from "@/lib/types";

// A few ready-to-run examples so the tab isn't a blank box.
const EXAMPLES = [
  "Mathematics learning tool kit for dyscalculia and dyslexia",
  "Kit pembelajaran matematik untuk murid berkeperluan khas (MBPK)",
  "Usability of a mathematics courseware for special education needs",
];

/** Colour the score chip: green (strong) -> amber -> muted. */
function scoreTone(score: number): string {
  if (score >= 0.7) return "text-emerald-600 border-emerald-500/30 bg-emerald-500/10";
  if (score >= 0.6) return "text-amber-600 border-amber-500/30 bg-amber-500/10";
  return "text-muted border-border bg-surface";
}

export default function Corpus() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<CorpusHit[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState("");

  async function run(q: string) {
    const term = q.trim();
    if (!term || loading) return;
    setLoading(true);
    setError(null);
    setLastQuery(term);
    try {
      const res = await api.searchCorpus(term, 25);
      if (res.status !== "ok") {
        setError(res.message ?? "Search failed.");
        setResults([]);
      } else {
        setResults(res.results);
      }
    } catch (e) {
      setError(`Search failed: ${e instanceof Error ? e.message : "unknown error"}`);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    run(query);
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <div className="mb-6">
        <p className="flex items-center gap-2 text-sm text-muted">
          <Database className="h-4 w-4" aria-hidden />
          Academic corpus search
        </p>
        <h1 className="mt-1 font-display text-2xl font-semibold sm:text-3xl">
          Search the <span className="text-gradient">ThesisSifu corpus</span>
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          Semantic search over ~7.1 million academic papers (OpenAlex), embedded
          with the multilingual bge-m3 model — so it matches by meaning, not just
          keywords. Works across languages (English, Bahasa Melayu, and more).
          Each result links to its OpenAlex page for full metadata.
        </p>
      </div>

      <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
            aria-hidden
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. mathematics learning tool for dyscalculia"
            aria-label="Corpus search query"
            className="w-full rounded-xl border border-border bg-surface py-3 pl-9 pr-3 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-primary"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="flex items-center justify-center gap-2 rounded-xl bg-gradient-idea px-5 py-3 text-sm font-medium text-white transition-opacity hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <Search className="h-4 w-4" aria-hidden />
          )}
          Search
        </button>
      </form>

      {/* Example chips */}
      {results === null && !loading && (
        <div className="mt-5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            Try one of these
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => {
                  setQuery(ex);
                  run(ex);
                }}
                className="rounded-full border border-border px-3 py-1.5 text-xs text-muted transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                {ex}
              </button>
            ))}
          </div>
          {USING_MOCK && (
            <p className="mt-4 text-xs text-muted">
              Demo mode — showing placeholder results. Connect the backend for
              live corpus search.
            </p>
          )}
        </div>
      )}

      {/* Results */}
      <section aria-live="polite" className="mt-6">
        {loading && (
          <div className="grid min-h-[200px] place-items-center rounded-2xl border border-dashed border-border">
            <div className="text-center">
              <Loader2 className="mx-auto h-7 w-7 animate-spin text-primary" aria-hidden />
              <p className="mt-3 text-sm text-muted">
                Embedding your query and searching 7.1M papers…
              </p>
            </div>
          </div>
        )}

        {!loading && error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-600">
            {error}
          </div>
        )}

        {!loading && !error && results && (
          <>
            <p className="mb-3 text-sm text-muted">
              {results.length > 0
                ? `${results.length} result${results.length === 1 ? "" : "s"} for `
                : "No results for "}
              <span className="font-medium text-foreground">"{lastQuery}"</span>
            </p>
            <ol className="space-y-2.5">
              {results.map((hit, i) => (
                <li
                  key={`${hit.openalex_id ?? "na"}-${i}`}
                  className="card-shadow rounded-xl border border-border bg-surface p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium leading-snug">
                        {hit.title}
                      </p>
                      {hit.openalex_id && (
                        <a
                          href={hit.openalex_id}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1.5 inline-flex items-center gap-1 text-xs text-primary hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                        >
                          <ExternalLink className="h-3 w-3" aria-hidden />
                          View on OpenAlex
                        </a>
                      )}
                    </div>
                    <span
                      title="Semantic similarity (cosine)"
                      className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium tabular-nums ${scoreTone(
                        hit.score,
                      )}`}
                    >
                      {(hit.score * 100).toFixed(0)}%
                    </span>
                  </div>
                </li>
              ))}
            </ol>
            <p className="mt-4 text-xs text-muted">
              Note: the corpus stores each paper's title + OpenAlex ID only. Open
              a result on OpenAlex for authors, year, abstract, and PDF links.
            </p>
          </>
        )}
      </section>
    </main>
  );
}
