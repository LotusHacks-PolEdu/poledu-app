import { useState } from 'react';
import { Send, Mic } from 'lucide-react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSendMessage, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="border-t border-white/10 bg-[#212121] p-4">
      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
        <div className="relative flex items-end gap-2 bg-[#2f2f2f] rounded-2xl p-2 shadow-lg">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message PolEdu"
            disabled={disabled}
            className="flex-1 bg-transparent border-0 resize-none focus-visible:ring-0 focus-visible:ring-offset-0 text-[15px] placeholder:text-white/40 text-white min-h-[24px] max-h-[200px]"
            rows={1}
          />
          <Button
            type="button"
            size="icon"
            className="h-8 w-8 rounded-lg bg-transparent hover:bg-white/10 text-white/60 hover:text-white"
            title="Voice chat (coming soon)"
          >
            <Mic className="h-4 w-4" />
          </Button>
          <Button
            type="submit"
            size="icon"
            disabled={!input.trim() || disabled}
            className="h-8 w-8 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:bg-white/20 disabled:text-white/40"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-xs text-white/40 text-center mt-2">
          PolEdu can make mistakes. Check important info.
        </p>
      </form>
    </div>
  );
}