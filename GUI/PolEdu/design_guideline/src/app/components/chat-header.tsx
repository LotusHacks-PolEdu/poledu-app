import { useState } from 'react';
import { Button } from './ui/button';

interface ChatHeaderProps {
  isLoggedIn: boolean;
  onLogin: (email: string) => void;
}

export function ChatHeader({ isLoggedIn, onLogin }: ChatHeaderProps) {
  const [showLogin, setShowLogin] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = () => {
    if (email.trim()) {
      onLogin(email);
      setShowLogin(false);
      setEmail('');
      setPassword('');
    }
  };

  if (isLoggedIn) {
    return null; // Don't show header login button if already logged in
  }

  return (
    <>
      <div className="h-16 border-b border-white/10 flex items-center justify-end px-6">
        <Button
          onClick={() => setShowLogin(true)}
          className="bg-green-600 hover:bg-green-700 text-white px-6"
        >
          Login
        </Button>
      </div>

      {/* Login Modal */}
      {showLogin && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-black border border-white/20 rounded-2xl p-8 w-96 shadow-2xl">
            <h2 className="text-2xl font-bold text-white mb-6">Login to PolEdu</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-white mb-2">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder:text-white/40 focus:outline-none focus:border-green-500"
                  placeholder="Enter your email"
                />
              </div>
              <div>
                <label className="block text-sm text-white mb-2">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder:text-white/40 focus:outline-none focus:border-green-500"
                  placeholder="Enter your password"
                />
              </div>
              <div className="flex gap-2 pt-4">
                <Button
                  onClick={() => setShowLogin(false)}
                  className="flex-1 bg-white/10 hover:bg-white/20 text-white"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleLogin}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                >
                  Sign In
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}