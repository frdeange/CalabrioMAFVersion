import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Output } from '@angular/core';
import { MsalService } from '@azure/msal-angular';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent {
  @Output() public newChat = new EventEmitter<void>();

  constructor(private readonly msalService: MsalService) {}

  public get userName(): string {
    const [activeAccount] = this.msalService.instance.getAllAccounts();
    return activeAccount?.name ?? 'Supervisor';
  }

  public startNewChat(): void {
    this.newChat.emit();
  }

  public signIn(): void {
    this.msalService.loginRedirect();
  }

  public signOut(): void {
    this.msalService.logoutRedirect({
      postLogoutRedirectUri: window.location.origin
    });
  }
}
