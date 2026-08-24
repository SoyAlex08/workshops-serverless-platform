import { Component, OnInit, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { WorkshopsApiService } from '../../core/api/workshops-api.service';
import { Workshop } from '../../core/models/workshop.model';

@Component({
  selector: 'app-workshop-detail',
  standalone: true,
  imports: [],
  templateUrl: './workshop-detail.html',
})
export class WorkshopDetail implements OnInit {
  readonly workshop = signal<Workshop | null>(null);
  readonly loading = signal(true);
  readonly registering = signal(false);
  readonly registerMessage = signal<string | null>(null);
  readonly registerError = signal<string | null>(null);

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: WorkshopsApiService,
    readonly auth: AuthService,
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id')!;
    this.api.get(id).subscribe({
      next: (w) => {
        this.workshop.set(w);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  register(): void {
    const workshop = this.workshop();
    if (!workshop) return;

    this.registering.set(true);
    this.registerError.set(null);
    this.api.register(workshop.id).subscribe({
      next: () => {
        this.registerMessage.set('¡Inscripción confirmada!');
        this.registering.set(false);
      },
      error: (err) => {
        const detail = err?.error?.detail ?? 'No se pudo completar la inscripción';
        this.registerError.set(detail);
        this.registering.set(false);
      },
    });
  }
}
