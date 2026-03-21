import { Plus, MessageSquare, Menu, Trash2, PanelLeftClose, FileText, User } from 'lucide-react';
import { Button } from './ui/button';
import logoImage from 'figma:asset/8289073d5453cf95f32130e7565ad1fb1fd39549.png';

interface Conversation {
  id: string;
  title: string;
  timestamp: Date;
}

interface ChatSidebarProps {
  conversations: Conversation[];
  currentConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: string) => void;
  isOpen: boolean;
  onToggle: () => void;
  isLoggedIn: boolean;
  userEmail: string | null;
  onShowLogin: () => void;
}

export function ChatSidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  isOpen,
  onToggle,
  isLoggedIn,
  userEmail,
  onShowLogin
}: ChatSidebarProps) {
  if (!isOpen) {
    return (
      <div className="absolute top-4 left-4 z-10">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className="rounded-lg text-white hover:bg-white/10"
        >
          <Menu className="h-5 w-5" />
        </Button>
      </div>
    );
  }

  return (
    <div className="w-64 bg-[#171717] border-r border-white/10 flex flex-col h-full">
      {/* Logo and PolEdu header */}
      <div className="h-16 border-b border-white/10 flex items-center px-4 gap-3">
        <div className="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0">
          <img 
            src={logoImage}
            alt="PolEdu Logo"
            className="w-full h-full object-cover"
          />
        </div>
        <span className="text-xl font-semibold text-white">PolEdu</span>
      </div>
      
      <div className="p-2">
        <div className="flex items-center gap-2 mb-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
            className="rounded-lg hover:bg-white/10 text-white"
          >
            <PanelLeftClose className="h-5 w-5" />
          </Button>
          <Button
            onClick={onNewConversation}
            className="flex-1 justify-start gap-2 bg-transparent border border-white/10 hover:bg-white/10 text-white"
          >
            <Plus className="h-4 w-4" />
            New chat
          </Button>
        </div>
        
        {/* Documents Section - Below New Chat */}
        <div className="flex items-center gap-2 p-3 rounded-lg hover:bg-white/5 cursor-pointer border border-white/10">
          <FileText className="h-4 w-4 text-white/80" />
          <span className="text-sm text-white">Documents</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-2">
        {conversations.map((conversation) => (
          <div
            key={conversation.id}
            className={`group relative flex items-center gap-2 p-3 rounded-lg cursor-pointer mb-1 ${
              currentConversationId === conversation.id
                ? 'bg-white/10'
                : 'hover:bg-white/5'
            }`}
            onClick={() => onSelectConversation(conversation.id)}
          >
            <MessageSquare className="h-4 w-4 flex-shrink-0 text-white/80" />
            <span className="text-sm truncate flex-1 text-white">{conversation.title}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white/10 text-white"
              onClick={(e) => {
                e.stopPropagation();
                onDeleteConversation(conversation.id);
              }}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        ))}
      </div>

      {/* Login/User Account Section - Bottom Left */}
      <div className="border-t border-white/10 p-3">
        {isLoggedIn ? (
          <div className="flex items-center gap-3 p-2 rounded-lg bg-white/5">
            <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center">
              <User className="h-4 w-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white truncate">{userEmail}</p>
            </div>
          </div>
        ) : (
          <div>
            <Button
              onClick={onShowLogin}
              className="w-full justify-center bg-green-600 hover:bg-green-700 text-white mb-2"
            >
              Login
            </Button>
            <p className="text-xs text-yellow-500 text-center">
              Please login to save your conversations
            </p>
          </div>
        )}
      </div>
    </div>
  );
}