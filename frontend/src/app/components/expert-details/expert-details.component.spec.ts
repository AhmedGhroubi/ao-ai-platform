import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ExpertDetailsComponent } from './expert-details.component';

describe('ExpertDetailsComponent', () => {
  let component: ExpertDetailsComponent;
  let fixture: ComponentFixture<ExpertDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExpertDetailsComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(ExpertDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
