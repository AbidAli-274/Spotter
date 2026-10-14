import { heatmap } from '../test/fixtures';
import { heatmapFrame, worstLevelByHour } from './heatmap';

describe('heatmap helpers', () => {
  it('builds one feature per point with the level for the chosen hour', () => {
    const frame = heatmapFrame(heatmap, 1);
    expect(frame.features.map((f) => f.properties.level)).toEqual([2, 3]);
    expect(frame.features[0].geometry.coordinates).toEqual([-100, 40]);
  });

  it('clamps unknown levels to zero heat and the hour to the valid range', () => {
    expect(heatmapFrame(heatmap, 3).features.map((f) => f.properties.level)).toEqual([0, 0]);
    expect(heatmapFrame(heatmap, 99).features).toHaveLength(2);
    expect(heatmapFrame(heatmap, -5).features[0].properties.level).toBe(0);
  });

  it('reports the worst level per hour', () => {
    expect(worstLevelByHour(heatmap)).toEqual([1, 3, 4, -1]);
  });
});
