import ScoreCard from '../../../components/ScoreCard';

export default function ComplianceScore({ score, projectedScore }) {
  return (
    <ScoreCard
      score={score}
      projectedScore={projectedScore}
      label="Compliance Score"
      thresholds={{ good: 80, warn: 50 }}
    />
  );
}
