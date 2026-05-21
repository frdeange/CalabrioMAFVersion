import { CommonModule } from '@angular/common';
import { Component, Input, SecurityContext } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ChatMessage } from '../../../core/models/chat.model';
import { ProgressComponent } from '../progress/progress.component';

@Component({
  selector: 'app-message',
  standalone: true,
  imports: [CommonModule, ProgressComponent],
  templateUrl: './message.component.html',
  styleUrl: './message.component.scss'
})
export class MessageComponent {
  @Input({ required: true }) public message!: ChatMessage;

  constructor(private readonly sanitizer: DomSanitizer) {}

  public get executors(): string[] {
    if (!this.message.events?.length) {
      return [];
    }

    return [...new Set(this.message.events.map((event) => event.executor))];
  }

  public get formattedContent(): SafeHtml | string {
    const content = this.message.content;
    if (this.message.role === 'assistant' && this.looksLikeMarkdownTable(content)) {
      const tableHtml = this.formatMarkdownTable(content);
      return this.sanitizer.bypassSecurityTrustHtml(tableHtml);
    }

    return this.sanitizer.sanitize(SecurityContext.HTML, content) ?? '';
  }

  private looksLikeMarkdownTable(content: string): boolean {
    const lines = content.split('\n').map((line) => line.trim()).filter((line) => line.length > 0);
    for (let index = 0; index < lines.length - 1; index += 1) {
      const current = lines[index];
      const next = lines[index + 1];
      const isHeaderRow = current.startsWith('|') && current.endsWith('|');
      const isDividerRow = next.startsWith('|') && next.includes('---');
      if (isHeaderRow && isDividerRow) {
        return true;
      }
    }

    return false;
  }

  private formatMarkdownTable(content: string): string {
    const lines = content.split('\n');
    let inTable = false;
    let tableHtml = '';
    let result = '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        if (!inTable) {
          inTable = true;
          tableHtml = '<table class="data-table"><thead><tr>';
          const headers = trimmed.split('|').filter((cell) => cell.trim());
          headers.forEach((header) => {
            tableHtml += `<th>${this.escapeHtml(header.trim())}</th>`;
          });
          tableHtml += '</tr></thead><tbody>';
        } else if (trimmed.includes('---')) {
          continue;
        } else {
          tableHtml += '<tr>';
          const cells = trimmed.split('|').filter((cell) => cell.trim());
          cells.forEach((cell) => {
            tableHtml += `<td>${this.escapeHtml(cell.trim())}</td>`;
          });
          tableHtml += '</tr>';
        }
      } else {
        if (inTable) {
          inTable = false;
          tableHtml += '</tbody></table>';
          result += tableHtml;
          tableHtml = '';
        }
        result += `${this.escapeHtml(line)}<br />`;
      }
    }

    if (inTable) {
      tableHtml += '</tbody></table>';
      result += tableHtml;
    }

    return result.replace(/(<br \/>)+$/g, '').trim();
  }

  private escapeHtml(value: string): string {
    return value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
}
