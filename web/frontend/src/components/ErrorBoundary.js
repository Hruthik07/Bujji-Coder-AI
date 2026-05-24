import React from 'react';
import './ErrorBoundary.css';

/**
 * Top-level error boundary.
 *
 * Catches any uncaught rendering / lifecycle error from descendants
 * and renders a calm fallback instead of the React white-screen-of-
 * death. Without this, a single throw inside any component takes
 * down the whole app — bad UX, worse demo signal.
 *
 * React error boundaries must be class components (the hook
 * equivalent doesn't exist as of React 18). This is the only class
 * component in the project.
 */
class ErrorBoundary extends React.Component {
  state = { error: null, info: null, showDetails: false };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Once we wire Sentry (Phase 4.2) this is where Sentry.captureException
    // goes. For now: console.error so the dev can still spot it.
    // eslint-disable-next-line no-console
    console.error('[ErrorBoundary]', error, info);
    this.setState({ info });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleHome = () => {
    window.location.href = '/';
  };

  toggleDetails = () => {
    this.setState((s) => ({ showDetails: !s.showDetails }));
  };

  render() {
    const { error, info, showDetails } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="error-boundary">
        <div className="error-boundary-card">
          <h1 className="error-boundary-title">Something went wrong.</h1>
          <p className="error-boundary-subtitle">
            The page hit an unexpected error. Reloading usually fixes it. If
            it keeps happening, please open an issue on GitHub with the
            details below.
          </p>
          <div className="error-boundary-actions">
            <button
              type="button"
              className="error-boundary-primary"
              onClick={this.handleReload}
            >
              Reload page
            </button>
            <button
              type="button"
              className="error-boundary-secondary"
              onClick={this.handleHome}
            >
              Back to landing
            </button>
          </div>

          <button
            type="button"
            className="error-boundary-details-toggle"
            onClick={this.toggleDetails}
          >
            {showDetails ? 'Hide details' : 'Show details'}
          </button>

          {showDetails && (
            <pre className="error-boundary-details">
              {String(error?.stack || error)}
              {info?.componentStack ? `\n\n${info.componentStack}` : ''}
            </pre>
          )}
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
