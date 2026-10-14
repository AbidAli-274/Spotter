import { fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { TripForm } from './TripForm';

function setup(onSubmit = vi.fn()) {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <TripForm loading={false} onSubmit={onSubmit} />
    </QueryClientProvider>,
  );
  return onSubmit;
}

describe('TripForm', () => {
  it('requires origin and destination', () => {
    const onSubmit = setup();
    fireEvent.click(screen.getByRole('button', { name: /Find safest route/ }));
    expect(screen.getByRole('alert')).toHaveTextContent(/origin and a destination/);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('rejects an invalid load weight', () => {
    const onSubmit = setup();
    fireEvent.click(screen.getByRole('button', { name: /Try an example/ }));
    fireEvent.change(screen.getByLabelText(/Load weight/), { target: { value: '999999' } });
    fireEvent.click(screen.getByRole('button', { name: /Find safest route/ }));
    expect(screen.getByRole('alert')).toHaveTextContent(/Load weight/);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits a normalized request', () => {
    const onSubmit = setup();
    fireEvent.click(screen.getByRole('button', { name: /Try an example/ }));
    fireEvent.click(screen.getByLabelText('50 mi'));
    fireEvent.click(screen.getByRole('button', { name: /Find safest route/ }));
    expect(onSubmit).toHaveBeenCalledOnce();
    const request = onSubmit.mock.calls[0][0];
    expect(request).toMatchObject({
      origin: { label: 'Chicago, IL' },
      destination: { label: 'Denver, CO' },
      load_lb: 42000,
      interval_mi: 50,
    });
    expect(new Date(request.departure).toISOString()).toBe(request.departure);
  });
});
