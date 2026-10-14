import { defaultDeparture, formatDuration, formatMiles, toLocalInputValue } from './format';

describe('format', () => {
  it('formats durations', () => {
    expect(formatDuration(45 * 60)).toBe('45m');
    expect(formatDuration(3600 + 5 * 60)).toBe('1h 05m');
    expect(formatDuration(27 * 3600)).toBe('27h 00m');
  });

  it('formats miles with grouping', () => {
    expect(formatMiles(1243.4)).toBe('1,243 mi');
  });

  it('builds a datetime-local value in local time', () => {
    expect(toLocalInputValue(new Date(2026, 0, 5, 7, 3))).toBe('2026-01-05T07:03');
  });

  it('defaults departure to the next top of the hour', () => {
    const d = defaultDeparture(new Date(2026, 0, 5, 10, 40), 30);
    expect(d.getMinutes()).toBe(0);
    expect(d.getTime()).toBeGreaterThan(new Date(2026, 0, 5, 11, 10).getTime() - 1);
  });
});
