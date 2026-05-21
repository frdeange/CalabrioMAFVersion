import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { MsalService } from '@azure/msal-angular';

interface NavItem {
  icon: string;
  label: string;
  active?: boolean;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})
export class SidebarComponent {
  public collapsed = false;

  public readonly navItems: NavItem[] = [
    { icon: '👥', label: 'People' },
    { icon: '🔐', label: 'Permissions' },
    { icon: '📋', label: 'Plans' },
    { icon: '🎯', label: 'Shift bidding' },
    { icon: '📅', label: 'Schedules' },
    { icon: '💬', label: 'Sessions' },
    { icon: '📨', label: 'Requests' },
    { icon: '📊', label: 'Intraday' },
    { icon: '✓', label: 'Adherence' },
    { icon: '🤝', label: 'Partner Manager' },
    { icon: '📈', label: 'Reports' },
    { icon: '💰', label: 'Payroll Integration' },
    { icon: '⚙️', label: 'WFM settings' },
    { icon: '📆', label: 'Meetings' },
    { icon: '⏰', label: 'MyTime' },
    { icon: '💭', label: 'Supervisor Assist', active: true }
  ];

  public readonly bottomItems: NavItem[] = [
    { icon: '🔔', label: 'Notifications' }
  ];

  constructor(private readonly msalService: MsalService) {}

  public get userName(): string {
    const [activeAccount] = this.msalService.instance.getAllAccounts();
    return activeAccount?.name ?? 'Supervisor';
  }

  public toggleCollapse(): void {
    this.collapsed = !this.collapsed;
  }
}
