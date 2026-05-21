import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { WorkflowEvent } from '../../../core/models/chat.model';

type ProgressStepId = 'intent' | 'sql' | 'executing' | 'result';
type ProgressStepState = 'pending' | 'active' | 'complete' | 'error';

interface ProgressStep {
  id: ProgressStepId;
  label: string;
}

@Component({
  selector: 'app-progress',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './progress.component.html'
})
export class ProgressComponent {
  @Input({ required: true }) public executor = '';
  @Input() public events: WorkflowEvent[] = [];

  public readonly steps: ProgressStep[] = [
    { id: 'intent', label: 'Intent' },
    { id: 'sql', label: 'SQL' },
    { id: 'executing', label: 'Executing' },
    { id: 'result', label: 'Result' }
  ];

  public getState(step: ProgressStepId): ProgressStepState {
    const eventOrder: ProgressStepId[] = this.events
      .filter((event) => event.executor === this.executor)
      .map((event) => this.toStep(event.event));

    if (this.events.some((event) => event.executor === this.executor && event.event === 'error')) {
      return 'error';
    }

    const stepIndex = this.steps.findIndex((item) => item.id === step);
    const reachedIndex = Math.max(...eventOrder.map((currentStep) => this.steps.findIndex((item) => item.id === currentStep)), -1);

    if (stepIndex < reachedIndex) {
      return 'complete';
    }

    if (stepIndex === reachedIndex) {
      return 'active';
    }

    return 'pending';
  }

  private toStep(event: WorkflowEvent['event']): ProgressStepId {
    switch (event) {
      case 'intent_resolved':
        return 'intent';
      case 'sql_building':
      case 'sql_ready':
        return 'sql';
      case 'executing':
        return 'executing';
      case 'result':
      case 'done':
      case 'error':
        return 'result';
      default:
        return 'intent';
    }
  }
}
