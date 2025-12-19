import React from "react";

class CompetitionErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("Competition viz crashed", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center px-6">
          <div className="max-w-lg text-center space-y-3">
            <h1 className="text-2xl font-semibold">Something went wrong</h1>
            <p className="text-slate-400">
              The interactive explainer failed to load. Please refresh the page or return to the leaderboard.
            </p>
            <a
              href="/"
              className="inline-flex items-center justify-center rounded-md bg-white/10 px-4 py-2 text-sm font-medium text-white ring-1 ring-white/10 hover:bg-white/15 transition"
            >
              Back to leaderboard
            </a>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default CompetitionErrorBoundary;
