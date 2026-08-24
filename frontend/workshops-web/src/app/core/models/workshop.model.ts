export interface Workshop {
  id: string;
  name: string;
  description?: string;
  category: string;
  location: string;
  startAt: number;
  endAt: number;
  status: 'scheduled' | 'cancelled';
  capacity: number;
  createdAt?: number;
  updatedAt?: number;
}

export interface WorkshopInput {
  name: string;
  description?: string;
  category: string;
  location: string;
  startAt: number;
  endAt: number;
  status?: 'scheduled' | 'cancelled';
  capacity: number;
}

export interface WorkshopListResponse {
  items: Workshop[];
  nextToken?: string | null;
}
