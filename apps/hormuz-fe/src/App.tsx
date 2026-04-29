import { AppProviders } from './app/providers'
import { ScanPage } from './features/scan/pages/ScanPage'

export default function App() {
  return (
    <AppProviders>
      <ScanPage />
    </AppProviders>
  )
}

