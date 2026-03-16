import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './HomePage.css';

const heroBgImage = `${process.env.PUBLIC_URL || ''}/bg-image.avif`;
const carGifUrl = 'https://cdn.dribbble.com/users/145629/screenshots/1944279/loader0001.gif';

function HomePage() {
  const location = useLocation();
  const fromLogin = location.state?.fromLogin === true;
  const [popIn, setPopIn] = useState(!fromLogin);
  const workflowSectionRef = useRef(null);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [sectionVisible, setSectionVisible] = useState(false);

  useEffect(() => {
    if (fromLogin) {
      const t = requestAnimationFrame(() => {
        requestAnimationFrame(() => setPopIn(true));
      });
      return () => cancelAnimationFrame(t);
    }
  }, [fromLogin]);

  useEffect(() => {
    const section = workflowSectionRef.current;
    if (!section) return;

    const onScroll = () => {
      const rect = section.getBoundingClientRect();
      const viewportHeight = window.innerHeight;
      const sectionTop = rect.top;
      const sectionBottom = rect.bottom;

      const inView = sectionBottom > 0 && sectionTop < viewportHeight;
      setSectionVisible(inView);

      if (!inView) {
        if (sectionBottom <= 0) setScrollProgress(1);
        else setScrollProgress(0);
        return;
      }
      /* 0 = section just entering from bottom, 1 = section top at viewport top (leaving) */
      const progress = (viewportHeight - sectionTop) / viewportHeight;
      setScrollProgress(Math.max(0, Math.min(1, progress)));
    };

    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div className="cortex-page">
      {/* 1. Hero Section – background image only for this section */}
      <section
        className="cortex-hero"
        style={{
          backgroundImage: `url(${heroBgImage})`,
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'center',
          backgroundSize: 'cover',
        }}
      >
        <div className="cortex-hero-bg">
          <div className="cortex-hero-grid" aria-hidden="true" />
          <div className="cortex-hero-glow" aria-hidden="true" />
        </div>
        <div
          className={`cortex-container cortex-hero-inner ${fromLogin ? 'cortex-page__content--from-login' : ''} ${fromLogin && popIn ? 'cortex-page__content--visible' : ''}`}
        >
          <div className="cortex-hero-content">
            <h1 className="cortex-hero-title">
              <span className="cortex-hero-title-line">
                <span className="cortex-hero-title-brand">CortexForge</span> Diagnostics
              </span>
            </h1>
            <p className="cortex-hero-tagline">
              AI-Powered Technician Copilot for Automotive Fault Diagnostics
            </p>
            <p className="cortex-hero-sub">
              Transform Diagnostic Trouble Codes into structured troubleshooting workflows with guided electrical diagnostics, visual assistance, and real-time technician support.
            </p>
            <div className="cortex-hero-actions">
              <Link to="/chat" className="cortex-btn cortex-btn-primary">
                Launch Diagnostic Workspace
              </Link>
              <Link to="/chat" className="cortex-btn cortex-btn-secondary">
                Access Technician Copilot
              </Link>
            </div>
          </div>
          <div className="cortex-hero-visual">
            <div className="cortex-hero-dashboard">
              <div className="cortex-dash-header">Diagnostic Terminal</div>
              <div className="cortex-dash-lines">
                <span className="cortex-dash-line" style={{ animationDelay: '0s' }}>DTC: P0300 — Multiple cylinder misfire</span>
                <span className="cortex-dash-line" style={{ animationDelay: '0.2s' }}>Workflow: Ignition / Fuel delivery</span>
                <span className="cortex-dash-line" style={{ animationDelay: '0.4s' }}>Step 1: Verify spark plug condition</span>
                <span className="cortex-dash-line cortex-dash-cursor" style={{ animationDelay: '0.6s' }}>_</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Platform Capabilities: title full left, right section scrolls one-by-one */}
      <section className="cortex-section cortex-capabilities">
        <div className="cortex-capabilities-wrap">
          <div className="cortex-capabilities-left">
            <h2 className="cortex-capabilities-title">Platform <em>Capabilities</em></h2>
          </div>
          <div className="cortex-capabilities-right">
            <div className="cortex-cards-stack">
            <article className="cortex-card">
              <div className="cortex-card-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" /></svg>
              </div>
              <div className="cortex-card-right">
                <h3 className="cortex-card-title">DTC Diagnostic Engine</h3>
                <p className="cortex-card-desc">Automatically interprets fault codes and retrieves structured troubleshooting procedures aligned with service manuals.</p>
              </div>
            </article>
            <article className="cortex-card">
              <div className="cortex-card-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 5l7 7-7 7" /><path d="M3 5l7 7-7 7" /></svg>
              </div>
              <div className="cortex-card-right">
                <h3 className="cortex-card-title">Guided Diagnostic Workflow</h3>
                <p className="cortex-card-desc">Step-by-step diagnostic guidance that supports technicians during fault isolation and root cause analysis.</p>
              </div>
            </article>
            <article className="cortex-card">
              <div className="cortex-card-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
              </div>
              <div className="cortex-card-right">
                <h3 className="cortex-card-title">Electrical Diagnostics Assistant</h3>
                <p className="cortex-card-desc">Provides instructions for multimeter testing, voltage validation, wiring continuity checks, and sensor verification.</p>
              </div>
            </article>
            <article className="cortex-card">
              <div className="cortex-card-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="23 7 16 12 23 17 23 7" /><rect x="1" y="5" width="15" height="14" rx="2" ry="2" /></svg>
              </div>
              <div className="cortex-card-right">
                <h3 className="cortex-card-title">Visual Diagnostic Support</h3>
                <p className="cortex-card-desc">Integrated access to video tutorials and diagnostic demonstrations for complex procedures.</p>
              </div>
            </article>
            <article className="cortex-card">
              <div className="cortex-card-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 016.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" /><line x1="8" y1="6" x2="16" y2="6" /><line x1="8" y1="10" x2="16" y2="10" /></svg>
              </div>
              <div className="cortex-card-right">
                <h3 className="cortex-card-title">Diagnostic Knowledge Repository</h3>
                <p className="cortex-card-desc">Centralized repository containing diagnostic procedures, component checks, and failure patterns.</p>
              </div>
            </article>
            </div>
          </div>
        </div>
      </section>

      {/* Technician Workflow: title top, steps scroll horizontally; car at bottom moves with scroll */}
      <section ref={workflowSectionRef} className="cortex-section cortex-workflow">
        <div className="cortex-workflow-wrap">
          <div className="cortex-workflow-top">
            <h2 className="cortex-workflow-title">From <em>Fault Code</em> to Root Cause</h2>
          </div>
          <div className="cortex-workflow-scroll" role="region" aria-label="Workflow steps">
            <div className="cortex-timeline">
              <div className="cortex-timeline-step">
                <span className="cortex-timeline-num">1</span>
                <p>Retrieve DTC from diagnostic tool</p>
              </div>
              <div className="cortex-timeline-connector" aria-hidden="true" />
              <div className="cortex-timeline-step">
                <span className="cortex-timeline-num">2</span>
                <p>Enter code into Diagnostic Workspace</p>
              </div>
              <div className="cortex-timeline-connector" aria-hidden="true" />
              <div className="cortex-timeline-step">
                <span className="cortex-timeline-num">3</span>
                <p>Receive guided troubleshooting workflow</p>
              </div>
              <div className="cortex-timeline-connector" aria-hidden="true" />
              <div className="cortex-timeline-step">
                <span className="cortex-timeline-num">4</span>
                <p>Perform electrical validation and component checks</p>
              </div>
              <div className="cortex-timeline-connector" aria-hidden="true" />
              <div className="cortex-timeline-step">
                <span className="cortex-timeline-num">5</span>
                <p>Identify root cause and recommended corrective action</p>
              </div>
            </div>
          </div>
          <br></br>
          <div
            className="cortex-workflow-car-track"
            aria-hidden="true"
            style={{ opacity: sectionVisible ? 1 : 0 }}
          >
            <div
              className="cortex-workflow-car"
              style={{ left: `${9 + scrollProgress * 82}%` }}
            >
              <img src={carGifUrl} alt="" />
            </div>
          </div>
        </div>
      </section>

      {/* 5. Problem / Value Proposition */}
      <section className="cortex-section cortex-problem">
        <div className="cortex-container">
          <h2 className="cortex-section-title">Designed for Real Workshop Challenges</h2>
          <p className="cortex-problem-lead">
            Technicians often face challenges such as searching through thousands of manual pages, interpreting complex diagnostic trees, and executing electrical diagnostics without clear procedural guidance.
          </p>
          <p className="cortex-problem-solution">
            CortexForge Diagnostics addresses these challenges by converting static documentation into interactive troubleshooting intelligence.
          </p>
          <div className="cortex-problem-cards">
            <div className="cortex-problem-card">
              <div className="cortex-problem-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 016.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" /><line x1="8" y1="6" x2="16" y2="6" /><line x1="8" y1="10" x2="12" y2="10" /></svg>
              </div>
              <h3>Manual overload</h3>
              <p>Thousands of pages to search through</p>
            </div>
            <div className="cortex-problem-card">
              <div className="cortex-problem-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 11 12 14 22 4" /><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" /></svg>
              </div>
              <h3>Complex diagnostic trees</h3>
              <p>Hard to interpret and follow</p>
            </div>
            <div className="cortex-problem-card">
              <div className="cortex-problem-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
              </div>
              <h3>Unclear electrical procedures</h3>
              <p>No clear step-by-step guidance</p>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Platform Modules – divided into sections with hover lighten */}
      <section className="cortex-section cortex-modules">
        <div className="cortex-container">
          <h2 className="cortex-section-title">System Modules</h2>

          <div className="cortex-modules-group">
            <h3 className="cortex-modules-group-title">Core diagnostic tools</h3>
            <div className="cortex-modules-grid">
              {[
                { title: 'Diagnostic Workspace', desc: 'Central hub for DTC entry and workflow execution.' },
                { title: 'Technician Copilot', desc: 'AI assistant for real-time diagnostic support.' },
                { title: 'Procedure Navigator', desc: 'Structured access to troubleshooting procedures.' },
              ].map((m, i) => (
                <article key={i} className="cortex-module-card">
                  <div className="cortex-module-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" /></svg>
                  </div>
                  <h3 className="cortex-module-title">{m.title}</h3>
                  <p className="cortex-module-desc">{m.desc}</p>
                </article>
              ))}
            </div>
          </div>

          <div className="cortex-modules-group">
            <h3 className="cortex-modules-group-title">Library & analytics</h3>
            <div className="cortex-modules-grid">
              {[
                { title: 'Visual Diagnostic Library', desc: 'Video and visual reference library.' },
                { title: 'Diagnostic Knowledge Repository', desc: 'Searchable procedures and failure patterns.' },
                { title: 'Session Analytics', desc: 'Track diagnostic sessions and outcomes.' },
              ].map((m, i) => (
                <article key={i} className="cortex-module-card">
                  <div className="cortex-module-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" /></svg>
                  </div>
                  <h3 className="cortex-module-title">{m.title}</h3>
                  <p className="cortex-module-desc">{m.desc}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 7. Enterprise Integration */}
      <section className="cortex-section cortex-enterprise">
        <div className="cortex-container">
          <h2 className="cortex-section-title">Designed for OEM and Service Networks</h2>
          <p className="cortex-enterprise-lead">
            CortexForge Diagnostics can integrate with:
          </p>
          <div className="cortex-integration-grid">
            <div className="cortex-integration-item">
              <div className="cortex-integration-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /></svg>
              </div>
              <span>OEM diagnostic tools</span>
            </div>
            <div className="cortex-integration-item">
              <div className="cortex-integration-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 016.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" /></svg>
              </div>
              <span>Service documentation repositories</span>
            </div>
            <div className="cortex-integration-item">
              <div className="cortex-integration-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z" /><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z" /></svg>
              </div>
              <span>Technician training platforms</span>
            </div>
            <div className="cortex-integration-item">
              <div className="cortex-integration-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /></svg>
              </div>
              <span>Workshop management systems</span>
            </div>
          </div>
        </div>
      </section>

      {/* 8. Footer */}
      <footer className="cortex-footer">
        <div className="cortex-container cortex-footer-inner">
          <div className="cortex-footer-brand">CortexForge Diagnostics</div>
          <nav className="cortex-footer-nav" aria-label="Footer">
            <Link to="/about">About</Link>
            <a href={`${process.env.PUBLIC_URL || ''}/TechnicalGuideDocument-CortexForgeDiagnosticAIAGent.pdf`} target="_blank" rel="noopener noreferrer">Documentation</a>
            <a href="https://mail.google.com/mail/?view=cm&to=info@axtr.in" target="_blank" rel="noopener noreferrer">For query: info@axtr.in</a>
          </nav>
          <div className="cortex-footer-copy">
            &copy; {new Date().getFullYear()} aXtrLabs. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}

export default HomePage;
