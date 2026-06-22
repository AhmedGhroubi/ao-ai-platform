import { Routes } from '@angular/router';
import { TenderUploadComponent } from './components/tender-upload/tender-upload.component';
import { TenderListComponent } from './components/tender-list/tender-list.component';
import { TenderEditorComponent } from './components/tender-editor/tender-editor.component';
import { TenderDetailsComponent } from './components/tender-details/tender-details.component';
export const routes: Routes = [
  { path: 'upload', component: TenderUploadComponent },
  { path: 'list', component: TenderListComponent },
  { path: 'editor/:id', component: TenderEditorComponent },
  { path: 'details/:id', component: TenderDetailsComponent },
  { path: '', redirectTo: '/list', pathMatch: 'full' } 
];