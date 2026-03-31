'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { campaignApi, stateApi, sessionApi } from '@/lib/api';
import type { Campaign, WorldState, SessionEvent } from '@/types';

export default function StatePage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>('');
  const [worldState, setWorldState] = useState<WorldState[]>([]);
  const [recentEvents, setRecentEvents] = useState<SessionEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadCampaigns();
  }, []);

  useEffect(() => {
    if (selectedCampaignId) {
      loadWorldState(selectedCampaignId);
    }
  }, [selectedCampaignId]);

  const loadCampaigns = async () => {
    try {
      const data = await campaignApi.list();
      setCampaigns(data);
      if (data.length > 0 && !selectedCampaignId) {
        setSelectedCampaignId(data[0].id);
      }
    } catch (error) {
      console.error('Failed to load campaigns:', error);
    }
  };

  const loadWorldState = async (campaignId: string) => {
    setIsLoading(true);
    try {
      const [state, events] = await Promise.all([
        stateApi.getWorldState(campaignId),
        sessionApi.getTimeline(campaignId, campaignId, 1, 20).catch(() => ({ events: [] })),
      ]);
      setWorldState(state);
      setRecentEvents(events.events || []);
    } catch (error) {
      console.error('Failed to load world state:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-slate-800 text-white p-4">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-gray-300 hover:text-white">
              ← 返回
            </Link>
            <h1 className="text-xl font-bold">世界状态</h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto p-6">
        <div className="card mb-6">
          <h2 className="text-lg font-semibold mb-4">选择战役</h2>
          <select
            value={selectedCampaignId}
            onChange={(e) => setSelectedCampaignId(e.target.value)}
            className="input w-full max-w-md"
          >
            <option value="">-- 选择战役 --</option>
            {campaigns.map((campaign) => (
              <option key={campaign.id} value={campaign.id}>
                {campaign.name} ({campaign.edition})
              </option>
            ))}
          </select>
        </div>

        {selectedCampaignId && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h2 className="text-lg font-semibold mb-4">世界状态</h2>
              {isLoading ? (
                <p className="text-gray-500">加载中...</p>
              ) : worldState.length === 0 ? (
                <p className="text-gray-500">暂无世界状态</p>
              ) : (
                <ul className="space-y-2">
                  {worldState.map((state) => (
                    <li
                      key={state.id}
                      className="border rounded-lg p-3 hover:bg-gray-50"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-mono text-sm font-medium">
                            {state.key}
                          </p>
                          <p className="text-sm text-gray-600 mt-1">
                            {typeof state.value_json === 'object'
                              ? JSON.stringify(state.value_json)
                              : String(state.value_json)}
                          </p>
                        </div>
                        <span className="text-xs text-gray-400">
                          {new Date(state.updated_at).toLocaleString()}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="card">
              <h2 className="text-lg font-semibold mb-4">最近事件</h2>
              {isLoading ? (
                <p className="text-gray-500">加载中...</p>
              ) : recentEvents.length === 0 ? (
                <p className="text-gray-500">暂无事件</p>
              ) : (
                <ul className="space-y-3">
                  {recentEvents.map((event) => (
                    <li
                      key={event.id}
                      className="border-l-4 border-blue-500 pl-3 py-1"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <span className="font-medium text-sm">
                            {event.event_type}
                          </span>
                          <p className="text-xs text-gray-500 mt-1">
                            {JSON.stringify(event.payload_json)}
                          </p>
                        </div>
                        <span className="text-xs text-gray-400">
                          {new Date(event.event_time).toLocaleString()}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
