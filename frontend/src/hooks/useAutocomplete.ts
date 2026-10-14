import { useQuery } from '@tanstack/react-query';

import { api } from '../api/client';
import { useDebounce } from './useDebounce';

export function useAutocomplete(text: string, enabled: boolean) {
  const query = useDebounce(text.trim(), 300);
  return useQuery({
    queryKey: ['autocomplete', query],
    queryFn: ({ signal }) => api.autocomplete(query, signal),
    enabled: enabled && query.length >= 3,
    staleTime: 10 * 60_000,
    retry: false,
  });
}
