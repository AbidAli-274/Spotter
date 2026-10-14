import { useMutation } from '@tanstack/react-query';

import { api } from '../api/client';
import type { TripRequest } from '../api/types';

export function useAnalyzeTrip() {
  return useMutation({ mutationFn: (payload: TripRequest) => api.analyzeTrip(payload) });
}
