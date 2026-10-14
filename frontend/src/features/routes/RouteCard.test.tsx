import { fireEvent, render, screen } from '@testing-library/react';

import { route } from '../../test/fixtures';
import { RouteCard } from './RouteCard';

describe('RouteCard', () => {
  it('shows recommendation, key metrics and a No Travel warning', () => {
    render(<RouteCard route={route} color="#123456" selected onSelect={() => {}} />);
    expect(screen.getByText('Recommended')).toBeInTheDocument();
    expect(screen.getByText('200 mi')).toBeInTheDocument();
    expect(screen.getByText('4h 00m')).toBeInTheDocument();
    expect(screen.getByText(/5 mi of No Travel/)).toBeInTheDocument();
    expect(screen.getByText('Worst: No Travel')).toBeInTheDocument();
  });

  it('selects on click and toggles the checkpoint table', () => {
    const onSelect = vi.fn();
    render(<RouteCard route={route} color="#123456" selected={false} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole('button', { name: /Route A/ }));
    expect(onSelect).toHaveBeenCalledOnce();

    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Show 2 checkpoints/ }));
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByText('Unknown')).toBeInTheDocument(); // checkpoint without forecast
  });
});
