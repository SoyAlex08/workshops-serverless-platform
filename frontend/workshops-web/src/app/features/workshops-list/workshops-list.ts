import { Component, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { WorkshopsApiService } from '../../core/api/workshops-api.service';
import { Workshop } from '../../core/models/workshop.model';

@Component({
  selector: 'app-workshops-list',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './workshops-list.html',
})
export class WorkshopsList implements OnInit {
  readonly workshops = signal<Workshop[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  constructor(private readonly api: WorkshopsApiService) {}

  ngOnInit(): void {
    this.api.list().subscribe({
      next: (res) => {
        this.workshops.set(res.items);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No se pudieron cargar los talleres');
        this.loading.set(false);
      },
    });
  }
}
