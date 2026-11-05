import React from "react";

export const AnimatedWaveBackground: React.FC = () => {
  return (
    <div
      aria-hidden="true"
      className="absolute -top-12 md:-top-14 lg:-top-16 -left-6 md:-left-8 lg:-left-10 -right-6 md:-right-8 lg:-right-10 h-[280px] pointer-events-none overflow-hidden select-none z-0"
    >
      {/* Wave Layer 1 - Deep soft periwinkle ribbon */}
      <div className="absolute top-0 left-0 w-[200%] h-full animate-wave-seamless-slow opacity-75">
        <svg
          className="w-full h-full"
          viewBox="0 0 2880 260"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="fullWidthWaveGrad1" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#818CF8" stopOpacity="0.15" />
              <stop offset="25%" stopColor="#A5B4FC" stopOpacity="0.35" />
              <stop offset="50%" stopColor="#60A5FA" stopOpacity="0.45" />
              <stop offset="75%" stopColor="#818CF8" stopOpacity="0.32" />
              <stop offset="100%" stopColor="#A5B4FC" stopOpacity="0.15" />
            </linearGradient>
            <linearGradient id="fullWidthEdge1" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#818CF8" stopOpacity="0.5" />
              <stop offset="50%" stopColor="#60A5FA" stopOpacity="0.7" />
              <stop offset="100%" stopColor="#818CF8" stopOpacity="0.5" />
            </linearGradient>
          </defs>
          <path
            d="M 0,20 C 360,95 620,-10 880,35 C 1140,95 1300,-5 1440,20 C 1800,95 2060,-10 2320,35 C 2580,95 2740,-5 2880,20 L 2880,125 C 2740,80 2580,180 2320,120 C 2060,60 1800,170 1440,105 C 1300,80 1140,180 880,120 C 620,60 360,170 0,105 Z"
            fill="url(#fullWidthWaveGrad1)"
          />
          <path
            d="M 0,20 C 360,95 620,-10 880,35 C 1140,95 1300,-5 1440,20 C 1800,95 2060,-10 2320,35 C 2580,95 2740,-5 2880,20"
            stroke="url(#fullWidthEdge1)"
            strokeWidth="1.5"
            fill="none"
          />
        </svg>
      </div>

      {/* Wave Layer 2 - Sweeping sky-blue ribbon */}
      <div className="absolute top-0 left-0 w-[200%] h-full animate-wave-seamless-medium animate-wave-float opacity-80">
        <svg
          className="w-full h-full"
          viewBox="0 0 2880 260"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="fullWidthWaveGrad2" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.18" />
              <stop offset="30%" stopColor="#60A5FA" stopOpacity="0.40" />
              <stop offset="65%" stopColor="#38BDF8" stopOpacity="0.48" />
              <stop offset="100%" stopColor="#3B82F6" stopOpacity="0.18" />
            </linearGradient>
            <linearGradient id="fullWidthEdge2" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#38BDF8" stopOpacity="0.6" />
              <stop offset="50%" stopColor="#60A5FA" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#38BDF8" stopOpacity="0.6" />
            </linearGradient>
          </defs>
          <path
            d="M 0,45 C 320,-10 580,105 840,30 C 1100,-25 1280,85 1440,45 C 1760,-10 2020,105 2280,30 C 2540,-25 2720,85 2880,45 L 2880,135 C 2720,165 2540,50 2280,110 C 2020,175 1760,60 1440,125 C 1280,165 1100,50 840,110 C 580,175 320,60 0,125 Z"
            fill="url(#fullWidthWaveGrad2)"
          />
          <path
            d="M 0,45 C 320,-10 580,105 840,30 C 1100,-25 1280,85 1440,45 C 1760,-10 2020,105 2280,30 C 2540,-25 2720,85 2880,45"
            stroke="url(#fullWidthEdge2)"
            strokeWidth="1.5"
            fill="none"
          />
        </svg>
      </div>

      {/* Wave Layer 3 - Light cyan accent crest */}
      <div className="absolute top-0 left-0 w-[200%] h-full animate-wave-seamless-fast opacity-85">
        <svg
          className="w-full h-full"
          viewBox="0 0 2880 260"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="fullWidthWaveGrad3" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#0EA5E9" stopOpacity="0.10" />
              <stop offset="40%" stopColor="#38BDF8" stopOpacity="0.30" />
              <stop offset="70%" stopColor="#7DD3FC" stopOpacity="0.40" />
              <stop offset="100%" stopColor="#0EA5E9" stopOpacity="0.10" />
            </linearGradient>
          </defs>
          <path
            d="M 0,5 C 400,60 680,-15 960,40 C 1200,85 1340,0 1440,5 C 1840,60 2120,-15 2400,40 C 2640,85 2780,0 2880,5 L 2880,85 C 2780,65 2640,135 2400,95 C 2120,45 1840,115 1440,70 C 1340,65 1200,135 960,95 C 680,45 400,115 0,70 Z"
            fill="url(#fullWidthWaveGrad3)"
          />
        </svg>
      </div>
    </div>
  );
};

export default AnimatedWaveBackground;
