import ActionPanel from '../../../components/ActionPanel';

export default function ScanPanel({ disabled, onScan }) {
  return (
    <ActionPanel
      disabled={disabled}
      onRun={onScan}
      label="Scan target"
      placeholder="Path or URL to a Git repository"
      buttonLabel={disabled ? 'Scanning…' : 'Scan'}
      helperText="Local path, branch URL, or hosted repository."
    />
  );
}
