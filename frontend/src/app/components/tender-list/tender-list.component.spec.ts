import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TenderListComponent } from './tender-list.component';

describe('TenderListComponent', () => {
  let component: TenderListComponent;
  let fixture: ComponentFixture<TenderListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TenderListComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(TenderListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
