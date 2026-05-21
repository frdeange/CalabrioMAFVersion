import { Injectable, OnDestroy } from '@angular/core';
import { MsalService } from '@azure/msal-angular';
import { Observable, Subject } from 'rxjs';
import { ChatRequest, WorkflowEvent } from '../models/chat.model';
import { ApiService } from './api.service';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ChatService implements OnDestroy {
  private readonly workflowEventsSubject = new Subject<WorkflowEvent>();
  private readonly maxReconnectAttempts = 3;

  private abortController?: AbortController;
  private reconnectAttempts = 0;
  private reconnectTimerId?: number;
  private reconnecting = false;
  private currentConversationId?: string;
  private currentPayload?: ChatRequest;
  private streamCompleted = false;

  constructor(
    private readonly apiService: ApiService,
    private readonly msalService: MsalService
  ) {}

  public sendMessage(text: string): Observable<WorkflowEvent> {
    const payload: ChatRequest = {
      message: text,
      conversation_id: this.currentConversationId
    };

    this.currentPayload = payload;
    this.reconnectAttempts = 0;
    this.streamCompleted = false;
    this.closeActiveStream();
    this.clearReconnectTimer();
    void this.connect(payload);

    return this.workflowEventsSubject.asObservable();
  }

  public cancel(): void {
    this.streamCompleted = true;
    this.reconnecting = false;
    this.reconnectAttempts = 0;
    this.closeActiveStream();
    this.clearReconnectTimer();
  }

  public ngOnDestroy(): void {
    this.cancel();
    this.workflowEventsSubject.complete();
  }

  private async connect(payload: ChatRequest): Promise<void> {
    this.closeActiveStream();
    this.clearReconnectTimer();
    this.abortController = new AbortController();

    try {
      const accessToken = await this.acquireAccessToken();
      const response = await fetch(this.apiService.chatUrl, {
        method: 'POST',
        headers: {
          Accept: 'text/event-stream',
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`
        },
        body: JSON.stringify(payload),
        signal: this.abortController.signal
      });

      if (!response.ok || !response.body) {
        throw new Error(`Failed to stream chat response (${response.status})`);
      }

      this.reconnecting = false;
      this.reconnectAttempts = 0;
      await this.consumeSse(response.body.getReader());

      if (!this.streamCompleted) {
        this.tryReconnect();
      }
    } catch (error: unknown) {
      if (this.isAbortError(error) || this.streamCompleted) {
        return;
      }
      this.tryReconnect();
    }
  }

  private tryReconnect(): void {
    if (this.reconnecting) {
      return;
    }

    if (!this.currentPayload || this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.emitError('stream', 'Streaming disconnected.', 'Please send your question again.');
      this.cancel();
      return;
    }

    this.reconnecting = true;
    this.reconnectAttempts += 1;
    const payload: ChatRequest = {
      ...this.currentPayload,
      conversation_id: this.currentConversationId ?? this.currentPayload.conversation_id
    };
    this.currentPayload = payload;
    this.reconnectTimerId = window.setTimeout(() => {
      this.reconnecting = false;
      void this.connect(payload);
    }, 1200);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimerId !== undefined) {
      window.clearTimeout(this.reconnectTimerId);
      this.reconnectTimerId = undefined;
    }
  }

  private closeActiveStream(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = undefined;
    }
  }

  private async consumeSse(reader: ReadableStreamDefaultReader<Uint8Array>): Promise<void> {
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
      buffer = this.processSseBuffer(buffer);
    }
  }

  private processSseBuffer(buffer: string): string {
    let nextBuffer = buffer;
    let separatorIndex = nextBuffer.indexOf('\n\n');

    while (separatorIndex !== -1) {
      const eventBlock = nextBuffer.slice(0, separatorIndex);
      nextBuffer = nextBuffer.slice(separatorIndex + 2);
      this.handleSseEvent(eventBlock);
      separatorIndex = nextBuffer.indexOf('\n\n');
    }

    return nextBuffer;
  }

  private handleSseEvent(eventBlock: string): void {
    if (!eventBlock) {
      return;
    }

    const dataLines = eventBlock
      .split('\n')
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart());
    if (!dataLines.length) {
      return;
    }

    const event = this.parseWorkflowEvent(dataLines.join('\n'));
    if (!event) {
      return;
    }

    const conversationId = this.readText(event.data, 'conversation_id');
    if (conversationId) {
      this.currentConversationId = conversationId;
    }

    this.workflowEventsSubject.next(event);

    if (event.event === 'done') {
      this.streamCompleted = true;
      this.cancel();
    }
  }

  private parseWorkflowEvent(rawData: string): WorkflowEvent | null {
    try {
      const parsed: unknown = JSON.parse(rawData);
      if (!this.isWorkflowEvent(parsed)) {
        return null;
      }

      return parsed;
    } catch {
      return null;
    }
  }

  private readText(data: Record<string, unknown>, key: string): string | null {
    const value = data[key];
    return typeof value === 'string' && value.length > 0 ? value : null;
  }

  private isAbortError(error: unknown): boolean {
    return error instanceof Error && error.name === 'AbortError';
  }

  private async acquireAccessToken(): Promise<string> {
    const account = this.msalService.instance.getActiveAccount() ?? this.msalService.instance.getAllAccounts()[0];
    if (!account) {
      throw new Error('No signed-in account available for chat stream.');
    }

    const tokenResponse = await this.msalService.instance.acquireTokenSilent({
      scopes: environment.msalConfig.scopes,
      account
    });
    return tokenResponse.accessToken;
  }

  private isWorkflowEvent(value: unknown): value is WorkflowEvent {
    if (typeof value !== 'object' || value === null) {
      return false;
    }

    const candidate = value as Record<string, unknown>;
    return typeof candidate['event'] === 'string'
      && typeof candidate['executor'] === 'string'
      && typeof candidate['timestamp'] === 'string'
      && typeof candidate['data'] === 'object'
      && candidate['data'] !== null;
  }

  private emitError(layer: string, reason: string, suggestion: string): void {
    this.workflowEventsSubject.next({
      event: 'error',
      executor: 'guardrail',
      data: { layer, reason, suggestion },
      timestamp: new Date().toISOString()
    });
  }
}
