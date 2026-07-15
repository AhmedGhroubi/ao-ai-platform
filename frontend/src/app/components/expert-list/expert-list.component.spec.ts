import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ExpertListComponent } from './expert-list.component';

describe('ExpertListComponent', () => {
  let component: ExpertListComponent;
  let fixture: ComponentFixture<ExpertListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExpertListComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(ExpertListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
