import { User, Bot } from 'lucide-react';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={`w-full py-6 px-4 ${
        isUser ? 'bg-transparent' : 'bg-[#2f2f2f]'
      }`}
    >
      <div className="max-w-3xl mx-auto flex gap-6">
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-sm flex items-center justify-center ${
            isUser ? 'bg-green-600' : 'bg-green-600'
          }`}
        >
          {isUser ? (
            <User className="h-5 w-5 text-white" />
          ) : (
            <Bot className="h-5 w-5 text-white" />
          )}
        </div>
        <div className="flex-1 space-y-2">
          <p className="text-[15px] leading-7 whitespace-pre-wrap text-white">
            {message.content}
          </p>
        </div>
      </div>
    </div>
  );
}