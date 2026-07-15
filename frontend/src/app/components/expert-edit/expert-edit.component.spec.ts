import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ExpertEditComponent } from './expert-edit.component';

describe('ExpertEditComponent', () => {
  let component: ExpertEditComponent;
  let fixture: ComponentFixture<ExpertEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExpertEditComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(ExpertEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
