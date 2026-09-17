import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import { StaffingDashboardComponent } from './staffing-dashboard.component';
import { StaffingService } from '../../services/staffing.service';

describe('StaffingDashboardComponent', () => {
  let component: StaffingDashboardComponent;
  let fixture: ComponentFixture<StaffingDashboardComponent>;
  let staffingService: jasmine.SpyObj<StaffingService>;

  beforeEach(async () => {
    staffingService = jasmine.createSpyObj('StaffingService', ['generateStaffing', 'selectManualExpert', 'getCandidatesForProfile']);
    staffingService.generateStaffing.and.returnValue(of({
      status: 'ok',
      score_global_equipe: 70,
      conflits_arbitres: [],
      proposition_equipe: []
    }));
    staffingService.getCandidatesForProfile.and.returnValue(of([]));

    await TestBed.configureTestingModule({
      imports: [StaffingDashboardComponent],
      providers: [
        { provide: StaffingService, useValue: staffingService },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => '42' } } } },
        { provide: Router, useValue: { navigate: jasmine.createSpy('navigate') } }
      ]
    }).compileComponents();
    
    fixture = TestBed.createComponent(StaffingDashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should force a fresh generation on initial load', () => {
    component.loadInitialStaffing();

    expect(staffingService.generateStaffing).toHaveBeenCalledWith(42, true);
  });

  it('should detect when an expert is already assigned to another slot', () => {
    component.staffingData = {
      status: 'ok',
      score_global_equipe: 70,
      conflits_arbitres: [],
      proposition_equipe: [
        {
          poste: 'Développeur',
          required_profile_id: 1,
          expert_selectionne: { expert_id: 10, nom_expert: 'Alice', score_global: 80, confidence: 0.9, score_breakdown: [], justification_ia: { resume: '', points_forts: [], points_faibles: [] }, selectionne_par_defaut: true },
          alternatives: []
        },
        {
          poste: 'Architecte',
          required_profile_id: 2,
          expert_selectionne: { expert_id: 20, nom_expert: 'Bob', score_global: 75, confidence: 0.8, score_breakdown: [], justification_ia: { resume: '', points_forts: [], points_faibles: [] }, selectionne_par_defaut: true },
          alternatives: []
        }
      ]
    } as any;

    const conflictSlot = component.findAssignedSlotForExpert(20, 1);

    expect(conflictSlot?.required_profile_id).toBe(2);
  });

  it('should reset transient UI state when a new staffing response is applied', () => {
    component.activeJustificationSlotId = 1;
    component.conflictWarning = {
      expertId: 10,
      expertName: 'Alice',
      currentSlotId: 1,
      conflictingSlotId: 2
    };

    component['applyStaffingResponse']({
      status: 'ok',
      score_global_equipe: 75,
      conflits_arbitres: [],
      proposition_equipe: [
        {
          poste: 'Développeur',
          required_profile_id: 1,
          expert_selectionne: { expert_id: 10, nom_expert: 'Alice', score_global: 80, confidence: 0.9, score_breakdown: [], justification_ia: { resume: '', points_forts: [], points_faibles: [] }, selectionne_par_defaut: true },
          alternatives: []
        }
      ]
    } as any);

    expect(component.activeJustificationSlotId).toBeNull();
    expect(component.conflictWarning).toBeNull();
    expect(component.staffingData?.proposition_equipe[0].showAlternatives).toBeFalse();
  });

  it('should persist both sides of a replacement after confirming a conflict warning', () => {
    component.staffingData = {
      status: 'ok',
      score_global_equipe: 70,
      conflits_arbitres: [],
      proposition_equipe: [
        {
          poste: 'Développeur',
          required_profile_id: 1,
          expert_selectionne: { expert_id: 10, nom_expert: 'Alice', score_global: 80, confidence: 0.9, score_breakdown: [], justification_ia: { resume: '', points_forts: [], points_faibles: [] }, selectionne_par_defaut: true, selectionne_par_user: true },
          alternatives: []
        },
        {
          poste: 'Architecte',
          required_profile_id: 2,
          expert_selectionne: { expert_id: 20, nom_expert: 'Bob', score_global: 75, confidence: 0.8, score_breakdown: [], justification_ia: { resume: '', points_forts: [], points_faibles: [] }, selectionne_par_defaut: true, selectionne_par_user: true },
          alternatives: []
        }
      ]
    } as any;

    component.conflictWarning = {
      expertId: 11,
      expertName: 'Charlie',
      currentSlotId: 1,
      conflictingSlotId: 2,
      replacementExpert: {
        expert_id: 11,
        nom_expert: 'Charlie',
        score_global: 85,
        confidence: 0.95,
        score_breakdown: [],
        selectionne_par_defaut: false,
        justification_ia: { resume: '', points_forts: [], points_faibles: [] }
      }
    };

    const staffingData = component.staffingData;
    if (!staffingData) {
      throw new Error('staffingData should be initialized');
    }

    const replacementExpert = staffingData.proposition_equipe[0].expert_selectionne;
    const previousExpert = staffingData.proposition_equipe[1].expert_selectionne;

    staffingService.selectManualExpert.and.returnValue(of({
      status: 'updated',
      message: 'ok',
      expert_id: replacementExpert.expert_id,
      required_profile_id: 1,
      score_global: replacementExpert.score_global,
      justification_ia: replacementExpert.justification_ia
    }));

    component.confirmConflictReplacement();

    expect(staffingService.selectManualExpert).toHaveBeenCalledWith(42, 1, 11);
    expect(staffingService.selectManualExpert).toHaveBeenCalledWith(42, 2, 20);
  });
});
