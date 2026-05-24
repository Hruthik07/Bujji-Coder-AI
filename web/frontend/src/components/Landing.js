import React from 'react';
import GitHubAuthButton from './GitHubAuthButton';
import './Landing.css';

const FEATURES = [
  {
    title: 'BYOK by default',
    body: "Bring your own Anthropic, OpenAI, or DeepSeek key. It's stored only in your browser's localStorage and sent with each request as a header. Never logged, never stored on our server.",
  },
  {
    title: 'AST-aware RAG',
    body: 'Code is chunked along function and class boundaries, not at arbitrary character counts. Retrieval combines keyword and semantic search and re-ranks before feeding the LLM.',
  },
  {
    title: 'Hybrid LLM routing',
    body: 'DeepSeek Coder for code generation, Claude for complex reasoning, OpenAI as fallback. A task classifier picks the right model per request and tracks cost per provider.',
  },
  {
    title: 'Multi-agent pipeline',
    body: 'Retrieval → Planning → Validation. The validator catches syntax and lint issues before any diff is applied. Real refactors, validated before they touch your files.',
  },
];

const STACK = [
  'FastAPI',
  'React',
  'ChromaDB',
  'Redis',
  'Claude 4.7',
  'OpenAI',
  'DeepSeek',
  'GitHub OAuth',
  'Railway',
  'Vercel',
];

function Landing() {
  const goToApp = () => {
    window.location.href = '/app';
  };

  return (
    <div className="landing">
      <header className="landing-header">
        <div className="landing-logo">
          <span className="landing-logo-mark">B</span>
          <span className="landing-logo-text">Bujji Coder AI</span>
        </div>
        <nav className="landing-nav">
          <a
            href="https://github.com/Hruthik07/Bujji-Coder-AI"
            target="_blank"
            rel="noopener noreferrer"
            className="landing-nav-link"
          >
            GitHub
          </a>
          <GitHubAuthButton />
        </nav>
      </header>

      <main className="landing-main">
        <section className="landing-hero">
          <h1 className="landing-tagline">
            Code with an AI that actually understands your codebase.
          </h1>
          <p className="landing-subtitle">
            Hybrid LLM routing, AST-aware retrieval, and a multi-agent
            pipeline that retrieves, plans, and validates before applying
            changes — running on your own API keys.
          </p>
          <div className="landing-cta-row">
            <button
              type="button"
              className="landing-cta-primary"
              onClick={goToApp}
            >
              Try with my API key →
            </button>
            <a
              href="https://github.com/Hruthik07/Bujji-Coder-AI"
              target="_blank"
              rel="noopener noreferrer"
              className="landing-cta-secondary"
            >
              View source
            </a>
          </div>
          <p className="landing-byok-note">
            No signup required — keys stay in your browser.
          </p>
        </section>

        <section className="landing-features">
          {FEATURES.map((f) => (
            <article key={f.title} className="landing-feature">
              <h3 className="landing-feature-title">{f.title}</h3>
              <p className="landing-feature-body">{f.body}</p>
            </article>
          ))}
        </section>

        <section className="landing-stack">
          <h2 className="landing-stack-title">Built with</h2>
          <ul className="landing-stack-list">
            {STACK.map((s) => (
              <li key={s} className="landing-stack-pill">
                {s}
              </li>
            ))}
          </ul>
        </section>

        <section className="landing-how">
          <h2 className="landing-how-title">How it works</h2>
          <ol className="landing-how-steps">
            <li>
              <strong>Open Settings</strong> and paste your Anthropic /
              OpenAI / DeepSeek key. Or sign in with GitHub for cross-device
              chat history.
            </li>
            <li>
              <strong>Ask anything about your code</strong> — Bujji indexes
              the workspace with ChromaDB and retrieves the relevant
              functions and classes for each question.
            </li>
            <li>
              <strong>Review the diff</strong> before applying. The
              validator runs syntax + lint checks first.
            </li>
          </ol>
        </section>
      </main>

      <footer className="landing-footer">
        <span>
          © {new Date().getFullYear()} Bujji Coder AI · MIT
        </span>
        <span className="landing-footer-spacer">·</span>
        <a
          href="https://github.com/Hruthik07/Bujji-Coder-AI"
          target="_blank"
          rel="noopener noreferrer"
        >
          GitHub
        </a>
        <span className="landing-footer-spacer">·</span>
        <a
          href="https://github.com/Hruthik07/Bujji-Coder-AI/issues"
          target="_blank"
          rel="noopener noreferrer"
        >
          Report an issue
        </a>
      </footer>
    </div>
  );
}

export default Landing;
