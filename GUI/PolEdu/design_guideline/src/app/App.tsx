import { useState } from 'react';
import { ChatSidebar } from './components/chat-sidebar';
import { ChatMessage, Message } from './components/chat-message';
import { ChatInput } from './components/chat-input';
import { ChatWelcome } from './components/chat-welcome';
import { ChatHeader } from './components/chat-header';
import { Button } from './components/ui/button';
import { LandingPage } from './components/landing-page';

interface Conversation {
  id: string;
  title: string;
  timestamp: Date;
  messages: Message[];
}

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [conversations, setConversations] = useState<Conversation[]>([
    {
      id: '1',
      title: 'Previous conversation example',
      timestamp: new Date(Date.now() - 86400000),
      messages: [
        {
          id: '1',
          role: 'user',
          content: 'Hello! How can you help me today?',
          timestamp: new Date(Date.now() - 86400000),
        },
        {
          id: '2',
          role: 'assistant',
          content:
            "Hello! I'm here to help you with a wide variety of tasks. I can assist with:\n\n• Answering questions and providing information\n• Writing and editing content\n• Coding and technical problems\n• Creative brainstorming\n• Analysis and research\n• And much more!\n\nWhat would you like help with today?",
          timestamp: new Date(Date.now() - 86400000),
        },
      ],
    },
  ]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [showLoginModal, setShowLoginModal] = useState(false);

  const currentConversation = conversations.find((c) => c.id === currentConversationId);

  const handleEnterChat = () => {
    setShowLanding(false);
  };

  const handleNewConversation = () => {
    setCurrentConversationId(null);
  };

  const handleSelectConversation = (id: string) => {
    setCurrentConversationId(id);
  };

  const handleDeleteConversation = (id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (currentConversationId === id) {
      setCurrentConversationId(null);
    }
  };

  const handleLogin = (email: string) => {
    setIsLoggedIn(true);
    setUserEmail(email);
    setShowLoginModal(false);
  };

  const handleShowLogin = () => {
    setShowLoginModal(true);
  };

  const handleSendMessage = (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    // If no current conversation, create a new one
    if (!currentConversationId) {
      const newConversation: Conversation = {
        id: Date.now().toString(),
        title: content.slice(0, 30) + (content.length > 30 ? '...' : ''),
        timestamp: new Date(),
        messages: [userMessage],
      };

      setConversations((prev) => [newConversation, ...prev]);
      setCurrentConversationId(newConversation.id);

      // Simulate AI response
      setTimeout(() => {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content:
            "I'm a demo PolEdu interface. In a real application, I would process your message and provide a helpful response. This is a UI demonstration showing how the chat interface works with message history, conversations, and a clean design.",
          timestamp: new Date(),
        };

        setConversations((prev) =>
          prev.map((conv) =>
            conv.id === newConversation.id
              ? { ...conv, messages: [...conv.messages, assistantMessage] }
              : conv
          )
        );
      }, 1000);
    } else {
      // Add to existing conversation
      setConversations((prev) =>
        prev.map((conv) =>
          conv.id === currentConversationId
            ? { ...conv, messages: [...conv.messages, userMessage] }
            : conv
        )
      );

      // Simulate AI response
      setTimeout(() => {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content:
            "I'm a demo PolEdu interface. In a real application, I would process your message and provide a helpful response. This is a UI demonstration showing how the chat interface works.",
          timestamp: new Date(),
        };

        setConversations((prev) =>
          prev.map((conv) =>
            conv.id === currentConversationId
              ? { ...conv, messages: [...conv.messages, assistantMessage] }
              : conv
          )
        );
      }, 1000);
    }
  };

  return (
    <>
      {showLanding ? (
        <LandingPage onEnter={handleEnterChat} />
      ) : (
        <div className="size-full flex bg-[#212121] text-white">
          <ChatSidebar
            conversations={conversations}
            currentConversationId={currentConversationId}
            onSelectConversation={handleSelectConversation}
            onNewConversation={handleNewConversation}
            onDeleteConversation={handleDeleteConversation}
            isOpen={sidebarOpen}
            onToggle={() => setSidebarOpen(!sidebarOpen)}
            isLoggedIn={isLoggedIn}
            userEmail={userEmail}
            onShowLogin={handleShowLogin}
          />

          <div className="flex-1 flex flex-col h-full">
            <ChatHeader isLoggedIn={isLoggedIn} onLogin={handleLogin} />
            
            {!currentConversation ? (
              <ChatWelcome onSelectSuggestion={handleSendMessage} />
            ) : (
              <div className="flex-1 overflow-y-auto bg-[#212121]">
                {currentConversation.messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
              </div>
            )}

            <ChatInput onSendMessage={handleSendMessage} />
          </div>
        </div>
      )}

      {/* Login Modal from Sidebar */}
      {showLoginModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-black border border-white/20 rounded-2xl p-8 w-96 shadow-2xl">
            <h2 className="text-2xl font-bold text-white mb-6">Login to PolEdu</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-white mb-2">Email</label>
                <input
                  type="email"
                  id="sidebar-email"
                  className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder:text-white/40 focus:outline-none focus:border-green-500"
                  placeholder="Enter your email"
                />
              </div>
              <div>
                <label className="block text-sm text-white mb-2">Password</label>
                <input
                  type="password"
                  className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder:text-white/40 focus:outline-none focus:border-green-500"
                  placeholder="Enter your password"
                />
              </div>
              <div className="flex gap-2 pt-4">
                <Button
                  onClick={() => setShowLoginModal(false)}
                  className="flex-1 bg-white/10 hover:bg-white/20 text-white"
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => {
                    const emailInput = document.getElementById('sidebar-email') as HTMLInputElement;
                    if (emailInput?.value.trim()) {
                      handleLogin(emailInput.value);
                    }
                  }}
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