import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { formatDateTime, formatDuration, formatTime } from '../lib/format';

const ROBOT_PALETTE = [
  { bg: 'rgba(255, 165, 176, 0.45)', border: '#f05473', text: '#9f1239' },
  { bg: 'rgba(255, 224, 130, 0.5)', border: '#f59e0b', text: '#92400e' },
  { bg: 'rgba(168, 236, 191, 0.55)', border: '#22a559', text: '#166534' },
  { bg: 'rgba(167, 215, 255, 0.52)', border: '#1d72d8', text: '#1e3a8a' },
  { bg: 'rgba(224, 197, 255, 0.45)', border: '#9333ea', text: '#5b21b6' },
  { bg: 'rgba(255, 206, 160, 0.46)', border: '#ea580c', text: '#9a3412' },
  { bg: 'rgba(172, 247, 246, 0.5)', border: '#0d9488', text: '#115e59' },
  { bg: 'rgba(250, 208, 228, 0.45)', border: '#db2777', text: '#9d174d' },
];

const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;
const TIMELINE_PADDING_MS = 5 * MINUTE_MS;

const TRACK_INSET_PX = 16;
const MIN_CARD_WIDTH_PX = 108;

const CLOCK_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

const DAY_FORMATTER = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: '2-digit',
});

function toDate(value) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function hashLabel(value) {
  const base = String(value || 'Sem robo');
  let hash = 0;
  for (let index = 0; index < base.length; index += 1) {
    hash = (hash * 31 + base.charCodeAt(index)) >>> 0;
  }
  return hash;
}

function getRobotColor(robotName) {
  const colorIndex = hashLabel(robotName) % ROBOT_PALETTE.length;
  return ROBOT_PALETTE[colorIndex];
}

function clamp(value, min, max) {
  if (max < min) return min;
  return Math.min(Math.max(value, min), max);
}

function floorToStep(timestamp, stepMs) {
  return Math.floor(timestamp / stepMs) * stepMs;
}

function ceilToStep(timestamp, stepMs) {
  return Math.ceil(timestamp / stepMs) * stepMs;
}

function getStartOfLocalDayMs(value) {
  const date = new Date(value);
  date.setHours(0, 0, 0, 0);
  return date.getTime();
}

function getGridConfig(totalRangeMs) {
  const totalHours = totalRangeMs / HOUR_MS;

  if (totalHours <= 8) return { gridStepMs: 30 * MINUTE_MS, labelEvery: 2 };
  if (totalHours <= 18) return { gridStepMs: HOUR_MS, labelEvery: 2 };
  if (totalHours <= 36) return { gridStepMs: HOUR_MS, labelEvery: 3 };
  return { gridStepMs: 2 * HOUR_MS, labelEvery: 2 };
}

function getDaySuffix(startedAt, finishedAt) {
  if (!startedAt || !finishedAt) return '';

  const startDayMs = getStartOfLocalDayMs(startedAt);
  const endDayMs = getStartOfLocalDayMs(finishedAt);
  if (startDayMs === endDayMs) return '';

  const diffDays = Math.round((endDayMs - startDayMs) / DAY_MS);
  if (diffDays <= 0) return '';
  return `(+${diffDays}d)`;
}

function intervalsIntersectByTime(runA, runB) {
  return runA.startMs < runB.endMs && runB.startMs < runA.endMs;
}

function intervalsIntersectByVisualBox(runA, runB) {
  return runA.visualLeftPx < runB.visualRightPx && runB.visualLeftPx < runA.visualRightPx;
}

function collidesInLane(run, laneRuns) {
  return laneRuns.some((placedRun) => {
    return intervalsIntersectByTime(run, placedRun) || intervalsIntersectByVisualBox(run, placedRun);
  });
}

