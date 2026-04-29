import ScoreCard from '../../../components/ScoreCard';

export default function ComplianceScore({ score }) {
  return (
    <ScoreCard
      score={score}
      label="Compliance Score"
      thresholds={{ good: 80, warn: 50 }}
    />
  );
}
