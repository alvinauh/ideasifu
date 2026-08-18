import { useNavigate } from "react-router-dom";
import { Trash2, ArrowRight, Sparkles, BookOpen } from "lucide-react";
import { store, useStore } from "@/lib/store";

export default function Library() {
  const navigate = useNavigate();
  const library = useStore((s) => s.library);

  function open(key: string) {
    const entry = store.openFromLibrary(key);
    if (entry) navigate("/idea");
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold sm:text-3xl">
          Your <span className="text-gradient">Library</span>
        </h1>
        <p className="mt-1 text-sm text-muted">
          A portfolio of your thinking — every idea you saved, ready to reopen.
        </p>
      </div>

      {library.length === 0 ? (
        <div className="grid place-items-center rounded-2xl border border-dashed border-border py-20 text-center">
          <BookOpen className="h-8 w-8 text-muted" aria-hidden />
          <p className="mt-3 text-sm text-muted">
            Nothing saved yet. Build an idea and hit "Save to Library".
          </p>
          <button
            onClick={() => navigate("/")}
            className="mt-4 flex items-center gap-2 rounded-xl bg-gradient-idea px-5 py-2.5 text-sm font-semibold text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <Sparkles className="h-4 w-4" aria-hidden />
            Start a new idea
          </button>
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {library.map((entry) => (
            <li
              key={entry.key}
              className="card-shadow flex flex-col rounded-2xl border border-border bg-surface p-5"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted">
                  University
                </span>
                <button
                  onClick={() => store.removeFromLibrary(entry.key)}
                  aria-label="Delete saved idea"
                  className="rounded-md p-1.5 text-muted transition-colors hover:text-[color:var(--color-danger)] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>

              <h2 className="mt-3 font-display text-lg font-semibold leading-snug">
                {entry.result.idea.title}
              </h2>
              <p className="mt-1 text-xs text-muted">{entry.brief.subject}</p>
              <p className="mt-2 line-clamp-3 text-sm text-muted">
                {entry.result.idea.statement}
              </p>

              <div className="mt-auto flex items-center justify-between pt-4 text-xs text-muted">
                <span>{new Date(entry.savedAt).toLocaleDateString()}</span>
                <button
                  onClick={() => open(entry.key)}
                  className="flex items-center gap-1.5 rounded-lg border border-primary bg-primary/15 px-3 py-1.5 font-medium text-foreground transition-colors hover:bg-primary/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                  Reopen
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
