import React, { useMemo, useRef, useState } from "react";
import "./StableLeaderboardView.css";
import {
  CRACKLE_PURPLE,
  DISPLAY_GRADE_SCALE,
  gradeChipClass,
  isXX,
  rateFor,
} from "./stableLeaderboardUtils";
import useCrackleEffect from "../../hooks/useCrackleEffect";

const gradeBreakpoints = DISPLAY_GRADE_SCALE.filter(
  ([, label]) => label !== "XX★"
).map(([ceilingDisplay, label], index, array) => ({
  label,
  ceilingDisplay,
  floorDisplay: index === 0 ? null : array[index - 1][0],
}));

const formatThreshold = (value) => {
  if (value == null) return "—";
  if (!Number.isFinite(value)) return "∞";
  if (Number.isInteger(value)) return value;
  const rounded = Number.parseFloat(value.toFixed(1));
  return Number.isInteger(rounded) ? rounded : rounded.toFixed(1);
};

const formatTimestamp = (ms) => {
  if (!ms) return null;
  const date = new Date(ms);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString();
};

const CompetitionFaq = ({ percentiles }) => {
  const [showExtendedVersion, setShowExtendedVersion] = useState(false);
  const [showNerdVersion, setShowNerdVersion] = useState(false);
  const [showGradeNerdVersion, setShowGradeNerdVersion] = useState(false);
  const rootRef = useRef(null);

  useCrackleEffect(rootRef, [showGradeNerdVersion]);

  const gradeThresholds = percentiles?.grade_thresholds;
  const gradeStatsByLabel = useMemo(() => {
    const map = new Map();
    const entries = Array.isArray(gradeThresholds) ? gradeThresholds : [];
    entries.forEach((entry) => {
      if (entry && entry.label) {
        map.set(entry.label, entry);
      }
    });
    return map;
  }, [gradeThresholds]);

  const scorePopulation = percentiles?.score_population ?? null;
  const percentilesStale = Boolean(percentiles?.stale);
  const percentilesRetrievedAt = percentiles?.retrieved_at_ms
    ? formatTimestamp(percentiles.retrieved_at_ms)
    : null;

  const faqs = [
    {
      question: "What are these rankings?",
      answer: (
        <p>
          This is a player leaderboard built from sendou.ink tournament data.
          It reflects performance in RANKED, finalized events and tracks players
          individually (not fixed teams), so switching rosters between events is
          fine; your personal results follow you.
        </p>
      ),
    },
    {
      question: "How is the score calculated?",
      answer: (
        <div className="space-y-3">
          <p>
            Beating strong opponents at tougher tournaments helps the most. The
            system compares who you beat and who beat you across the entire
            scene and turns that into a single number. It's designed to reward
            quality wins without letting raw volume or grinding inflate scores.
          </p>
          <button
            type="button"
            className="block rounded-md border border-blue-500/40 bg-blue-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-200 hover:bg-blue-500/20"
            onClick={() => setShowExtendedVersion((value) => !value)}
          >
            {showExtendedVersion ? "Hide Extended Version" : "Show Extended Version"}
          </button>
          {showExtendedVersion && (
            <div className="rounded-md border border-blue-500/30 bg-slate-900/70 p-4 text-sm text-blue-100 space-y-3">
              <p>
                Strength of opposition matters. Beating high-performing players
                at stronger events boosts your score more than routine wins
                against mid-tier opposition. Losses to much lower-rated players
                sting more than expected losses to favorites.
              </p>
              <p>
                Results are reinterpreted as the field evolves. If a "new"
                player turns out to be elite, the system later treats earlier
                losses to them as less damaging because it learned they're
                strong. Scores are frozen after each player's most recent
                eligible tournament; we surface the next update the moment that
                player records another eligible result.
              </p>
            </div>
          )}
          <button
            type="button"
            className="block rounded-md border border-fuchsia-500/40 bg-fuchsia-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-fuchsia-200 hover:bg-fuchsia-500/20"
            onClick={() => setShowNerdVersion((value) => !value)}
          >
            {showNerdVersion ? "Hide Nerd Version" : "Show Nerd Version"}
          </button>
          {showNerdVersion && (
            <div className="rounded-md border border-fuchsia-500/30 bg-slate-900/70 p-4 text-sm text-fuchsia-100 space-y-3">
              <ol className="list-decimal space-y-2 pl-5 text-fuchsia-100/90">
                <li>
                  Run a tick-tock loop to estimate per-tournament influence
                  <code className="mx-1">S</code> from the participants'
                  current ratings. Production uses
                  <code className="mx-1">log_top_20_sum</code> and mean-normalizes
                  <code className="mx-1">S</code> to 1.0.
                </li>
                <li>
                  Convert every ranked set into player-level winner-&gt;loser pairs
                  with weights
                  <code className="mx-1">w = exp(-decay_rate * delta_days) * S^beta</code>.
                  Production runs with <code className="mx-1">beta = 1</code> and a
                  half-life of roughly 180 days.
                </li>
                <li>
                  Build a directed player graph and run PageRank in both
                  directions using the same teleport vector
                  <code className="mx-1">rho</code>, where
                  <code className="mx-1">rho_i proportional to exposure_i</code>
                  (share of weighted match participation).
                </li>
                <li>
                  Compute <code className="mx-1">PR_win</code> on the winner graph
                  and <code className="mx-1">PR_loss</code> on the mirrored loss
                  graph with damping <code className="mx-1">alpha ~ 0.85</code>.
                  Apply lambda smoothing with
                  <code className="mx-1">lambda ~ 0.025 * median(PR) / median(rho)</code>
                  and publish the raw score
                  <code className="mx-1">s_i = log((PR_win_i + lambda * rho_i)/(PR_loss_i + lambda * rho_i))</code>.
                </li>
              </ol>
              <p>
                Long-gap inactivity decay is available (delay ~ 180 days with a
                small daily rate). The raw log-odds output is then converted to
                display units via <code className="mx-1">display = 150 + 25 * raw</code>
                (multiply by 25, then add 150) and frozen until you appear in another
                eligible tournament.
              </p>
            </div>
          )}
        </div>
      ),
    },
    {
      question: "When does the leaderboard refresh?",
      answer: (
        <p>
          Rankings are recomputed daily from finalized sendou.ink data at 12:15 UTC
          (07:15 Eastern during standard time, 08:15 Eastern during daylight time).
          Your entry updates the next time you play a new eligible tournament.
        </p>
      ),
    },
    {
      question: "Do scores decay if I stop playing?",
      answer: (
        <p>
          This is a bit complicated. You will not see your score decay, instead
          you will be dropped from the leaderboard if you stop playing for a
          while. However, if you come back to play another eligible tournament,
          your score will be updated with old data having a much smaller weight,
          so you might see a large shift in your score in either direction.
        </p>
      ),
    },
    {
      question: "Why is a player missing from the leaderboard?",
      answer: (
        <div className="space-y-3">
          <p>
            Eligibility uses only finalized sendou.ink tournaments marked
            RANKED. Players appear after meeting a small minimum of eligible
            events and will be tracked regardless of team changes.
          </p>
          <p>
            Players will be tracked even if they are not eligible for the
            leaderboard. I am still debating whether to add a view that shows
            all players regardless of eligibility status.
          </p>
          <p>
            Seeing duplicate entries for the same person? sendou.ink supports
            account merges; DM me the sendou helpdesk thread confirming the
            merge and I'll mirror it on the next refresh.
          </p>
        </div>
      ),
    },
    {
      question: "I just played an event - why isn't it showing up?",
      answer: (
        <div className="space-y-3">
          <p>
            A few common reasons:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-slate-300/90">
            <li>The tournament isn't marked RANKED on sendou.ink.</li>
            <li>The tournament isn't finalized yet on sendou.ink.</li>
            <li>It will land with the next daily refresh cycle.</li>
          </ul>
          <p>
            Once it's finalized and marked RANKED, it will count in the next
            refresh. Casual events and scrims don't affect standings.
          </p>
        </div>
      ),
    },
    {
      question: "What do the grades mean?",
      answer: (
        <div className="space-y-3">
          <p>
            Grades follow the Splatoon ladder but add an "X" prefix (XB, XA,
            XS, XS+) to highlight the competitive tier. They're derived from
            the same score shown on the table and don't depend on your team.
          </p>
          <div className="rounded-md border border-slate-800/60 bg-slate-900/50 p-3 text-sm text-slate-200">
            <p className="font-semibold text-center text-slate-100">Grade floors &amp; percentiles</p>
            <p className="mt-1 text-center text-xs text-slate-400">
              Each floor is the minimum display score to hold that grade; share shows the
              portion of tracked players at or above it.
            </p>
            <div className="mt-3 flex justify-center">
              <div className="w-full max-w-md overflow-x-auto">
                <table className="w-full table-auto border-separate border-spacing-y-2 text-center text-sm text-slate-200">
                  <thead className="text-xs uppercase tracking-wide text-slate-400/90">
                    <tr>
                      <th scope="col" className="px-3 py-2 font-semibold">
                        Grade
                      </th>
                      <th scope="col" className="px-3 py-2 font-semibold">
                        Display score ≥
                      </th>
                      <th scope="col" className="px-3 py-2 font-semibold">
                        Share ≥
                      </th>
                      <th scope="col" className="px-3 py-2 font-semibold">
                        Players ≥
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {gradeBreakpoints.map(({ label, floorDisplay }, index) => {
                      const crackle = isXX(label);
                      const crackleProps = crackle
                        ? { "data-color": CRACKLE_PURPLE, "data-rate": rateFor(label) }
                        : {};
                      const chipClassName = `${gradeChipClass(label, false)} ${crackle ? "crackle" : ""}`.trim();
                      const stats = gradeStatsByLabel.get(label);
                      const percentileDisplay =
                        typeof stats?.percentile === "number"
                          ? `Top ${(stats.percentile * 100).toFixed(1)}%`
                          : "—";
                      const countDisplay =
                        typeof stats?.count === "number"
                          ? stats.count.toLocaleString()
                          : "—";
                      const fallbackFloor =
                        index === 0
                          ? null
                          : gradeBreakpoints[index - 1]?.ceilingDisplay ?? null;
                      const thresholdValue =
                        typeof stats?.display_floor === "number"
                          ? stats.display_floor
                          : floorDisplay ?? fallbackFloor;
                      const floorText =
                        thresholdValue == null
                          ? "—"
                          : `≥ ${formatThreshold(thresholdValue)}`;
                      return (
                        <tr key={label} className="rounded-lg">
                          <td className="px-3 py-2">
                            <span className={chipClassName} {...crackleProps}>
                              {label}
                            </span>
                          </td>
                          <td className="px-3 py-2 font-data text-slate-100">
                            {floorText}
                          </td>
                          <td className="px-3 py-2 font-data text-slate-200">
                            {percentileDisplay}
                          </td>
                          <td className="px-3 py-2 font-data text-slate-300">
                            {countDisplay}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
            <p className="mt-3 text-xs text-slate-400 text-center">
              {scorePopulation != null
                ? `${scorePopulation.toLocaleString()} players counted.`
                : "Player counts pending."}
              {percentilesRetrievedAt && ` Snapshot taken ${percentilesRetrievedAt}.`}
              {percentilesStale && " (May be stale)"}
            </p>
          </div>
          <button
            type="button"
            className="block rounded-md border border-fuchsia-500/40 bg-fuchsia-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-fuchsia-200 hover:bg-fuchsia-500/20"
            onClick={() => setShowGradeNerdVersion((value) => !value)}
          >
            {showGradeNerdVersion ? "Hide Nerd Version" : "Show Nerd Version"}
          </button>
          {showGradeNerdVersion && (
            <div className="rounded-md border border-fuchsia-500/30 bg-slate-900/70 p-4 text-sm text-fuchsia-100 space-y-3">
              <p>
                The scoring engine produces a raw log-odds value. We map it to
                display units using <code className="mx-1">display = 150 + 25 * raw</code>
                so the numbers are easier to read, but grade thresholds are defined
                on the raw scale. Each integer step in the raw score is about e
                times harder to reach than the previous one, and we label the
                resulting bands with the X-prefixed Splatoon grades (for example
                XB, XA, XS, XS+).
              </p>
              <p>
                XS- (display score 150+) marks the point where the win and loss flows
                balance—your PageRank odds match the overall competitive field. It's a
                meaningful milestone, though not the 50th percentile. Percentile markers
                are planned for a future update.
              </p>
            </div>
          )}
        </div>
      ),
    },
    {
      question: "What tournaments count, exactly?",
      answer: (
        <div className="space-y-3">
          <p>
            Only finalized sendou.ink tournaments that are explicitly marked
            RANKED are used. Byes/forfeits don't create wins or losses. When
            available, per-match player appearances are preferred; otherwise the
            team's active roster is used for that match. If you play as a
            substitute for a match but are not in the active roster, the match
            will count but the tournament will not for purposes of eligibility.
          </p>
        </div>
      ),
    },
    {
      question: "Who do I contact for fixes or feedback?",
      answer: (
        <p>
          DM <span className="font-mono">pyproject.toml</span> on Discord with
          your player ID, event link, and what needs attention. I'll take a look
          and queue any corrections for the next refresh.
        </p>
      ),
    },
  ];

  return (
    <div ref={rootRef} className="space-y-10">
      <section className="rounded-lg border border-slate-800 bg-slate-900/60 px-6 py-6">
        <h2 className="text-2xl font-semibold text-white">Competitive Leaderboard FAQ</h2>
        <p className="mt-3 text-slate-300">
          New to the competitive leaderboard? These answers explain what the
          rankings show, when the board refreshes, and how to get help if
          something looks off.
        </p>
      </section>

      <dl className="space-y-6">
        {faqs.map(({ question, answer }) => (
          <div
            key={question}
            className="rounded-lg border border-slate-800 bg-slate-900/40 px-6 py-5"
          >
            <dt className="text-lg font-semibold text-white">{question}</dt>
            <dd className="mt-3 text-slate-300 space-y-3">{answer}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
};

export default CompetitionFaq;
