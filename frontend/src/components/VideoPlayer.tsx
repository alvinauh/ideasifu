import { useEffect, useRef, useState } from "react";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  RotateCcw,
  Film,
  Clapperboard,
} from "lucide-react";
import type { VideoSummary } from "@/lib/types";

/** A "player" mock that steps through scenes with narration as captions,
 * the scene visual description, and a progress bar. Storyboard listed below. */
export default function VideoPlayer({ video }: { video: VideoSummary }) {
  const [scene, setScene] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [elapsedInScene, setElapsedInScene] = useState(0);
  const rafRef = useRef<number | null>(null);
  const lastTs = useRef<number | null>(null);

  const scenes = video.scenes;
  const current = scenes[scene];

  // Cumulative seconds before the current scene, for the global progress bar.
  const before = scenes.slice(0, scene).reduce((a, s) => a + s.seconds, 0);
  const globalElapsed = before + elapsedInScene;

  useEffect(() => {
    if (!playing) {
      lastTs.current = null;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      return;
    }
    function tick(ts: number) {
      if (lastTs.current == null) lastTs.current = ts;
      const dt = (ts - lastTs.current) / 1000;
      lastTs.current = ts;
      setElapsedInScene((prev) => {
        const next = prev + dt;
        if (next >= current.seconds) {
          // advance
          if (scene < scenes.length - 1) {
            setScene((s) => s + 1);
            return 0;
          }
          setPlaying(false);
          return current.seconds;
        }
        return next;
      });
      rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [playing, scene, current.seconds, scenes.length]);

  function go(to: number) {
    setScene(Math.max(0, Math.min(scenes.length - 1, to)));
    setElapsedInScene(0);
    lastTs.current = null;
  }
  function restart() {
    setScene(0);
    setElapsedInScene(0);
    setPlaying(true);
  }

  const globalPct = (globalElapsed / video.total_seconds) * 100;
  const finished = scene === scenes.length - 1 && elapsedInScene >= current.seconds;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div>
        {/* Stage */}
        <div className="card-shadow relative aspect-video overflow-hidden rounded-2xl border border-border bg-surface-2">
          <div
            aria-hidden
            className="absolute inset-0 opacity-40"
            style={{ background: "var(--gradient-glow)" }}
          />
          <div className="absolute left-4 top-4 flex items-center gap-2 text-xs text-muted">
            <span
              className="grid h-7 w-7 place-items-center rounded-lg"
              style={{
                color: "var(--color-director)",
                backgroundColor: "color-mix(in oklab, currentColor 18%, transparent)",
              }}
            >
              <Clapperboard className="h-4 w-4" aria-hidden />
            </span>
            Scene {current.n} of {scenes.length}
          </div>

          {/* Visual description */}
          <div className="absolute inset-0 grid place-items-center p-8 text-center">
            <div>
              <Film className="mx-auto h-8 w-8 text-muted" aria-hidden />
              <p className="mt-3 max-w-md text-sm italic text-muted">
                {current.visual}
              </p>
            </div>
          </div>

          {/* Caption */}
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-4 pt-10">
            <p
              aria-live="polite"
              className="mx-auto max-w-xl text-center text-sm font-medium leading-relaxed text-white"
            >
              {current.narration}
            </p>
          </div>
        </div>

        {/* Progress */}
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
          <div
            className="h-full bg-gradient-idea transition-[width] duration-150"
            style={{ width: `${Math.min(100, globalPct)}%` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted">
          <span>{Math.round(globalElapsed)}s</span>
          <span>{video.total_seconds}s total</span>
        </div>

        {/* Controls */}
        <div className="mt-4 flex items-center justify-center gap-3">
          <button
            onClick={() => go(scene - 1)}
            disabled={scene === 0}
            aria-label="Previous scene"
            className="rounded-full border border-border p-2.5 text-muted transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-40"
          >
            <SkipBack className="h-4 w-4" />
          </button>

          {finished ? (
            <button
              onClick={restart}
              aria-label="Replay"
              className="flex items-center gap-2 rounded-full bg-gradient-idea px-6 py-3 font-semibold text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              <RotateCcw className="h-5 w-5" />
              Replay
            </button>
          ) : (
            <button
              onClick={() => setPlaying((p) => !p)}
              aria-label={playing ? "Pause" : "Play"}
              className="flex items-center gap-2 rounded-full bg-gradient-idea px-6 py-3 font-semibold text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              {playing ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
              {playing ? "Pause" : "Play"}
            </button>
          )}

          <button
            onClick={() => go(scene + 1)}
            disabled={scene === scenes.length - 1}
            aria-label="Next scene"
            className="rounded-full border border-border p-2.5 text-muted transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-40"
          >
            <SkipForward className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Storyboard */}
      <aside>
        <h3 className="mb-2 font-display text-sm font-medium uppercase tracking-wider text-muted">
          Storyboard
        </h3>
        <p className="mb-3 text-xs text-muted">{video.hook}</p>
        <ol className="space-y-2">
          {scenes.map((s, i) => (
            <li key={s.n}>
              <button
                onClick={() => go(i)}
                className={`w-full rounded-xl border p-3 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                  i === scene
                    ? "border-[color:var(--color-director)] bg-surface"
                    : "border-border bg-surface hover:bg-surface-2"
                }`}
              >
                <div className="flex items-center justify-between text-xs text-muted">
                  <span className="font-medium">Scene {s.n}</span>
                  <span>{s.seconds}s</span>
                </div>
                <p className="mt-1 text-xs italic text-muted">{s.visual}</p>
                <p className="mt-1.5 text-sm leading-snug">{s.narration}</p>
              </button>
            </li>
          ))}
        </ol>
      </aside>
    </div>
  );
}
