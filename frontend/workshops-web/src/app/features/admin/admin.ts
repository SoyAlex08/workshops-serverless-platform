import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { WorkshopsApiService } from '../../core/api/workshops-api.service';
import { Workshop, WorkshopInput } from '../../core/models/workshop.model';

const EMPTY_FORM: WorkshopInput = {
  name: '',
  description: '',
  category: '',
  location: '',
  startAt: Math.floor(Date.now() / 1000),
  endAt: Math.floor(Date.now() / 1000) + 3600,
  status: 'scheduled',
  capacity: 20,
};

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './admin.html',
})
export class Admin implements OnInit {
  readonly workshops = signal<Workshop[]>([]);
  readonly editingId = signal<string | null>(null);
  readonly error = signal<string | null>(null);
  form: WorkshopInput = { ...EMPTY_FORM };

  constructor(private readonly api: WorkshopsApiService) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.api.list().subscribe((res) => this.workshops.set(res.items));
  }

  edit(w: Workshop): void {
    this.editingId.set(w.id);
    this.form = {
      name: w.name,
      description: w.description,
      category: w.category,
      location: w.location,
      startAt: w.startAt,
      endAt: w.endAt,
      status: w.status,
      capacity: w.capacity,
    };
  }

  resetForm(): void {
    this.editingId.set(null);
    this.form = { ...EMPTY_FORM };
    this.error.set(null);
  }

  save(): void {
    this.error.set(null);
    const id = this.editingId();
    const payload = this.form;
    const request = id ? this.api.update(id, payload) : this.api.create(payload);

    request.subscribe({
      next: () => {
        this.resetForm();
        this.refresh();
      },
      error: (err) => this.error.set(err?.error?.detail ?? 'Error al guardar el taller'),
    });
  }

  remove(w: Workshop): void {
    if (!confirm(`¿Eliminar el taller "${w.name}"?`)) return;
    this.api.delete(w.id).subscribe({
      next: () => this.refresh(),
      error: (err) => this.error.set(err?.error?.detail ?? 'Error al eliminar el taller'),
    });
  }
}
