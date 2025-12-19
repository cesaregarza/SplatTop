import React, { useRef } from "react";
import { Link } from "react-router-dom";
import "./CompetitionViz.css";
import { useCompetitionVizSimulation } from "./useCompetitionVizSimulation";

const SCENE_DATA = {
  nodes: [
    { id: 0, label: "P0 (Skill 0.22)" },
    { id: 1, label: "P1 (Skill 0.77)" },
    { id: 2, label: "P2 (Skill 0.80)" },
    { id: 3, label: "P3 (Skill 0.84)" },
    { id: 4, label: "P4 (Skill 0.87)" },
    { id: 5, label: "P5 (Skill 0.88)" },
    { id: 6, label: "P6 (Skill 0.89)" },
    { id: 7, label: "P7 (Skill 1.12)" },
    { id: 8, label: "P8 (Skill 1.26)" },
    { id: 9, label: "P9 (Skill 1.39)" },
    { id: 10, label: "P10 (Skill 1.93)" },
    { id: 11, label: "P11 (Skill 2.02)" },
    { id: 12, label: "P12 (Skill 3.20)" },
  ],
  links: [
    { source: 0, target: 1, weight: 1 },
    { source: 0, target: 4, weight: 1 },
    { source: 0, target: 5, weight: 1 },
    { source: 0, target: 6, weight: 1 },
    { source: 0, target: 7, weight: 1 },
    { source: 0, target: 8, weight: 1 },
    { source: 0, target: 9, weight: 1 },
    { source: 1, target: 0, weight: 4 },
    { source: 1, target: 2, weight: 2 },
    { source: 1, target: 3, weight: 3 },
    { source: 1, target: 4, weight: 1 },
    { source: 1, target: 5, weight: 2 },
    { source: 1, target: 7, weight: 4 },
    { source: 1, target: 8, weight: 1 },
    { source: 1, target: 9, weight: 2 },
    { source: 1, target: 10, weight: 2 },
    { source: 1, target: 12, weight: 1 },
    { source: 2, target: 0, weight: 5 },
    { source: 2, target: 1, weight: 1 },
    { source: 2, target: 3, weight: 1 },
    { source: 2, target: 4, weight: 3 },
    { source: 2, target: 5, weight: 3 },
    { source: 2, target: 6, weight: 4 },
    { source: 2, target: 7, weight: 4 },
    { source: 2, target: 8, weight: 1 },
    { source: 2, target: 9, weight: 3 },
    { source: 2, target: 10, weight: 1 },
    { source: 2, target: 12, weight: 2 },
    { source: 3, target: 0, weight: 1 },
    { source: 3, target: 1, weight: 3 },
    { source: 3, target: 2, weight: 3 },
    { source: 3, target: 4, weight: 1 },
    { source: 3, target: 5, weight: 1 },
    { source: 3, target: 6, weight: 4 },
    { source: 3, target: 7, weight: 4 },
    { source: 3, target: 8, weight: 3 },
    { source: 3, target: 9, weight: 3 },
    { source: 3, target: 10, weight: 2 },
    { source: 3, target: 11, weight: 2 },
    { source: 3, target: 12, weight: 2 },
    { source: 4, target: 0, weight: 2 },
    { source: 4, target: 1, weight: 3 },
    { source: 4, target: 2, weight: 5 },
    { source: 4, target: 3, weight: 2 },
    { source: 4, target: 5, weight: 1 },
    { source: 4, target: 6, weight: 4 },
    { source: 4, target: 7, weight: 5 },
    { source: 4, target: 9, weight: 1 },
    { source: 4, target: 10, weight: 3 },
    { source: 4, target: 11, weight: 1 },
    { source: 5, target: 0, weight: 4 },
    { source: 5, target: 1, weight: 5 },
    { source: 5, target: 2, weight: 2 },
    { source: 5, target: 4, weight: 1 },
    { source: 5, target: 6, weight: 1 },
    { source: 5, target: 7, weight: 3 },
    { source: 5, target: 8, weight: 4 },
    { source: 5, target: 9, weight: 2 },
    { source: 5, target: 10, weight: 2 },
    { source: 5, target: 11, weight: 4 },
    { source: 5, target: 12, weight: 1 },
    { source: 6, target: 0, weight: 2 },
    { source: 6, target: 1, weight: 1 },
    { source: 6, target: 3, weight: 4 },
    { source: 6, target: 4, weight: 1 },
    { source: 6, target: 5, weight: 4 },
    { source: 6, target: 7, weight: 1 },
    { source: 6, target: 8, weight: 2 },
    { source: 6, target: 9, weight: 4 },
    { source: 6, target: 10, weight: 1 },
    { source: 6, target: 11, weight: 2 },
    { source: 6, target: 12, weight: 1 },
    { source: 7, target: 0, weight: 7 },
    { source: 7, target: 1, weight: 2 },
    { source: 7, target: 2, weight: 2 },
    { source: 7, target: 4, weight: 2 },
    { source: 7, target: 5, weight: 2 },
    { source: 7, target: 6, weight: 4 },
    { source: 7, target: 8, weight: 3 },
    { source: 7, target: 9, weight: 4 },
    { source: 7, target: 10, weight: 1 },
    { source: 7, target: 11, weight: 4 },
    { source: 7, target: 12, weight: 2 },
    { source: 8, target: 2, weight: 1 },
    { source: 8, target: 3, weight: 4 },
    { source: 8, target: 4, weight: 4 },
    { source: 8, target: 5, weight: 2 },
    { source: 8, target: 6, weight: 5 },
    { source: 8, target: 7, weight: 2 },
    { source: 8, target: 9, weight: 2 },
    { source: 8, target: 10, weight: 5 },
    { source: 8, target: 11, weight: 1 },
    { source: 8, target: 12, weight: 2 },
    { source: 9, target: 0, weight: 2 },
    { source: 9, target: 1, weight: 7 },
    { source: 9, target: 2, weight: 3 },
    { source: 9, target: 3, weight: 5 },
    { source: 9, target: 4, weight: 4 },
    { source: 9, target: 5, weight: 4 },
    { source: 9, target: 7, weight: 2 },
    { source: 9, target: 8, weight: 4 },
    { source: 9, target: 10, weight: 1 },
    { source: 9, target: 12, weight: 2 },
    { source: 10, target: 0, weight: 2 },
    { source: 10, target: 1, weight: 6 },
    { source: 10, target: 2, weight: 4 },
    { source: 10, target: 3, weight: 4 },
    { source: 10, target: 4, weight: 5 },
    { source: 10, target: 5, weight: 6 },
    { source: 10, target: 6, weight: 4 },
    { source: 10, target: 7, weight: 3 },
    { source: 10, target: 9, weight: 4 },
    { source: 10, target: 11, weight: 5 },
    { source: 10, target: 12, weight: 4 },
    { source: 11, target: 0, weight: 4 },
    { source: 11, target: 1, weight: 3 },
    { source: 11, target: 2, weight: 8 },
    { source: 11, target: 3, weight: 6 },
    { source: 11, target: 4, weight: 9 },
    { source: 11, target: 5, weight: 5 },
    { source: 11, target: 6, weight: 5 },
    { source: 11, target: 8, weight: 10 },
    { source: 11, target: 9, weight: 3 },
    { source: 11, target: 10, weight: 4 },
    { source: 11, target: 12, weight: 5 },
    { source: 12, target: 0, weight: 3 },
    { source: 12, target: 1, weight: 4 },
    { source: 12, target: 2, weight: 6 },
    { source: 12, target: 3, weight: 5 },
    { source: 12, target: 4, weight: 4 },
    { source: 12, target: 5, weight: 5 },
    { source: 12, target: 6, weight: 4 },
    { source: 12, target: 7, weight: 5 },
    { source: 12, target: 8, weight: 7 },
    { source: 12, target: 9, weight: 7 },
    { source: 12, target: 10, weight: 7 },
    { source: 12, target: 11, weight: 14 },
  ],
};

