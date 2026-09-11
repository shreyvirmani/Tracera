import { ScanForm } from '@/components/ScanForm';
import { ScanResults } from '@/components/ScanResults';
import { useState } from 'react';

export default function HomePage() {
  const [scanId, setScanId] = useState<string | null>(null);
  const [view, setView] = useState<'form' | 'results'>('form');

  const handleScanComplete = (id: string) => {
    setScanId(id);
    setView('results');
  };

  const handleNewScan = () => {
    setScanId(null);
    setView('form');
  };

  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <header className="text-center mb-10">
          <h1 className="text-4xl font-bold text-gray-900">Tracera</h1>
          <p className="text-gray-600 mt-2">Defensive website risk assessment</p>
        </header>

        {view === 'form' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
            <ScanForm onScanComplete={handleScanComplete} />
          </div>
        )}

        {view === 'results' && scanId && (
          <ScanResults scanId={scanId} onNewScan={handleNewScan} />
        )}
      </div>
    </main>
  );
}