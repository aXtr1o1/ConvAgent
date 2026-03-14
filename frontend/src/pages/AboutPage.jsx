import React from 'react';
import { Link } from 'react-router-dom';
import './HomePage.css';
import './AboutPage.css';

const bgImage = `${process.env.PUBLIC_URL || ''}/bg-image.avif`;

function AboutPage() {
  return (
    <div className="cortex-page cortex-about">
      <div className="cortex-about-content">
      {/* Section 1 — background image on the area behind the card, not on the card */}
      <div
        className="cortex-about-hero-zone"
        style={{
          backgroundImage: `url(${bgImage})`,
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'center',
          backgroundSize: 'cover',
        }}
      >
        <section className="cortex-section cortex-about-section">
          <div className="cortex-container">
            <h2 className="cortex-section-title">About CortexForge Diagnostics</h2>
          <p className="cortex-about-lead">
            CortexForge Diagnostics is an AI-powered diagnostic intelligence platform developed to assist automotive service technicians in troubleshooting vehicle faults with greater precision and efficiency.
          </p>
          <p className="cortex-about-lead">
            The system transforms Diagnostic Trouble Codes (DTCs) into structured diagnostic workflows, combining procedural guidance, electrical diagnostics support, and visual technical assistance to accelerate root cause identification.
          </p>
          <p className="cortex-about-lead">
            The platform is designed to complement modern OEM diagnostic tools by providing practical guidance during complex diagnostic scenarios.
          </p>
          </div>
        </section>
      </div>

      

      {/* Section 4 — Vision: two columns, blob left + image right (app theme) */}
      <section className="cortex-section cortex-about-vision-section">
        <div className="cortex-about-vision-wrap">
          <div className="cortex-about-vision-left">
            <div className="cortex-about-vision-blob">
              <div className="cortex-about-vision-img-wrap" aria-hidden="true">
                <div className="cortex-about-vision-img" />
              </div>
              <h2 className="cortex-about-vision-title">Our Vision</h2>
              <p className="cortex-about-vision-text">
                To create an intelligent diagnostic platform that transforms static service documentation into interactive technician guidance systems for modern automotive service environments.
              </p>
              <Link to="/about" className="cortex-about-vision-cta">Learn more</Link>
            </div>
          </div>
          </div>
      </section>

      {/* Bottom — Developed by (top) + logo full width, 75% height shown */}
      <section className="cortex-about-footer">
        <p className="cortex-about-footer-title">Developed by</p>
        <div className="cortex-about-footer-logo-wrap">
          <img
            src={`${process.env.PUBLIC_URL || ''}/AI-Company-logo.png`}
            alt="The AI Company"
            className="cortex-about-footer-logo"
          />
        </div>
      </section>
      </div>
    </div>
  );
}

export default AboutPage;
