export interface WorkflowEvent {
  event: 'intent_resolved' | 'sql_building' | 'sql_ready' | 'executing' | 'result' | 'done' | 'error';
  executor: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  events?: WorkflowEvent[];
  status: 'sending' | 'streaming' | 'complete' | 'error';
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
}

export interface ChatResponse {
  conversation_id: string;
  message?: string;
}
