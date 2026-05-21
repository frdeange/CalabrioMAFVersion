import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';
import { ChatComponent } from './features/chat/chat.component';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'chat'
  },
  {
    path: 'chat',
    component: ChatComponent,
    canActivate: [authGuard]
  },
  {
    path: '**',
    redirectTo: 'chat'
  }
];
