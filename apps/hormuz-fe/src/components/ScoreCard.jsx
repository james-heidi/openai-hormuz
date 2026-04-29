import { useEffect, useRef, useState } from 'react';
import { animate, useMotionValue, useTransform, motion } from 'framer-motion';
import clsx from 'clsx';

const DEFAULT_THRESHOLDS = { good: 80, warn: 50 };

function pickNumberClass(score, thresholds) {
  if (score === null || score === undefined) return 'score-number-idle';
  if (score >= thresholds.good) return 'score-number-good';
  if (score >= thresholds.warn) return 'score-number-mid';
  return 'score-number-bad';
}

function pickScoreClass(score, thresholds) {
  if (score === null || score === undefined) return 'score-panel-idle';
  if (score >= thresholds.good) return 'score-panel-good';
  if (score >= thresholds.warn) return 'score-panel-mid';
  return 'score-panel-bad';
}

function pickAssessment(score, thresholds) {
  if (score === null || score === undefined) return 'Awaiting scan';
  if (score >= thresholds.good) return 'Controlled posture';
  if (score >= thresholds.warn) return 'Needs review';
  return 'Critical risk';
}

export default function ScoreCard({
  score,
  projectedScore,
  label = 'Score',
  thresholds = DEFAULT_THRESHOLDS,
}) {
  const display = useMotionValue(0);
  const rounded = useTransform(display, (v) => Math.round(v));
  const isFirstScoreRef = useRef(true);
  const [, force] = useState(0);

  useEffect(() => {
    if (typeof score !== 'number') return;
    if (isFirstScoreRef.current) {
      isFirstScoreRef.current = false;
      display.set(0);
    }
    const controls = animate(display, score, {
      duration: 1.5,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: () => force((n) => n + 1),
    });
    return () => controls.stop();
  }, [score, display]);

  const hasScore = typeof score === 'number';
  const numberClass = pickNumberClass(score, thresholds);
  const scoreClass = pickScoreClass(score, thresholds);
  const assessment = pickAssessment(score, thresholds);
  const hasProjectedScore = typeof projectedScore === 'number';

  return (
    <motion.div
      className={clsx(
        'glass-panel-strong theme-transition flex h-full min-h-[200px] flex-col justify-between rounded-lg p-5',
        scoreClass,
      )}
      initial={false}
      animate={{ opacity: hasScore ? 1 : 0.7 }}
    >
      <div>
        <div className="text-xs font-medium uppercase tracking-wider text-text-dim">
          {label}
        </div>
        <div className="mt-3 font-mono text-6xl leading-none">
          {hasScore ? (
            <motion.span className={clsx('theme-transition', numberClass)}>
              {rounded.get()}
            </motion.span>
          ) : (
            <span className="score-number-idle">—</span>
          )}
        </div>
      </div>
      <div>
        <div className="text-sm font-medium text-text">{assessment}</div>
        <div className="mt-1 text-[11px] text-text-dim">
          out of 100
        </div>
        {hasProjectedScore && (
          <div className="mt-1 font-mono text-[11px] text-accent">
            projected {projectedScore}
          </div>
        )}
      </div>
    </motion.div>
  );
}
