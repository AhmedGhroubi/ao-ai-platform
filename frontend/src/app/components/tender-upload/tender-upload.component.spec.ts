import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TenderUploadComponent } from './tender-upload.component';

describe('TenderUploadComponent', () => {
  let component: TenderUploadComponent;
  let fixture: ComponentFixture<TenderUploadComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TenderUploadComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(TenderUploadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
