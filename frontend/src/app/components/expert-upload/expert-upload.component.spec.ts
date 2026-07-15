import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ExpertUploadComponent } from './expert-upload.component';

describe('ExpertUploadComponent', () => {
  let component: ExpertUploadComponent;
  let fixture: ComponentFixture<ExpertUploadComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExpertUploadComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(ExpertUploadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
