export interface Campaign {
  id: string;
  name: string;
  edition: string;
  status: string;
  created_at: string;
}

export interface CampaignModule {
  campaign_id: string;
  module_id: string;
  enabled_at: string;
  priority: number;
}

export interface Module {
  id: string;
  name: string;
  version: string;
  edition: string;
  manifest_json: Record<string, unknown>;
  created_at: string;
}

export interface IngestionReport {
  chunks_created: number;
  entities_created: number;
  warnings: string[];
  errors: string[];
}

export interface ModuleIngestResponse {
  module_id: string;
  version: string;
  ingestion_report: IngestionReport;
}

export interface Citation {
  chunk_id: string;
  source_doc_id: string;
  title: string;
  uri: string | null;
  snippet: string;
}

export interface StateUpdate {
  op: string;
  path: string;
  value: unknown;
  reason: string;
}

export interface QueryResponse {
  answer: string;
  used_agent: 'rules' | 'narrative' | 'state' | 'encounter';
  confidence: number;
  citations: Citation[];
  state_updates: StateUpdate[];
  needs_clarification: boolean;
  clarification_question: string | null;
}

export interface SessionEvent {
  id: string;
  campaign_id: string;
  session_id: string;
  event_type: string;
  event_time: string;
  payload_json: Record<string, unknown>;
}

export interface TimelineResponse {
  events: SessionEvent[];
  total: number;
  page: number;
  page_size: number;
}

export interface WorldState {
  id: string;
  campaign_id: string;
  key: string;
  value_json: unknown;
  updated_at: string;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  agent?: string;
  citations?: Citation[];
  timestamp?: string;
}