function buildDayLayout(timelineStartMs, timelineEndMs, totalMs) {
  const dayBoundaries = [];
  const dayLabels = [];

  const firstBoundary = getStartOfLocalDayMs(timelineStartMs) + DAY_MS;
  for (let boundaryMs = firstBoundary; boundaryMs < timelineEndMs; boundaryMs += DAY_MS) {
    dayBoundaries.push({
      timestamp: boundaryMs,
      offsetPct: ((boundaryMs - timelineStartMs) / totalMs) * 100,
    });
  }

  const segmentStarts = [timelineStartMs, ...dayBoundaries.map((item) => item.timestamp)];
  segmentStarts.forEach((segmentStartMs) => {
    dayLabels.push({
      timestamp: segmentStartMs,
      offsetPct: ((segmentStartMs - timelineStartMs) / totalMs) * 100,
      label: DAY_FORMATTER.format(new Date(segmentStartMs)),
    });
  });

  return {
    dayBoundaries,
    dayLabels,
  };
}

function buildTimeline(items) {
  const nowMs = Date.now();

  const normalizedRuns = items
    .map((item) => {
      const startedAt = toDate(item.started_at);
      if (!startedAt) return null;

      // Runs com status 'running' sempre se estendem até agora,
      // independente de finished_at (API pode retornar valor desatualizado)
      const isActiveRun = item.normalizedStatus === 'running' || item.status === 'running';
      const finishedAt = isActiveRun ? null : toDate(item.finished_at);
      const startMs = startedAt.getTime();
      const endMs = Math.max(startMs + 1, (finishedAt || new Date(nowMs)).getTime());

      return {
        ...item,
        startedAt,
        finishedAt,
        startMs,
        endMs,
      };
    })
    .filter(Boolean)
    .sort((left, right) => {
      if (left.startMs !== right.startMs) return left.startMs - right.startMs;
      if (left.endMs !== right.endMs) return left.endMs - right.endMs;
      return String(left.id).localeCompare(String(right.id));
    });

  if (!normalizedRuns.length) {
    return {
      runs: [],
      hourTicks: [],
      dayLabels: [],
      dayBoundaries: [],
      laneCount: 0,
      timelineWidthPx: 880,
      trackWidthPx: 848,
      nowTrackX: 0,
      timelineStartMs: 0,
      timelineEndMs: 0,
      totalMs: 0,
    };
  }

  const minStartMs = Math.min(...normalizedRuns.map((run) => run.startMs));
  const maxEndMs = Math.max(...normalizedRuns.map((run) => run.endMs));

  const roughRangeMs = Math.max(4 * HOUR_MS, maxEndMs - minStartMs);
  const { gridStepMs, labelEvery } = getGridConfig(roughRangeMs);

  const timelineStartMs = floorToStep(minStartMs - TIMELINE_PADDING_MS, gridStepMs);
  // Garante pelo menos um grid step de espaço após o ponto mais à direita,
  // evitando que a linha "agora" fique colada ao último tick visível
  const timelineEndMs = ceilToStep(maxEndMs + Math.max(TIMELINE_PADDING_MS, gridStepMs), gridStepMs);
  const totalMs = Math.max(gridStepMs, timelineEndMs - timelineStartMs);

  const totalHours = totalMs / HOUR_MS;
  const timelineWidthPx = Math.max(920, Math.round(totalHours * 120));
  const trackWidthPx = Math.max(760, timelineWidthPx - TRACK_INSET_PX * 2);

  const hourTicks = [];
  const labelEveryMs = gridStepMs * labelEvery;
  for (let tickMs = timelineStartMs; tickMs <= timelineEndMs; tickMs += gridStepMs) {
    const offsetPct = ((tickMs - timelineStartMs) / totalMs) * 100;
    const isEdge = tickMs === timelineStartMs || tickMs === timelineEndMs;
    const isDayBoundary = getStartOfLocalDayMs(tickMs) === tickMs;
    const showLabel = isEdge || isDayBoundary || (tickMs - timelineStartMs) % labelEveryMs === 0;

    hourTicks.push({
      timestamp: tickMs,
      offsetPct,
      label: showLabel ? CLOCK_FORMATTER.format(new Date(tickMs)) : null,
      emphasized: showLabel,
      isDayBoundary,
    });
  }

  const { dayBoundaries, dayLabels } = buildDayLayout(timelineStartMs, timelineEndMs, totalMs);

  const runsWithVisualBox = normalizedRuns.map((run) => {
    const realLeftPx = ((run.startMs - timelineStartMs) / totalMs) * trackWidthPx;
    const realWidthPx = Math.max(1, ((run.endMs - run.startMs) / totalMs) * trackWidthPx);

    const visualWidthPx = clamp(
      Math.max(realWidthPx, MIN_CARD_WIDTH_PX),
      MIN_CARD_WIDTH_PX,
      trackWidthPx
    );

    const visualLeftPx = clamp(realLeftPx, 0, trackWidthPx - visualWidthPx);
    const visualRightPx = visualLeftPx + visualWidthPx;

    const robotLabel = run.automation_name || run.automation_code || 'Robo sem nome';
    const titleLabel = run.client_name ? `${robotLabel} - ${run.client_name}` : robotLabel;
    const endLabel = run.finishedAt ? formatTime(run.finishedAt) : 'Em execucao';
    const daySuffix = getDaySuffix(run.startedAt, run.finishedAt);

    return {
      ...run,
      realLeftPx,
      realWidthPx,
      visualLeftPx,
      visualRightPx,
      visualWidthPx,
      titleLabel,
      statusLabel: run.finishedAt
        ? (['stopped', 'cancelled'].includes(run.status) ? 'Parado' : run.status === 'failed' ? 'Falha' : 'Concluido')
        : 'Em execucao',
      timeLabel: `${formatTime(run.startedAt)} | ${endLabel}${daySuffix ? ` ${daySuffix}` : ''}`,
      daySuffix,
      clampedLeft: run.startMs < timelineStartMs,
      clampedRight: run.endMs > timelineEndMs,
      color: getRobotColor(run.automation_name || run.automation_code || run.id),
      isExecutionRunning: !run.finishedAt,
    };
  });

  const lanes = [];
  const packedRuns = runsWithVisualBox.map((run) => {
    let laneIndex = 0;

    while (true) {
      if (!lanes[laneIndex]) {
        lanes[laneIndex] = [run];
        break;
      }

      if (!collidesInLane(run, lanes[laneIndex])) {
        lanes[laneIndex].push(run);
        break;
      }

      laneIndex += 1;
    }

    return {
      ...run,
      laneIndex,
      leftPct: (run.visualLeftPx / trackWidthPx) * 100,
      widthPct: (run.visualWidthPx / trackWidthPx) * 100,
      widthPx: run.visualWidthPx,
    };
  });

  const nowClampedMs = clamp(nowMs, timelineStartMs, timelineEndMs);
  const nowTrackX = TRACK_INSET_PX + ((nowClampedMs - timelineStartMs) / totalMs) * trackWidthPx;
  const nowOffsetPct = ((nowClampedMs - timelineStartMs) / totalMs) * 100;

  return {
    runs: packedRuns,
    hourTicks,
    dayLabels,
    dayBoundaries,
    laneCount: lanes.length,
    timelineWidthPx,
    trackWidthPx,
    nowTrackX,
    nowOffsetPct,
    timelineStartMs,
    timelineEndMs,
    totalMs,
  };
}

