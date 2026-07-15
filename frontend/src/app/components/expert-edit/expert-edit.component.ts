import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ExpertService } from '../../services/expert.service';
import { Expert } from '../../models/expert.model';

@Component({
  selector: 'app-expert-edit',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './expert-edit.component.html',
  styleUrls: ['./expert-edit.component.css']
})
export class ExpertEditComponent implements OnInit {
  editForm!: FormGroup;
  isLoading = true;
  isSaving = false;
  isAnalyzingSection: string | null = null;
  expertId!: number;

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private expertService: ExpertService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.expertId = Number(this.route.snapshot.paramMap.get('id'));
    this.initForm();
    this.loadExpert();
  }
  initForm() {
    this.editForm = this.fb.group({
      nom_expert: ['', Validators.required],
      slug_unique: ['', Validators.required],
      status: [''],
      extracted_data: this.fb.group({
        date_naissance: [''],
        nationalite: [''],
        titre_poste_principal: [''],
        annees_experience_total: [0],
        langues: this.fb.array([]),
        certifications: this.fb.array([]),
        competences_techniques: this.fb.array([]),
        etudes: this.fb.array([]),
        experiences_professionnelles: this.fb.array([]),
        projets_et_missions: this.fb.array([])
      })
    });
  }

  setupSlugAutoGeneration(): void {
  // On écoute les changements sur le nom et la date de naissance
  const nomControl = this.editForm.get('nom_expert');
  const dateControl = this.editForm.get('extracted_data.date_naissance');
  const slugControl = this.editForm.get('slug_unique');

  if (nomControl && dateControl && slugControl) {
    // Dès qu'un des deux change
    const updateSlug = () => {
      // On ne l'auto-génère que si l'utilisateur n'a pas modifié le slug manuellement
      if (slugControl.pristine) {
        const nouveauSlug = this.generateExpertSlug(nomControl.value, dateControl.value);
        slugControl.setValue(nouveauSlug, { emitEvent: false });
      }
    };

    nomControl.valueChanges.subscribe(updateSlug);
    dateControl.valueChanges.subscribe(updateSlug);
  }
}

  // --- Helpers pour accéder aux FormArrays ---
  get experiences() { return this.editForm.get('extracted_data.experiences_professionnelles') as FormArray; }
  get etudes() { return this.editForm.get('extracted_data.etudes') as FormArray; }
  get competences() { return this.editForm.get('extracted_data.competences_techniques') as FormArray; }
  get langues() { return this.editForm.get('extracted_data.langues') as FormArray; }
  get projets(): FormArray {
  return (this.editForm.get('extracted_data') as FormGroup).get('projets_et_missions') as FormArray;
}
  loadExpert() {
    this.expertService.getExpertById(this.expertId).subscribe(expert => {
      this.patchForm(expert);
      this.isLoading = false;
    });
  }

  patchForm(expert: Expert) {
    const data = expert.extracted_data;
    if (!data) return;

    // Remplir les champs simples
    this.editForm.patchValue({
      nom_expert: expert.nom_expert,
      slug_unique: expert.slug_unique,
      status: expert.status
    });
    this.editForm.get('extracted_data')?.patchValue({
      date_naissance: data.date_naissance,
      nationalite: data.nationalite,
      titre_poste_principal: data.titre_poste_principal,
      annees_experience_total: data.annees_experience_total
    });

    this.langues.clear();
    this.competences.clear();
    this.etudes.clear();
    this.experiences.clear();
    this.projets.clear();

    data.langues?.forEach(l => this.langues.push(this.fb.control(l)));
    data.competences_techniques?.forEach(c => this.competences.push(this.fb.control(c)));
    
    data.etudes?.forEach(e => {
      this.etudes.push(this.fb.group({
        annee: [e.annee],
        diplome: [e.diplome],
        institution: [e.institution]
      }));
    });

    data.experiences_professionnelles?.forEach(exp => {
      this.experiences.push(this.fb.group({
        periode: [exp.periode],
        employeur: [exp.employeur],
        poste: [exp.poste],
        pays: [exp.pays],
        resume_activites: [exp.resume_activites?.join('\n')] 
      }));
    });

    data.projets_et_missions?.forEach(p => {
      this.projets.push(this.fb.group({
        nom_projet: [p.nom_projet],
        client_ou_bailleur: [p.client_ou_bailleur],
        annee: [p.annee],
        pays: [p.pays],
        poste_occupe: [p.poste_occupe]
      }));
    });
  }

  addItem(array: FormArray, group?: any) {
    array.push(group ? this.fb.group(group) : this.fb.control(''));
  }

  removeItem(array: FormArray, index: number) {
    array.removeAt(index);
  }

  onSubmit() {
    this.isSaving = true;
    const formValue = this.editForm.value;

    if (formValue.extracted_data) {
      formValue.extracted_data.nom_expert = formValue.nom_expert;
    }

    formValue.extracted_data.experiences_professionnelles.forEach((exp: any) => {
      if (typeof exp.resume_activites === 'string') {
        exp.resume_activites = exp.resume_activites.split('\n').filter((a: string) => a.trim() !== '');
      }
    });

    this.expertService.updateExpert(this.expertId, formValue).subscribe({
      next: () => {
        this.isSaving = false;
        this.router.navigate(['/experts/details', this.expertId]);
      },
      error: () => this.isSaving = false
    });
  }
  formatSlugFormSaisie(): void {
    const control = this.editForm.get('slug_unique');
    if (control && control.value) {
      let slug = control.value;
      slug = slug.normalize("NFD").replace(/[\u0300-\u036f]/g, "") // Enlève les accents
                 .toLowerCase() // Tout en minuscules
                 .replace(/\s+/g, '-') // Remplace les espaces par des tirets
                 .replace(/[^a-z0-9-]/g, '') // Supprime les caractères spéciaux
                 .replace(/-+/g, '-'); // Évite les tirets multiples 
      
      // Met à jour la valeur sans déclencher d'événement en boucle
      control.setValue(slug, { emitEvent: false });
    }
  }

  generateExpertSlug(nom: string, dateNaissance?: string | null): string {
  // 1. Sécurité si le nom est vide ou contient la valeur par défaut
  let nameToUse = nom ? nom.trim() : "";
  if (!nameToUse || nameToUse.toLowerCase().includes("nom et prenom")) {
    nameToUse = "expert_inconnu";
  }

  // 2. Nettoyage de base (minuscules, suppression des accents et caractères spéciaux)
  let nomClean = nameToUse
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // Supprime les accents
    .toLowerCase();
  
  nomClean = nomClean.replace(/[^a-z\s]/g, ""); // Garde uniquement lettres minuscules et espaces

  // 3. On trie les mots alphabétiquement
  const mots = nomClean.split(/\s+/).map(m => m.trim()).filter(m => m.length > 0);
  const motsTries = mots.sort(); // Tri alphabétique équivalent à sorted() en Python
  const nomOrdonne = motsTries.join("-");

  // 4. Normalisation de la date de naissance
  let dateStr = "sans-date";
  if (dateNaissance && typeof dateNaissance === 'string') {
    // Extrait uniquement les chiffres (équivalent de re.findall(r'\d+', ...))
    const chiffresDate = dateNaissance.replace(/\D/g, ""); 
    if (chiffresDate && chiffresDate.length >= 4) {
      dateStr = chiffresDate;
    }
  }

  return `${nomOrdonne}-${dateStr}`;
}
regenererSlugManuel(): void {
  const nom = this.editForm.get('nom_expert')?.value;
  const date = this.editForm.get('extracted_data.date_naissance')?.value;
  const slugControl = this.editForm.get('slug_unique');

  if (slugControl) {
    const nouveauSlug = this.generateExpertSlug(nom, date);
    slugControl.setValue(nouveauSlug);
    slugControl.markAsPristine();
  }
}
reanalyzeSection(sectionName: string) {
  this.isAnalyzingSection = sectionName;

  this.expertService.reanalyzeSection(this.expertId, sectionName).subscribe({
    next: (nouvellesDonnees: any) => {
      console.log(`📡 Données brutes reçues pour [${sectionName}] :`, nouvellesDonnees);

      // 🎯 Sécurité : Supporter plusieurs formes de réponse
      let source: any = nouvellesDonnees;
      if (source && source.extracted_data) {
        source = source.extracted_data;
      }
      if (source && source.expert) {
        source = source.expert;
      }
      if (source && source.identite) {
        source = source.identite;
      }

      // ==========================================
      // 1. SECTION IDENTITÉ (Informations Générales)
      // ==========================================
      if (sectionName === 'identite') {
        const extractedDataGroup = this.editForm.get('extracted_data');
        
        if (extractedDataGroup) {
          extractedDataGroup.patchValue({
            titre_poste_principal: source.titre_poste_principal || '',
            annees_experience_total: source.annees_experience_total !== undefined ? source.annees_experience_total : 0,
            nationalite: source.nationalite || '',
            date_naissance: source.date_naissance || ''
          });
          
          this.editForm.updateValueAndValidity();
          console.log("✅ Formulaire d'identité mis à jour avec succès !");
        } else {
          console.error("❌ Erreur : Le groupe 'extracted_data' est introuvable dans votre formulaire.");
        }
      }

      // ==========================================
      // 2. SECTION EXPÉRIENCES (Parcours Professionnel)
      // ==========================================
      else if (sectionName === 'experiences') {
        this.experiences.clear(); 

        let listeExperiences = source.experiences_professionnelles || source.experiences || [];
        
        if (listeExperiences.length === 0 && (source.projets_et_missions && source.projets_et_missions.length > 0)) {
          console.log("💡 Données d'expériences récupérées depuis 'projets_et_missions'");
          listeExperiences = source.projets_et_missions;
        }

        if (listeExperiences.length === 0) {
          alert("⚠️ L'IA n'a retourné aucun historique d'expérience.");
          this.isAnalyzingSection = null;
          return;
        }

        listeExperiences.forEach((exp: any) => {
          this.addItem(this.experiences, {
            poste: exp.poste || exp.poste_occupe || exp.titre_poste || '',
            periode: exp.periode || exp.annee || exp.date || '',
            employeur: exp.employeur || exp.client_ou_bailleur || exp.entreprise || '',
            pays: exp.pays || '',
            resume_activites: Array.isArray(exp.resume_activites) ? exp.resume_activites.join('\n') : exp.resume_activites || exp.nom_projet || exp.description || ''
          });
        });

        this.editForm.updateValueAndValidity();
        console.log(`✅ ${listeExperiences.length} expériences injectées dans le formulaire !`);
      }

      // ==========================================
      // 3. SECTION PROJETS (Projets & Missions)
      // ==========================================
      else if (sectionName === 'projets') {
        this.projets.clear();

        const projetsData = source.projets_et_missions || source.projets || [];

        if (!Array.isArray(projetsData) || projetsData.length === 0) {
          alert("⚠️ L'IA n'a retourné aucun projet ou mission.");
          this.isAnalyzingSection = null;
          return;
        }

        projetsData.forEach((proj: any) => {
          this.addItem(this.projets, {
            nom_projet: proj.nom_projet || proj.titre || proj.description || '',
            client_ou_bailleur: proj.client_ou_bailleur || proj.client || '',
            annee: proj.annee || proj.periode || '',
            pays: proj.pays || proj.pays_d_intervention || '',
            poste_occupe: proj.poste_occupe || proj.poste || ''
          });
        });

        this.editForm.updateValueAndValidity();
        console.log(`✅ ${projetsData.length} projets injectés dans le formulaire !`);
      }

      this.isAnalyzingSection = null;
    },
    error: (err) => {
      console.error(`❌ Erreur lors de la ré-analyse de ${sectionName}:`, err);
      alert("Une erreur est survenue lors de l'analyse.");
      this.isAnalyzingSection = null;
    }
  });
}
}