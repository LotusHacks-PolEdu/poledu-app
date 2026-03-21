import { Button } from './ui/button';
import logoImage from 'figma:asset/8289073d5453cf95f32130e7565ad1fb1fd39549.png';

interface LandingPageProps {
  onEnter: () => void;
}

export function LandingPage({ onEnter }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Hexagonal Bee Hive Pattern Background */}
      <div className="absolute inset-0 opacity-10">
        <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="hexagons" width="100" height="87" patternUnits="userSpaceOnUse" patternTransform="scale(1.5)">
              <path
                d="M25,0 L75,0 L100,43.5 L75,87 L25,87 L0,43.5 Z"
                fill="none"
                stroke="url(#gradient)"
                strokeWidth="1.5"
              />
            </pattern>
            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style={{ stopColor: '#10b981', stopOpacity: 1 }} />
              <stop offset="50%" style={{ stopColor: '#06b6d4', stopOpacity: 1 }} />
              <stop offset="100%" style={{ stopColor: '#10b981', stopOpacity: 1 }} />
            </linearGradient>
          </defs>
          <rect width="100%" height="100%" fill="url(#hexagons)" />
        </svg>
      </div>

      {/* Animated gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-green-500/5 via-cyan-500/5 to-green-500/5 animate-pulse" style={{ animationDuration: '4s' }}></div>

      {/* Fixed Logo Top Left */}
      <div className="fixed top-6 left-6 z-50 flex items-center gap-3">
        <div className="w-12 h-12 rounded-lg overflow-hidden shadow-lg">
          <img 
            src={logoImage}
            alt="PolEdu Logo"
            className="w-full h-full object-cover"
          />
        </div>
        <span className="text-2xl font-bold text-white">PolEdu</span>
      </div>

      {/* Main Content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        <div className="max-w-4xl mx-auto text-center space-y-12">
          {/* Hero Text */}
          <div className="space-y-6">
            <h1 className="text-6xl md:text-7xl lg:text-8xl font-bold leading-tight">
              <span className="bg-gradient-to-r from-green-400 via-cyan-400 to-green-400 bg-clip-text text-transparent animate-gradient">
                Learn
              </span>
              <span className="text-white">, in your way,</span>
              <br />
              <span className="text-white">at your </span>
              <span className="bg-gradient-to-r from-cyan-400 via-green-400 to-cyan-400 bg-clip-text text-transparent">
                pace
              </span>
            </h1>
            <p className="text-xl md:text-2xl text-gray-400 max-w-2xl mx-auto">
              Your personal AI tutor, ready to help you master any subject
            </p>
          </div>

          {/* Enter Button */}
          <div className="pt-8">
            <Button
              onClick={onEnter}
              className="px-12 py-6 text-lg font-semibold rounded-2xl bg-gradient-to-r from-white to-gray-100 text-black hover:from-gray-100 hover:to-white shadow-2xl hover:shadow-green-500/20 transition-all duration-300 transform hover:scale-105"
            >
              Enter PolEdu Tutor
            </Button>
          </div>

          {/* Feature Hexagons */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-16">
            <div className="group relative">
              <div className="absolute inset-0 bg-gradient-to-br from-green-500/20 to-cyan-500/20 rounded-3xl transform group-hover:scale-105 transition-transform duration-300"></div>
              <div className="relative p-6 rounded-3xl border border-green-500/30 backdrop-blur-sm">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-green-500 to-cyan-500 flex items-center justify-center">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold mb-2 text-white">Personalized Learning</h3>
                <p className="text-gray-400 text-sm">Adapt to your unique learning style and pace</p>
              </div>
            </div>

            <div className="group relative">
              <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 to-green-500/20 rounded-3xl transform group-hover:scale-105 transition-transform duration-300"></div>
              <div className="relative p-6 rounded-3xl border border-cyan-500/30 backdrop-blur-sm">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-cyan-500 to-green-500 flex items-center justify-center">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold mb-2 text-white">AI-Powered Insights</h3>
                <p className="text-gray-400 text-sm">Smart assistance that grows with you</p>
              </div>
            </div>

            <div className="group relative">
              <div className="absolute inset-0 bg-gradient-to-br from-green-500/20 to-cyan-500/20 rounded-3xl transform group-hover:scale-105 transition-transform duration-300"></div>
              <div className="relative p-6 rounded-3xl border border-green-500/30 backdrop-blur-sm">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-green-500 to-cyan-500 flex items-center justify-center">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold mb-2 text-white">24/7 Availability</h3>
                <p className="text-gray-400 text-sm">Learn anytime, anywhere, at your convenience</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* White Blank Space Section */}
      <div className="relative z-10 bg-white py-32 mt-32">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-black mb-4">
              Coming Soon
            </h2>
            <p className="text-xl text-gray-600">
              More features and content will be added here
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
            {/* Placeholder Box 1 */}
            <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-3xl p-12 flex items-center justify-center min-h-[300px]">
              <p className="text-gray-400 text-lg">Content Area 1</p>
            </div>
            
            {/* Placeholder Box 2 */}
            <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-3xl p-12 flex items-center justify-center min-h-[300px]">
              <p className="text-gray-400 text-lg">Content Area 2</p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer White Section */}
      <div className="relative z-10 bg-white py-16">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <p className="text-gray-500">© 2026 PolEdu. All rights reserved.</p>
        </div>
      </div>

      <style>{`
        @keyframes gradient {
          0%, 100% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 100% 50%;
          }
        }
        .animate-gradient {
          background-size: 200% 200%;
          animation: gradient 3s ease infinite;
        }
      `}</style>
    </div>
  );
}