function getTooltipPosition(clientX, clientY) {
  const margin = 12;
  const gap = 14;
  const tooltipWidth = 300;
  const tooltipHeight = 190;

  let left = clientX + gap;
  let top = clientY + gap;

  if (left + tooltipWidth > window.innerWidth - margin) {
    left = clientX - tooltipWidth - gap;
  }
  if (top + tooltipHeight > window.innerHeight - margin) {
    top = clientY - tooltipHeight - gap;
  }

  return {
    left: Math.max(margin, left),
    top: Math.max(margin, top),
  };
}

function ExecutionTimeline({ items = [] }) {
  const timeline = useMemo(() => buildTimeline(items), [items]);
  const [tooltip, setTooltip] = useState(null);
  const [showNowTooltip, setShowNowTooltip] = useState(false);

  const scrollRef = useRef(null);
  const autoScrolledRef = useRef(false);

  useEffect(() => {
    if (!timeline.runs.length || autoScrolledRef.current) return;

    const scroller = scrollRef.current;
    if (!scroller) return;

    const maxScrollLeft = Math.max(0, scroller.scrollWidth - scroller.clientWidth);
    const targetScrollLeft = clamp(timeline.nowTrackX - scroller.clientWidth * 0.3, 0, maxScrollLeft);

    scroller.scrollLeft = targetScrollLeft;
    autoScrolledRef.current = true;
  }, [timeline.nowTrackX, timeline.runs.length, timeline.timelineWidthPx]);

  if (!timeline.runs.length) {
    return null;
  }

  const dayBandHeight = 20;
  const hourBandHeight = 20;
  const labelBandHeight = dayBandHeight + hourBandHeight;

  const laneHeight = 52;
  const laneGap = 6;
  const cardHeight = 44;

  const trackHeight = Math.max(52, timeline.laneCount * laneHeight + (timeline.laneCount - 1) * laneGap);
  const totalHeight = labelBandHeight + trackHeight;

  const hideTooltip = () => setTooltip(null);

  const showTooltip = (event, run) => {
    const position = getTooltipPosition(event.clientX, event.clientY);
    setTooltip({ run, ...position });
  };

  const moveTooltip = (event, run) => {
    const position = getTooltipPosition(event.clientX, event.clientY);
    setTooltip((current) => {
      if (!current || current.run.id !== run.id) {
        return { run, ...position };
      }
      return { ...current, ...position };
    });
  };

  return (
    <>
      <div ref={scrollRef} className="overflow-x-auto pb-2">
        <div
          className="relative rounded-2xl border border-app-border bg-app-surface/60 p-4"
          style={{ minWidth: `${timeline.timelineWidthPx}px`, height: `${totalHeight + 16}px` }}
        >
          <div className="absolute left-4 right-4 top-4" style={{ height: `${totalHeight}px` }}>
            {timeline.dayLabels.map((dayLabel, index) => {
              const isFirst = index === 0;
              return (
                <div
                  key={`day-label-${dayLabel.timestamp}`}
                  className="pointer-events-none absolute"
                  style={{ left: `${dayLabel.offsetPct}%`, top: 0 }}
                >
                  <span className={`absolute text-[11px] font-semibold text-app-accent ${isFirst ? 'left-0' : 'left-1'}`}>
                    {dayLabel.label}
                  </span>
                </div>
              );
            })}

            {timeline.dayBoundaries.map((boundary) => (
              <div
                key={`day-boundary-${boundary.timestamp}`}
                className="pointer-events-none absolute"
                style={{ left: `${boundary.offsetPct}%`, top: 0, bottom: 0 }}
              >
                <span className="absolute top-0 bottom-0 border-l border-app-accent/60" style={{ left: 0 }} />
              </div>
            ))}

            {timeline.hourTicks.map((tick, index) => {
              const isFirst = index === 0;
              const isLast = index === timeline.hourTicks.length - 1;

              return (
                <div
                  key={`hour-tick-${tick.timestamp}`}
                  className="pointer-events-none absolute"
                  style={{ left: `${tick.offsetPct}%`, top: 0, bottom: 0 }}
                >
                  {tick.label ? (
                    <span
                      className={`absolute text-xs font-semibold ${tick.emphasized ? 'text-app-text' : 'text-app-muted'} ${isFirst ? 'left-0' : isLast ? 'right-0' : 'left-0 -translate-x-1/2'
                        }`}
                      style={{ top: `${dayBandHeight}px` }}
                    >
                      {tick.label}
                    </span>
                  ) : null}

                  <span
                    className={`absolute border-l border-dashed ${tick.isDayBoundary
                      ? 'border-app-accent/70'
                      : tick.emphasized
                        ? 'border-app-border'
                        : 'border-app-border/60'
                      }`}
                    style={{ left: 0, top: `${labelBandHeight}px`, bottom: 0 }}
                  />
                </div>
              );
            })}

            <div className="absolute left-0 right-0" style={{ top: `${labelBandHeight}px` }}>
              {/* Linha "agora" */}
              <div
                className="pointer-events-none absolute top-0 bottom-0 z-10"
                style={{ left: `${timeline.nowOffsetPct}%` }}
              >
                {/* Linha tracejada roxa */}
                <div
                  className="absolute top-0 bottom-0 border-l-2 border-dashed border-app-accent/70"
                  style={{ left: 0 }}
                />
                {/* Label interativo com tooltip de horário */}
                <div
                  className="pointer-events-auto absolute left-1 cursor-default"
                  style={{ top: `${-(labelBandHeight - 4)}px` }}
                  onMouseEnter={() => setShowNowTooltip(true)}
                  onMouseLeave={() => setShowNowTooltip(false)}
                >
                  <span className="text-[9px] font-bold uppercase tracking-wider text-app-accent">
                    agora
                  </span>
                  {showNowTooltip && (
                    <div className="absolute left-0 top-full mt-1.5 whitespace-nowrap rounded-lg border border-app-accent/30 bg-[#2b114a] px-2.5 py-1.5 text-[11px] font-bold text-white shadow-lg z-30">
                      {new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
                    </div>
                  )}
                </div>
              </div>

              {timeline.runs.map((run) => {
                const top = run.laneIndex * (laneHeight + laneGap) + (laneHeight - cardHeight) / 2;
                const isRunning = run.isExecutionRunning;
                const isFailed = run.normalizedStatus === 'failed' || run.alertTone === 'critical';
                const compact = run.widthPx < 100;

                const borderColor = isRunning ? '#f59e0b' : isFailed ? '#ef4444' : '#22c55e';
                const bgColor = isRunning
                  ? 'rgba(255, 251, 235, 0.95)'
                  : isFailed
                    ? 'rgba(254, 242, 242, 0.95)'
                    : 'rgba(240, 253, 244, 0.95)';
                const textColor = isRunning ? '#92400e' : isFailed ? '#991b1b' : '#166534';

                return (
                  <Link
                    key={run.id}
                    to={`/runs/${run.id}`}
                    onMouseEnter={(event) => showTooltip(event, run)}
                    onMouseMove={(event) => moveTooltip(event, run)}
                    onMouseLeave={hideTooltip}
                    className="group absolute block overflow-hidden rounded-lg border text-left shadow-sm transition hover:shadow-md hover:brightness-95"
                    style={{
                      left: `${run.leftPct}%`,
                      width: `${run.widthPct}%`,
                      top: `${top}px`,
                      height: `${cardHeight}px`,
                      backgroundColor: bgColor,
                      borderColor,
                      borderLeftWidth: '3px',
                      color: textColor,
                    }}
                  >
                    <div className="flex h-full flex-col justify-center px-2 py-1 overflow-hidden">
                      <div className="flex items-center gap-1.5 min-w-0">
                        {isRunning && (
                          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500 animate-pulse" />
                        )}
                        <span className="truncate text-[11px] font-semibold leading-tight">
                          {run.titleLabel}
                        </span>
                      </div>
                      {!compact && (
                        <span className="truncate text-[10px] opacity-70 leading-tight mt-0.5">
                          {run.timeLabel}
                        </span>
                      )}
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {tooltip ? (
        <div
          className="pointer-events-none fixed z-50 max-w-[300px] rounded-xl border border-app-border bg-app-surface px-3 py-2.5 text-xs text-app-text shadow-card"
          style={{ left: `${tooltip.left}px`, top: `${tooltip.top}px` }}
        >
          <p className="truncate text-sm font-semibold">{tooltip.run.automation_name || tooltip.run.automation_code || 'Robo sem nome'}</p>
          {tooltip.run.client_name ? <p className="mt-0.5 truncate text-app-muted">Cliente: {tooltip.run.client_name}</p> : null}

          <div className="mt-2 space-y-1 text-[11px] text-app-muted">
            <p>
              <span className="font-semibold text-app-text">Inicio:</span> {formatDateTime(tooltip.run.startedAt)}
            </p>
            <p>
              <span className="font-semibold text-app-text">Fim:</span>{' '}
              {tooltip.run.finishedAt ? formatDateTime(tooltip.run.finishedAt) : 'Em execucao'}
            </p>
            <p>
              <span className="font-semibold text-app-text">Status:</span> {tooltip.run.statusLabel}
            </p>
            <p>
              <span className="font-semibold text-app-text">Duracao:</span>{' '}
              {formatDuration(tooltip.run.startedAt, tooltip.run.finishedAt)}
            </p>
            {tooltip.run.clampedLeft || tooltip.run.clampedRight ? (
              <p className="font-semibold text-amber-700">Intervalo visivel parcial nesta janela.</p>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  );
}

export default ExecutionTimeline;
