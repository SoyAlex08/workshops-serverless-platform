import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from '../auth/auth.service';
import { Workshop, WorkshopInput, WorkshopListResponse } from '../models/workshop.model';

@Injectable({ providedIn: 'root' })
export class WorkshopsApiService {
  private readonly baseUrl = `${environment.apiBaseUrl}/workshops`;

  constructor(private readonly http: HttpClient, private readonly auth: AuthService) {}

  private authHeaders(): HttpHeaders {
    const token = this.auth.getIdToken();
    return token ? new HttpHeaders({ Authorization: token }) : new HttpHeaders();
  }

  list(category?: string, nextToken?: string): Observable<WorkshopListResponse> {
    let url = this.baseUrl;
    const params: string[] = [];
    if (category) params.push(`category=${encodeURIComponent(category)}`);
    if (nextToken) params.push(`nextToken=${encodeURIComponent(nextToken)}`);
    if (params.length) url += `?${params.join('&')}`;
    return this.http.get<WorkshopListResponse>(url);
  }

  get(id: string): Observable<Workshop> {
    return this.http.get<Workshop>(`${this.baseUrl}/${id}`);
  }

  create(input: WorkshopInput): Observable<Workshop> {
    return this.http.post<Workshop>(this.baseUrl, input, { headers: this.authHeaders() });
  }

  update(id: string, input: Partial<WorkshopInput>): Observable<Workshop> {
    return this.http.put<Workshop>(`${this.baseUrl}/${id}`, input, { headers: this.authHeaders() });
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`, { headers: this.authHeaders() });
  }

  register(id: string): Observable<{ workshopId: string; userId: string; registeredAt: number }> {
    return this.http.post<{ workshopId: string; userId: string; registeredAt: number }>(
      `${this.baseUrl}/${id}/register`,
      {},
      { headers: this.authHeaders() },
    );
  }
}