const CompetitionViz = () => {
  const rootRef = useRef(null);
  const canvasRef = useRef(null);
  const canvasContainerRef = useRef(null);
  const scatterCanvasRef = useRef(null);
  const barCanvasRef = useRef(null);
  const convergenceCanvasRef = useRef(null);
  const btnStepRef = useRef(null);
  const btnAutoRef = useRef(null);
  const btnResetRef = useRef(null);
  const btnExportRef = useRef(null);
  const speedSliderRef = useRef(null);
  const speedValueRef = useRef(null);
  const iterCountRef = useRef(null);
  const statusTextRef = useRef(null);
  const deltaValueRef = useRef(null);
  const deltaBarRef = useRef(null);
  const insightTextRef = useRef(null);
  const correlationValueRef = useRef(null);
  const nodeCountRef = useRef(null);
  const edgeCountRef = useRef(null);
  const dampingValueRef = useRef(null);
  const thresholdValueRef = useRef(null);
  const leaderNameRef = useRef(null);
  const leaderScoreRef = useRef(null);
  const leaderSkillRef = useRef(null);
  const leaderWinsRef = useRef(null);
  const leaderOppRef = useRef(null);

  const { unsupported, controls } = useCompetitionVizSimulation({
    sceneData: SCENE_DATA,
    rootRef,
    canvasRef,
    canvasContainerRef,
    scatterCanvasRef,
    barCanvasRef,
    convergenceCanvasRef,
    btnStepRef,
    btnAutoRef,
    btnResetRef,
    btnExportRef,
    speedSliderRef,
    speedValueRef,
    iterCountRef,
    statusTextRef,
    deltaValueRef,
    deltaBarRef,
    insightTextRef,
    correlationValueRef,
    nodeCountRef,
    edgeCountRef,
    dampingValueRef,
    thresholdValueRef,
    leaderNameRef,
    leaderScoreRef,
    leaderSkillRef,
    leaderWinsRef,
    leaderOppRef,
  });

  return (
    unsupported ? (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center px-6">
        <div className="max-w-lg text-center space-y-3">
          <h1 className="text-2xl font-semibold">Interactive explainer unavailable</h1>
          <p className="text-[#8b949e]">
            {unsupported} Please try a recent version of Chrome, Edge, or Firefox, or view the leaderboard
            instead.
          </p>
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-full bg-white/[0.03] px-4 py-2 text-sm font-semibold text-[#c9d1d9] border border-white/10 hover:bg-white/[0.06] transition"
          >
            Back to leaderboard
          </Link>
        </div>
      </div>
    ) : (
      <div
        ref={rootRef}
        className="comp-viz relative min-h-screen bg-slate-950 text-slate-100 overflow-x-hidden"
        style={{ colorScheme: "dark" }}
      >
        <a
          href="#controls"
          className="comp-viz__skip sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50"
        >
          Skip to controls
        </a>

        <div className="relative z-10">
          <header className="px-4 sm:px-6 pt-6">
            <div className="max-w-6xl mx-auto">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <Link
                    to="/"
                    className="rounded-full bg-white/[0.03] px-3 py-1.5 text-xs font-semibold tracking-wide text-[#c9d1d9] border border-white/10 hover:bg-white/[0.06]"
                  >
                    Back to leaderboard
                  </Link>
                  <span className="text-xs text-[#8b949e]">Ranking Simulator</span>
                </div>
              </div>

              <div className="mt-6">
                <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">Ranking Simulator</h1>
                <p className="mt-3 max-w-2xl text-[#8b949e]">
                  An explorable view of the competitive ranking engine. Scores flow from losers to winners,
                  amplifying victories over strong opponents while dampening farmed wins.
                </p>
              </div>
            </div>
          </header>

          <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-6 pb-16 space-y-6">
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(320px,1fr)] items-start">
              <section className="space-y-4">
                <div className="comp-viz__panel comp-viz__panel--accent pointer-events-auto p-6">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <h2 className="text-lg font-semibold text-white">Influence Graph</h2>
                      <p className="text-sm text-[#8b949e]">
                        Watch score flow across recent matchups as PageRank iterates.
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-xs text-[#8b949e] min-w-[240px]">
                      <div className="flex items-center justify-between">
                        <span>Players</span>
                        <span ref={nodeCountRef} id="nodeCount" className="font-data text-sm text-white">
                          -
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Matchups</span>
                        <span ref={edgeCountRef} id="edgeCount" className="font-data text-sm text-white">
                          -
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Damping</span>
                        <span ref={dampingValueRef} id="dampingValue" className="font-data text-sm text-white">
                          -
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Threshold</span>
                        <span
                          ref={thresholdValueRef}
                          id="thresholdValue"
                          className="font-data text-sm text-white"
                        >
                          -
                        </span>
                      </div>
                    </div>
                  </div>

                  <div
                    ref={canvasContainerRef}
                    className="comp-viz__canvas-shell mt-4"
                    role="img"
                    aria-label="Ranking graph simulation"
                  >
                    <canvas
                      ref={canvasRef}
                      id="simCanvas"
                      className="comp-viz__canvas"
                      onMouseMove={controls.onCanvasMouseMove}
                      onMouseDown={controls.onCanvasMouseDown}
                      onMouseUp={controls.onCanvasMouseUp}
                      onMouseLeave={controls.onCanvasMouseLeave}
                    />
                    <p className="sr-only">
                      Interactive graph showing players as nodes with edges representing wins. Use S to step,
                      A to auto-run, R to reset, and E to export. Drag nodes to reposition them.
                    </p>
                    <div className="comp-viz__canvas-hint">
                      Drag nodes and hover edges
                      <span>Step / Auto to iterate</span>
                    </div>
                  </div>
                </div>
              </section>

              <aside className="space-y-4" id="controls">
                <div className="comp-viz__panel comp-viz__panel--accent pointer-events-auto p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-lg font-semibold text-white">
                        Controls <span className="text-fuchsia-300 font-light">/</span>
                      </h2>
                      <p className="text-[11px] text-[#8b949e]">
                        Step through the ranking loop or auto-run to convergence.
                      </p>
                    </div>
                    <div className="flex items-center gap-1 text-[11px] text-[#8b949e]">
                      <span className="rounded bg-slate-800/80 px-2 py-1">S</span>
                      <span className="rounded bg-slate-800/80 px-2 py-1">A</span>
                      <span className="rounded bg-slate-800/80 px-2 py-1">R</span>
                      <span className="rounded bg-slate-800/80 px-2 py-1">E</span>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2">
                    <button
                      ref={btnStepRef}
                      id="btnStep"
                      className="comp-viz__button comp-viz__button--primary"
                      aria-keyshortcuts="S Space"
                      aria-label="Step forward one iteration (S or Space)"
                      onClick={controls.onStepClick}
                    >
                      Step
                    </button>
                    <button
                      ref={btnAutoRef}
                      id="btnAuto"
                      className="comp-viz__button comp-viz__button--secondary comp-viz__button--auto"
                      aria-keyshortcuts="A"
                      aria-label="Toggle auto run (A)"
                      onClick={controls.onAutoClick}
                    >
                      Auto
                    </button>
                  </div>

                  <div className="mt-4">
                    <div className="flex items-center justify-between text-[10px] text-[#8b949e] uppercase tracking-widest">
                      <label htmlFor="speedSlider">Speed</label>
                      <span ref={speedValueRef} id="speedValue" className="font-data text-slate-200">
                        2x
                      </span>
                    </div>
                    <input
                      ref={speedSliderRef}
                      type="range"
                      id="speedSlider"
                      min="0.5"
                      max="4"
                      step="0.5"
                      defaultValue="2"
                      className="comp-viz__slider mt-3"
                      aria-label="Animation speed"
                      onChange={controls.onSpeedInput}
                    />
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2">
                    <button
                      ref={btnResetRef}
                      id="btnReset"
                      className="comp-viz__button comp-viz__button--ghost"
                      aria-keyshortcuts="R"
                      aria-label="Reset simulation (R)"
                      onClick={controls.onResetClick}
                    >
                      Reset
                    </button>
                    <button
                      ref={btnExportRef}
                      id="btnExport"
                      className="comp-viz__button comp-viz__button--ghost"
                      aria-keyshortcuts="E"
                      aria-label="Export rankings as CSV (E)"
                      onClick={controls.onExportClick}
                    >
                      Export
                    </button>
                  </div>

                  <div className="mt-4 border-t border-white/10 pt-4 text-[11px] text-[#8b949e]">
                    Wins against strong opponents send more score. The loop repeats until the graph stabilizes.
                  </div>
                </div>

                <div className="comp-viz__panel pointer-events-auto p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-semibold uppercase tracking-widest text-[#8b949e]">
                        Simulation State
                      </h3>
                      <div
                        ref={iterCountRef}
                        className="mt-1 text-2xl font-semibold text-white font-data"
                        id="iterCount"
                      >
                        0
                      </div>
                    </div>
                    <div>
                      <span
                        ref={statusTextRef}
                        id="statusText"
                        className="inline-flex items-center leading-none text-[11px] font-semibold text-[#22d3d3] bg-[#22d3d3]/15 px-3 py-1.5 rounded-full border border-[#22d3d3]/25"
                      >
                        Ready
                      </span>
                    </div>
                  </div>

                  <div className="mt-4">
                    <div className="flex items-center justify-between text-[10px] uppercase tracking-widest text-[#8b949e]">
                      <span>Convergence</span>
                      <span ref={deltaValueRef} id="deltaValue" className="font-data text-slate-200">
                        -
                      </span>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-white/5 overflow-hidden">
                      <div
                        ref={deltaBarRef}
                        id="deltaBar"
                        className="h-full w-full bg-gradient-to-r from-fuchsia-500/80 to-fuchsia-600/80 transition-all duration-300"
                      />
                    </div>
                  </div>
                </div>

                <div className="comp-viz__panel pointer-events-auto p-6">
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-[#8b949e]">
                    Convergence History
                  </h3>
                  <canvas ref={convergenceCanvasRef} id="convergenceCanvas" className="mt-3 h-16 w-full" />
                </div>

                <div className="comp-viz__panel pointer-events-auto p-6">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold uppercase tracking-widest text-[#8b949e]">
                      Insight
                    </h3>
                    <span className="text-[10px] text-[#8b949e]">Realtime</span>
                  </div>
                  <p ref={insightTextRef} id="insightText" className="mt-3 text-sm text-[#c9d1d9] leading-relaxed">
                    Tap Step or Auto Run to begin. Watch how scores flow from losers to winners.
                  </p>
                </div>

                <div className="comp-viz__panel pointer-events-auto p-6">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold uppercase tracking-widest text-[#8b949e]">
                      Current Leader
                    </h3>
                    <span className="text-[10px] text-fuchsia-200/70">Top Rank</span>
                  </div>
                  <div className="mt-2">
                    <div ref={leaderNameRef} id="leaderName" className="text-xl font-semibold text-white">
                      -
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-3 text-[11px] text-[#8b949e]">
                      <div>
                        Score{" "}
                        <span ref={leaderScoreRef} id="leaderScore" className="font-data text-slate-100">
                          -
                        </span>
                      </div>
                      <div>
                        Skill{" "}
                        <span ref={leaderSkillRef} id="leaderSkill" className="font-data text-slate-100">
                          -
                        </span>
                      </div>
                      <div>
                        Wins{" "}
                        <span ref={leaderWinsRef} id="leaderWins" className="font-data text-slate-100">
                          -
                        </span>
                      </div>
                      <div>
                        Avg Opp{" "}
                        <span ref={leaderOppRef} id="leaderOpp" className="font-data text-slate-100">
                          -
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="comp-viz__panel pointer-events-auto p-6">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold uppercase tracking-widest text-[#8b949e]">
                      Interaction Guide
                    </h3>
                  </div>
                  <div className="mt-2 grid gap-2 text-[11px] text-[#8b949e]">
                    <div className="flex items-center justify-between">
                      <span>Drag nodes to reposition the graph</span>
                      <span className="text-slate-200">Mouse</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Hover nodes to highlight influence</span>
                      <span className="text-slate-200">Hover</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Export the current ranking snapshot</span>
                      <span className="text-slate-200">E key</span>
                    </div>
                  </div>
                </div>
              </aside>
            </div>

            <div>
              <div className="comp-viz__panel pointer-events-auto grid gap-6 lg:grid-cols-2 p-6">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xs font-semibold uppercase tracking-widest text-[#8b949e]">
                      Skill vs Score
                    </h3>
                    <span
                      ref={correlationValueRef}
                      id="correlationValue"
                      className="font-data text-fuchsia-300 text-xs"
                    >
                      r = -
                    </span>
                  </div>
                  <canvas ref={scatterCanvasRef} id="scatterCanvas" className="h-36 w-full" />
                  <div className="mt-2 text-[10px] text-[#8b949e]">True Skill -&gt;</div>
                </div>

                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-[#8b949e] mb-3">
                    Score Ranking
                  </h3>
                  <canvas ref={barCanvasRef} id="barCanvas" className="h-36 w-full" />
                  <div className="mt-2 text-[10px] text-[#8b949e]">Top 12 by score</div>
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    )
  );
};

export default CompetitionViz;
