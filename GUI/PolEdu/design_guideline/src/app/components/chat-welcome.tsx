import { MessageSquare, Lightbulb, Code, Sparkles } from 'lucide-react';

const suggestions = [
  {
    icon: MessageSquare,
    title: 'Create a to-do list',
    description: 'for an upcoming trip',
  },
  {
    icon: Lightbulb,
    title: 'Help me brainstorm',
    description: 'ideas for a team building event',
  },
  {
    icon: Code,
    title: 'Write code',
    description: 'to solve a problem in Python',
  },
  {
    icon: Sparkles,
    title: 'Summarize this article',
    description: 'into key takeaways',
  },
];

interface ChatWelcomeProps {
  onSelectSuggestion: (suggestion: string) => void;
}

export function ChatWelcome({ onSelectSuggestion }: ChatWelcomeProps) {
  return (
    <div className="flex-1 flex items-center justify-center p-8 bg-[#212121]">
      <div className="max-w-3xl w-full">
        <div className="text-center mb-8">
          <h1 className="text-4xl mb-4 text-white">What can I help with?</h1>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {suggestions.map((suggestion, index) => {
            const Icon = suggestion.icon;
            return (
              <button
                key={index}
                onClick={() =>
                  onSelectSuggestion(`${suggestion.title} ${suggestion.description}`)
                }
                className="text-left p-4 rounded-2xl border border-white/10 hover:bg-white/5 transition-colors group"
              >
                <div className="flex items-start gap-3">
                  <Icon className="h-5 w-5 text-white/60 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm text-white">
                      {suggestion.title}{' '}
                      <span className="text-white/60">{suggestion.description}</span>
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}