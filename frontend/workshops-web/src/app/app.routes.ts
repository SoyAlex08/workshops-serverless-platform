import { Routes } from '@angular/router';
import { adminGuard } from './core/guards/admin.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'workshops', pathMatch: 'full' },
  { path: 'login', loadComponent: () => import('./features/login/login').then((m) => m.Login) },
  {
    path: 'workshops',
    loadComponent: () => import('./features/workshops-list/workshops-list').then((m) => m.WorkshopsList),
  },
  {
    path: 'workshops/:id',
    loadComponent: () => import('./features/workshop-detail/workshop-detail').then((m) => m.WorkshopDetail),
  },
  {
    path: 'admin',
    loadComponent: () => import('./features/admin/admin').then((m) => m.Admin),
    canActivate: [adminGuard],
  },
  { path: '**', redirectTo: 'workshops' },
];
