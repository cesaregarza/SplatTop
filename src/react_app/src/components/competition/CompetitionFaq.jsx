import React, { useState } from "react";

const CompetitionFaq = () => {
  const [showExtendedVersion, setShowExtendedVersion] = useState(false);
  const [showNerdVersion, setShowNerdVersion] = useState(false);
  const [showGradeNerdVersion, setShowGradeNerdVersion] = useState(false);

  const faqs = [
    {
      question: "What are these rankings?",
      answer: (
        <p>
          This leaderboard highlights the strongest competitors based on recent
          ranked tournament results recorded on sendou.ink. You do not need to
          stay on a fixed roster; every player is tracked individually, so
          switching teams from event to event still counts toward your
          placement.
        </p>
      ),
    },
    {
      question: "How is the score calculated?",
      answer: (
        <div className="space-y-3">
          <p>
            We award more points for beating strong opponents at large events
            and fewer points for wins over lower-ranked teams. The result is a
            ladder that rewards consistent performance against tough brackets.
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
                Stronger opponents swing the score more: a win over a top seed
                adds a big chunk, while a loss to them barely dents your total.
                Upset losses to underdogs remove more points because the system
                expected you to win, and routine wins over mid-tier teams taper
                off as the bracket context stabilizes.
              </p>
              <p>
                Previous results are constantly recontextualized. If a player is
                secretly Magnus Carlsen smurfing their way through the bracket,
                you might lose a lot of points the day it happens, but as the
                algorithm realizes how strong they really are, it refunds those
                losses. Every event keeps feeding new information back into old
                matches so the table evolves toward the most accurate ordering.
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
              <p>
                Build a directed graph of ranked match outcomes, run
                exposure-weighted PageRank in both directions, and use
                <code className="mx-1">teleport_weight = 1 / (1 + exposure)</code>
                so players with huge match counts do not soak up free score from
                random jumps. The resulting vector becomes the seed for
                <code className="mx-1">tournament_influence</code>.
              </p>
              <p>
                Iterate until convergence:
                <code className="mx-1">player_score = PR(win_graph, tournament_influence)</code>
                and
                <code className="mx-1">tournament_influence = f(player_score)</code>.
                After it settles, run one more bidirectional PageRank with the
                final influence weights, yielding
                <code className="mx-1">win_pr</code> and
                <code className="mx-1">loss_pr</code>. The published raw score is
                <code className="mx-1">log(win_pr) - log(loss_pr)</code>, which
                neatly offsets volume bias and keeps the scale symmetric.
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
          We publish a fresh leaderboard update every day at 12:15 UTC. That
          daily export keeps the standings rock steady; if you check later in
          the day you will see the same order until the next morning.
        </p>
      ),
    },
    {
      question: "What is the danger window?",
      answer: (
        <p>
          Each placement only counts for a limited time. The danger column shows
          how many days remain before your oldest ranked result expires and, by
          extension, how close you are to dropping out of the leaderboard if you
          skip future ranked tournaments. If the number is low, plan your next
          event so you stay locked in.
        </p>
      ),
    },
    {
      question: "Why is a player missing from the leaderboard?",
      answer: (
        <div className="space-y-3">
          <p>
            Players only disappear if their results age out of the danger
            window. As long as someone has active ranked results from sendou.ink,
            they stay on the board, even if they change teams every event.
          </p>
          <p>
            Seeing duplicate entries for the same person? sendou.ink supports
            account merges, and we mirror those once we're notified. Share the
            sendou helpdesk thread where the merge was approved and I'll unify
            the accounts here as well.
          </p>
        </div>
      ),
    },
    {
      question: "I just played an event - why isn't it showing up?",
      answer: (
        <p>
          We currently ingest tournaments from sendou.ink that are flagged as
          RANKED on that site. Once the event is verified there, it lands in the
          next daily refresh. Casual brackets, scrims, and tournaments without
          the RANKED tag will not change the standings. Support for manually
          marking other events as ranked is on the roadmap.
        </p>
      ),
    },
    {
      question: "What do the grades mean?",
      answer: (
        <div className="space-y-3">
          <p>
            Grades mirror Splatoon's familiar ladder, prefixed with an X to show
            these are competitive tiers; think X-S+, X-S, X-A, and so on. They act
            like the ranked leagues in other games (gold, diamond, masters) so you
            can instantly read a player's tier.
          </p>
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
                Scores start as real numbers from the convergence routine, then
                we apply an affine transform so the displayed values are easier to
                read. Before the transform we bucket players by integer thresholds
                of the raw score, and each +1 step is roughly{' '}
                <code className="mx-1">e</code>{' '}times harder to obtain
                than the previous tier. Those raw thresholds lock in the grade
                bands, which we then label with the familiar X-grade names.
              </p>
            </div>
          )}
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
    <div className="space-y-10">
      <section className="rounded-lg border border-slate-800 bg-slate-900/60 px-6 py-6">
        <h2 className="text-2xl font-semibold text-white">Competition FAQ</h2>
        <p className="mt-3 text-slate-300">
          New to the competition leaderboard? These answers explain what the
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
