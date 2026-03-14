import React from 'react';

const bgImage = `${process.env.PUBLIC_URL || ''}/bg-image.avif`;

function LandingPage() {
  return (
    <div
      className="landing-page-layout"
      style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        backgroundImage: `url(${bgImage})`,
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'center',
        backgroundSize: 'cover',
      }}
    >
      {/* Landing content */}
    </div>
  );
}
export default LandingPage;