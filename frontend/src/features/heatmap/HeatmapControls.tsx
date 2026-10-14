import { useEffect } from 'react';

import type { Heatmap } from '../../api/types';
import { hourLabel, worstLevelByHour } from '../../lib/heatmap';
import { RISK_COLORS_BY_VALUE, UNKNOWN_COLOR } from '../../lib/risk';
import { useMemo } from 'react';

interface Props {
  heatmap: Heatmap;
  hour: number;
  onHourChange: (hour: number) => void;
  playing: boolean;
  onPlayingChange: (playing: boolean) => void;
  visible: boolean;
  onVisibleChange: (visible: boolean) => void;
}

const FRAME_MS = 450;

export function HeatmapControls({
  heatmap,
  hour,
  onHourChange,
  playing,
  onPlayingChange,
  visible,
  onVisibleChange,
}: Props) {
  const strip = useMemo(() => worstLevelByHour(heatmap), [heatmap]);
  const last = heatmap.hours - 1;

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => onHourChange(hour >= last ? 0 : hour + 1), FRAME_MS);
    return () => clearInterval(id);
  }, [playing, hour, last, onHourChange]);

  return (
    <section className="heat-controls" aria-label="Weather heatmap forecast">
      <div className="heat-top">
        <label className="toggle">
          <input
            type="checkbox"
            checked={visible}
            onChange={(e) => onVisibleChange(e.target.checked)}
          />
          Weather heatmap
        </label>
        <output className="heat-time" htmlFor="heat-hour">
          +{hour}h · {hourLabel(heatmap, hour)}
        </output>
      </div>
      <div className="heat-slider">
        <button
          type="button"
          className="icon-btn"
          onClick={() => onPlayingChange(!playing)}
          disabled={!visible}
          aria-label={playing ? 'Pause animation' : 'Play animation'}
        >
          {playing ? '❚❚' : '▶'}
        </button>
        <div className="slider-col">
          <input
            id="heat-hour"
            type="range"
            min={0}
            max={last}
            step={1}
            value={hour}
            disabled={!visible}
            onChange={(e) => {
              onPlayingChange(false);
              onHourChange(Number(e.target.value));
            }}
            aria-label="Forecast hour, 0 to 48"
          />
          <div className="strip" aria-hidden="true">
            {strip.map((level, h) => (
              <i
                key={h}
                className={h === hour ? 'now' : undefined}
                style={{ background: level < 0 ? UNKNOWN_COLOR : RISK_COLORS_BY_VALUE[level] }}
              />
            ))}
          </div>
        </div>
      </div>
      <p className="muted small">
        Worst corridor conditions by hour (strip) for your load. Hour 0 = departure.
      </p>
    </section>
  );
}
