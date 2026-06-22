import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TenderEditorComponent } from './tender-editor.component';

describe('TenderEditorComponent', () => {
  let component: TenderEditorComponent;
  let fixture: ComponentFixture<TenderEditorComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TenderEditorComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(TenderEditorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
