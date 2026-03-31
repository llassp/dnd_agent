'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { campaignApi, moduleApi } from '@/lib/api';
import type { Campaign, CampaignModule, Module, QueryResponse } from '@/types';

export default function CampaignPage() {
  const params = useParams();
  const router = useRouter();
  const campaignId = params.id as string;

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [enabledModules, setEnabledModules] = useState<CampaignModule[]>([]);
  const [availableModules, setAvailableModules] = useState<Module[]>([]);
  const [sessionId, setSessionId] = useState<string>('');
  const [queryInput, setQueryInput] = useState('');
  const [queryMode, setQueryMode] = useState<'auto' | 'rules' | 'narrative' | 'state' | 'encounter'>('auto');
  const [messages, setMessages] = useState<Array<{role: string; content: string; agent?: string}>>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isQuerying, setIsQuerying] = useState(false);

  useEffect(() => {
    loadCampaign();
    loadAvailableModules();
    // 自动生成 session ID
    if (!sessionId) {
      setSessionId(crypto.randomUUID());
    }
  }, [campaignId]);

  const loadCampaign = async () => {
    try {
      const data = await campaignApi.get(campaignId);
      setCampaign(data);
      const modules = await campaignApi.getModules(campaignId);
      setEnabledModules(modules);
    } catch (error) {
      console.error('Failed to load campaign:', error);
      router.push('/');
    } finally {
      setIsLoading(false);
    }
  };

  const loadAvailableModules = async () => {
    try {
      const modules = await moduleApi.list();
      setAvailableModules(modules);
    } catch {
      console.error('Failed to load modules');
    }
  };

  const handleEnableModule = async (moduleId: string) => {
    try {
      await campaignApi.enableModule(campaignId, { module_id: moduleId, priority: 50 });
      await loadCampaign();
    } catch (error) {
      console.error('Failed to enable module:', error);
    }
  };

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryInput.trim() || !sessionId) {
      if (!sessionId) {
        alert('请先开始一个新会话');
      }
      return;
    }

    setIsQuerying(true);
    const userMessage = { role: 'user' as const, content: queryInput };
    setMessages([...messages, userMessage]);
    setQueryInput('');

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campaign_id: campaignId,
          session_id: sessionId,
          user_input: queryInput,
          mode: queryMode,
        }),
      });

      if (response.ok) {
        const data: QueryResponse = await response.json();
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: data.answer,
            agent: data.used_agent,
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: '抱歉，发生了错误。请稍后重试。' },
        ]);
      }
    } catch (error) {
      console.error('Query failed:', error);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '抱歉，发生了错误。请稍后重试。' },
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  const startNewSession = () => {
    setSessionId(crypto.randomUUID());
    setMessages([]);
  };

  if (isLoading || !campaign) {
    return <div className="p-6">加载中...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-slate-800 text-white p-4">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-gray-300 hover:text-white">
              ← 返回
            </Link>
            <h1 className="text-xl font-bold">{campaign.name}</h1>
            <span className="text-sm text-gray-300">{campaign.edition}</span>
          </div>
        </div>
      </header>

      <main className="container mx-auto p-4">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <aside className="lg:col-span-1 space-y-4">
            <div className="card">
              <h3 className="font-semibold mb-3">会话控制</h3>
              {!sessionId ? (
                <button onClick={startNewSession} className="btn-primary w-full">
                  开始新会话
                </button>
              ) : (
                <div>
                  <p className="text-sm text-gray-500 mb-2">会话ID:</p>
                  <p className="text-xs font-mono bg-gray-100 p-2 rounded break-all">
                    {sessionId.slice(0, 8)}...
                  </p>
                  <button
                    onClick={startNewSession}
                    className="btn-secondary w-full mt-2 text-sm"
                  >
                    开始新会话
                  </button>
                </div>
              )}
            </div>

            <div className="card">
              <h3 className="font-semibold mb-3">已启用的模块</h3>
              {enabledModules.length === 0 ? (
                <p className="text-sm text-gray-500">暂无启用模块</p>
              ) : (
                <ul className="space-y-2">
                  {enabledModules.map((em) => {
                    const module = availableModules.find((m) => m.id === em.module_id);
                    return (
                      <li key={em.module_id} className="text-sm">
                        <span className="font-medium">{module?.name || 'Unknown'}</span>
                        <span className="text-gray-500 ml-2">优先级: {em.priority}</span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            <div className="card">
              <h3 className="font-semibold mb-3">启用模块</h3>
              {availableModules.length === 0 ? (
                <p className="text-sm text-gray-500">暂无可用模块</p>
              ) : (
                <ul className="space-y-2">
                  {availableModules
                    .filter((m) => !enabledModules.some((em) => em.module_id === m.id))
                    .map((module) => (
                      <li key={module.id} className="flex justify-between items-center">
                        <span className="text-sm">
                          {module.name} <span className="text-gray-500">v{module.version}</span>
                        </span>
                        <button
                          onClick={() => handleEnableModule(module.id)}
                          className="text-xs btn-secondary"
                        >
                          启用
                        </button>
                      </li>
                    ))}
                </ul>
              )}
            </div>
          </aside>

          <div className="lg:col-span-3">
            <div className="card h-[calc(100vh-200px)] flex flex-col">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold">会话</h2>
                <div className="flex gap-2">
                  <select
                    value={queryMode}
                    onChange={(e) => setQueryMode(e.target.value as typeof queryMode)}
                    className="input text-sm w-32"
                  >
                    <option value="auto">自动</option>
                    <option value="rules">规则</option>
                    <option value="narrative">叙事</option>
                    <option value="encounter">遭遇</option>
                    <option value="state">状态</option>
                  </select>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto border rounded-lg p-4 bg-gray-50 mb-4">
                {messages.length === 0 ? (
                  <p className="text-gray-400 text-center">
                    {!sessionId ? '点击"开始新会话"开始聊天' : '开始输入你的问题吧！'}
                  </p>
                ) : (
                  <div className="space-y-4">
                    {messages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[80%] rounded-lg p-3 ${
                            msg.role === 'user'
                              ? 'bg-blue-600 text-white'
                              : 'bg-white border'
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
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <form onSubmit={handleQuery} className="flex gap-2">
                <input
                  type="text"
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                  placeholder={sessionId ? '输入你的问题...' : '先开始一个新会话'}
                  disabled={!sessionId || isQuerying}
                  className="input flex-1"
                />
                <button
                  type="submit"
                  disabled={!sessionId || isQuerying}
                  className="btn-primary disabled:opacity-50"
                >
                  {isQuerying ? '发送中...' : '发送'}
                </button>
              </form>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
