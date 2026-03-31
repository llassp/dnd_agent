'use client';

import type { ChatMessage } from '@/types';
import CitationSidebar from './CitationSidebar';

interface ChatPanelProps {
  messages: ChatMessage[];
  onQuery: (input: string) => void;
  queryMode: string;
  onQueryModeChange: (mode: string) => void;
  citations: import('@/types').Citation[];
  disabled?: boolean;
  isLoading?: boolean;
}

export default function ChatPanel({
  messages,
  onQuery,
  queryMode,
  onQueryModeChange,
  citations,
  disabled,
  isLoading,
}: ChatPanelProps) {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const input = form.elements.namedItem('query') as HTMLInputElement;
    if (input.value.trim()) {
      onQuery(input.value);
      input.value = '';
    }
  };

  return (
    <div className="card flex flex-col h-[calc(100vh-200px)]">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">会话</h2>
        <select
          value={queryMode}
          onChange={(e) => onQueryModeChange(e.target.value)}
          className="input text-sm w-32"
        >
          <option value="auto">自动</option>
          <option value="rules">规则</option>
          <option value="narrative">叙事</option>
          <option value="encounter">遭遇</option>
          <option value="state">状态</option>
        </select>
      </div>

      <div className="flex-1 flex gap-4 mb-4">
        <div className="flex-1 overflow-y-auto border rounded-lg p-4 bg-gray-50">
          {messages.length === 0 ? (
            <p className="text-gray-400 text-center">开始输入你的问题吧！</p>
          ) : (
            <div className="space-y-4">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-3 ${
                      msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white border'
                    }`}
                  >
                    {msg.agent && (
                      <span
                        className={`agent-badge agent-${msg.agent} text-xs mb-1 inline-block`}
                      >
                        {msg.agent}
                      </span>
                    )}
                    <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                    <div className="text-xs opacity-70 mt-1">
                      {msg.timestamp || ''}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {citations.length > 0 && (
          <div className="w-80 overflow-y-auto">
            <CitationSidebar citations={citations} />
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          name="query"
          placeholder={disabled ? '先选择一个战役' : '输入你的问题...'}
          disabled={disabled || isLoading}
          className="input flex-1"
        />
        <button
          type="submit"
          disabled={disabled || isLoading}
          className="btn-primary disabled:opacity-50"
        >
          {isLoading ? '发送中...' : '发送'}
        </button>
      </form>

      {messages.some((m) => m.citations && m.citations.length > 0) && (
        <div className="mt-2 text-xs text-gray-500">
          点击消息可查看引用详情
        </div>
      )}
    </div>
  );
}
