import { CommonModule } from '@angular/common';
import { AfterViewChecked, Component, ElementRef, OnDestroy, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { MsalService } from '@azure/msal-angular';
import { ChatMessage, WorkflowEvent } from '../../core/models/chat.model';
import { ChatService } from '../../core/services/chat.service';
import { MessageComponent } from './message/message.component';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, MessageComponent],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss'
})
export class ChatComponent implements AfterViewChecked, OnDestroy {
  @ViewChild('messagesContainer') private messagesContainer?: ElementRef<HTMLElement>;

  public readonly messages: ChatMessage[] = [];
  public draft = '';
  public activeExecutor = '';

  private streamSubscription?: Subscription;
  private shouldAutoScroll = false;

  constructor(
    private readonly chatService: ChatService,
    private readonly msalService: MsalService
  ) {}

  public get userName(): string {
    const [activeAccount] = this.msalService.instance.getAllAccounts();
    return activeAccount?.name ?? 'Supervisor';
  }

  public sendMessage(): void {
    const content = this.draft.trim();
    if (!content) {
      return;
    }

    const userMessage: ChatMessage = {
      role: 'user',
      content,
      timestamp: new Date(),
      status: 'complete'
    };

    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: 'Preparing your request...',
      timestamp: new Date(),
      status: 'sending',
      events: []
    };

    this.messages.push(userMessage, assistantMessage);
    this.draft = '';
    this.shouldAutoScroll = true;

    this.streamSubscription?.unsubscribe();
    this.streamSubscription = this.chatService.sendMessage(content).subscribe({
      next: (event) => this.handleWorkflowEvent(event, assistantMessage),
      error: () => {
        assistantMessage.status = 'error';
        assistantMessage.content = 'Unable to process your request. Please try again.';
        this.shouldAutoScroll = true;
      }
    });
  }

  public cancel(): void {
    this.chatService.cancel();
    this.streamSubscription?.unsubscribe();
    this.activeExecutor = '';

    const activeMessage = this.messages[this.messages.length - 1];
    if (activeMessage?.role === 'assistant' && activeMessage.status !== 'complete') {
      activeMessage.status = 'error';
      activeMessage.content = 'Request canceled.';
      this.shouldAutoScroll = true;
    }
  }

  public ngAfterViewChecked(): void {
    if (!this.shouldAutoScroll || !this.messagesContainer) {
      return;
    }

    const element = this.messagesContainer.nativeElement;
    element.scrollTop = element.scrollHeight;
    this.shouldAutoScroll = false;
  }

  public ngOnDestroy(): void {
    this.streamSubscription?.unsubscribe();
    this.chatService.cancel();
  }

  private handleWorkflowEvent(event: WorkflowEvent, assistantMessage: ChatMessage): void {
    assistantMessage.status = event.event === 'done' ? 'complete' : event.event === 'error' ? 'error' : 'streaming';
    assistantMessage.events = [...(assistantMessage.events ?? []), event];
    this.activeExecutor = event.executor;

    if (event.event === 'result') {
      assistantMessage.content = this.readText(event.data, 'message') ?? this.readText(event.data, 'result') ?? assistantMessage.content;
    }

    if (event.event === 'error') {
      const layer = this.readText(event.data, 'layer') ?? 'unknown layer';
      const reason = this.readText(event.data, 'reason') ?? 'No details available.';
      const suggestion = this.readText(event.data, 'suggestion') ?? 'Try rephrasing your request.';
      assistantMessage.content = `Rejected by ${layer}: ${reason} Suggestion: ${suggestion}`;
    }

    if (event.event === 'intent_resolved') {
      const summary = this.readText(event.data, 'intent') ?? this.readText(event.data, 'summary');
      if (summary) {
        assistantMessage.content = `Intent: ${summary}`;
      }
    }

    if (event.event === 'executing') {
      assistantMessage.content = `Running ${event.executor}...`;
    }

    if (event.event === 'done') {
      this.streamSubscription?.unsubscribe();
      this.activeExecutor = '';
    }

    this.shouldAutoScroll = true;
  }

  private readText(data: Record<string, unknown>, key: string): string | null {
    const value = data[key];
    return typeof value === 'string' && value.length > 0 ? value : null;
  }
}
