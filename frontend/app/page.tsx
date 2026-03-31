'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { campaignApi, moduleApi, healthApi } from '@/lib/api';
import type { Campaign, Module } from '@/types';

export default function HomePage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [modules, setModules] = useState<Module[]>([]);
  const [newCampaignName, setNewCampaignName] = useState('');
  const [newCampaignEdition, setNewCampaignEdition] = useState('5e');
  const [isLoading, setIsLoading] = useState(true);
  const [healthStatus, setHealthStatus] = useState<string>('checking...');

  useEffect(() => {
    loadData();
    checkHealth();
  }, []);

  const loadData = async () => {
    try {
      const [campaignList, moduleList] = await Promise.all([
        campaignApi.list().catch(() => []),
        moduleApi.list().catch(() => []),
      ]);
      setCampaigns(campaignList);
      setModules(moduleList);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const checkHealth = async () => {
    try {
      const health = await healthApi.check();
      setHealthStatus(health.status);
    } catch {
      setHealthStatus('unavailable');
    }
  };

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCampaignName.trim()) return;

    try {
      const campaign = await campaignApi.create({
        name: newCampaignName,
        edition: newCampaignEdition,
      });
      setCampaigns([...campaigns, campaign]);
      setNewCampaignName('');
    } catch (error) {
      console.error('Failed to create campaign:', error);
    }
  };

  return (
    <div className="min-h-screen">
      <header className="bg-slate-800 text-white p-4">
        <div className="container mx-auto flex justify-between items-center">
          <h1 className="text-2xl font-bold">DnD RAG 战役助手</h1>
          <div className="flex items-center gap-4">
            <span
              className={`px-2 py-1 rounded text-sm ${
                healthStatus === 'healthy'
                  ? 'bg-green-600'
                  : 'bg-red-600'
              }`}
            >
              {healthStatus}
            </span>
          </div>
        </div>
      </header>

      <main className="container mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <section className="lg:col-span-2">
            <div className="card mb-6">
              <h2 className="text-xl font-semibold mb-4">创建新战役</h2>
              <form onSubmit={handleCreateCampaign} className="flex gap-4">
                <input
                  type="text"
                  value={newCampaignName}
                  onChange={(e) => setNewCampaignName(e.target.value)}
                  placeholder="战役名称"
                  className="input flex-1"
                />
                <select
                  value={newCampaignEdition}
                  onChange={(e) => setNewCampaignEdition(e.target.value)}
                  className="input w-32"
                >
                  <option value="5e">5e</option>
                  <option value="3.5e">3.5e</option>
                  <option value="other">Other</option>
                </select>
                <button type="submit" className="btn-primary">
                  创建
                </button>
              </form>
            </div>

            <div className="card">
              <h2 className="text-xl font-semibold mb-4">战役列表</h2>
              {isLoading ? (
                <p className="text-gray-500">加载中...</p>
              ) : campaigns.length === 0 ? (
                <p className="text-gray-500">暂无战役，请创建一个</p>
              ) : (
                <ul className="space-y-3">
                  {campaigns.map((campaign) => (
                    <li
                      key={campaign.id}
                      className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="font-medium text-lg">{campaign.name}</h3>
                          <p className="text-sm text-gray-500">
                            {campaign.edition} | {campaign.status}
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            创建于: {new Date(campaign.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <Link
                          href={`/campaigns/${campaign.id}`}
                          className="btn-primary text-sm"
                        >
                          进入战役
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <aside>
            <div className="card mb-6">
              <h2 className="text-xl font-semibold mb-4">可用模块</h2>
              {modules.length === 0 ? (
                <p className="text-gray-500 text-sm">暂无模块</p>
              ) : (
                <ul className="space-y-2">
                  {modules.map((module) => (
                    <li key={module.id} className="text-sm">
                      <span className="font-medium">{module.name}</span>
                      <span className="text-gray-500 ml-2">v{module.version}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="card">
              <h2 className="text-xl font-semibold mb-4">快速链接</h2>
              <ul className="space-y-2 text-sm">
                <li>
                  <Link href="/state" className="text-blue-600 hover:underline">
                    世界状态 →
                  </Link>
                </li>
              </ul>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
