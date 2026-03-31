import axios from 'axios';
import type {
  Campaign,
  CampaignModule,
  Module,
  ModuleIngestResponse,
  QueryResponse,
  SessionEvent,
  TimelineResponse,
  WorldState,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const campaignApi = {
  create: async (data: { name: string; edition: string }): Promise<Campaign> => {
    const response = await api.post<Campaign>('/campaigns', data);
    return response.data;
  },

  get: async (id: string): Promise<Campaign> => {
    const response = await api.get<Campaign>(`/campaigns/${id}`);
    return response.data;
  },

  list: async (): Promise<Campaign[]> => {
    const response = await api.get<Campaign[]>('/campaigns');
    return response.data;
  },

  enableModule: async (
    campaignId: string,
    data: { module_id: string; priority: number }
  ): Promise<CampaignModule> => {
    const response = await api.post<CampaignModule>(
      `/campaigns/${campaignId}/enable-module`,
      data
    );
    return response.data;
  },

  getModules: async (campaignId: string): Promise<CampaignModule[]> => {
    const response = await api.get<CampaignModule[]>(
      `/campaigns/${campaignId}/modules`
    );
    return response.data;
  },
};

export const moduleApi = {
  ingest: async (data: { package_path: string }): Promise<ModuleIngestResponse> => {
    const response = await api.post<ModuleIngestResponse>('/modules/ingest', data);
    return response.data;
  },

  list: async (): Promise<Module[]> => {
    const response = await api.get<Module[]>('/modules');
    return response.data;
  },
};

export const queryApi = {
  query: async (data: {
    campaign_id: string;
    session_id: string;
    user_input: string;
    mode?: 'auto' | 'rules' | 'narrative' | 'state' | 'encounter';
  }): Promise<QueryResponse> => {
    const response = await api.post<QueryResponse>('/query', data);
    return response.data;
  },
};

export const sessionApi = {
  createEvent: async (
    sessionId: string,
    data: {
      campaign_id: string;
      event_type: string;
      payload_json: Record<string, unknown>;
    }
  ): Promise<SessionEvent> => {
    const response = await api.post<SessionEvent>(
      `/sessions/${sessionId}/events`,
      data
    );
    return response.data;
  },

  getTimeline: async (
    sessionId: string,
    campaignId: string,
    page = 1,
    pageSize = 50
  ): Promise<TimelineResponse> => {
    const response = await api.get<TimelineResponse>(
      `/sessions/${sessionId}/events`,
      {
        params: { campaign_id: campaignId, page, page_size: pageSize },
      }
    );
    return response.data;
  },
};

export const stateApi = {
  apply: async (data: {
    campaign_id: string;
    patches: Array<{ op: string; path: string; value: unknown }>;
  }): Promise<{ applied: unknown[]; world_state: WorldState[] }> => {
    const response = await api.post('/state/apply', data);
    return response.data;
  },

  getWorldState: async (campaignId: string): Promise<WorldState[]> => {
    const response = await api.get<WorldState[]>(`/state/campaign/${campaignId}`);
    return response.data;
  },
};

export const healthApi = {
  check: async (): Promise<{ status: string }> => {
    const response = await api.get<{ status: string }>('/health');
    return response.data;
  },

  ready: async (): Promise<{ status: string; database: string }> => {
    const response = await api.get<{ status: string; database: string }>(
      '/health/ready'
    );
    return response.data;
  },
};

export default api;
