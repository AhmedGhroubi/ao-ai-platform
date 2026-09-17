import { Routes } from '@angular/router';
import { TenderUploadComponent } from './components/tender-upload/tender-upload.component';
import { TenderListComponent } from './components/tender-list/tender-list.component';
import { TenderEditorComponent } from './components/tender-editor/tender-editor.component';
import { TenderDetailsComponent } from './components/tender-details/tender-details.component';
import { ExpertUploadComponent } from './components/expert-upload/expert-upload.component';
import { ExpertListComponent } from './components/expert-list/expert-list.component';
import { ExpertDetailsComponent } from './components/expert-details/expert-details.component';
import { ExpertEditComponent } from './components/expert-edit/expert-edit.component';
import { StaffingDashboardComponent } from './components/staffing-dashboard/staffing-dashboard.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';
export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'upload', component: TenderUploadComponent },
  { path: 'list', component: TenderListComponent },
  { path: 'editor/:id', component: TenderEditorComponent },
  { path: 'details/:id', component: TenderDetailsComponent },
  { path: 'experts', component: ExpertListComponent },
  { path: 'experts/upload', component: ExpertUploadComponent },
  { path: 'experts/details/:id', component: ExpertDetailsComponent },
  { path: 'experts/edit/:id', component: ExpertEditComponent }, 
  {path: 'staffing/:tenderId',component:StaffingDashboardComponent},
  { path: '', redirectTo: '/list', pathMatch: 'full' } 
];