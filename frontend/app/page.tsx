'use client';

import ScanForm from '@/components/ScanForm';

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-16 sm:py-24">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900">Tracera</h1>
          <p className="mt-4 text-xl text-gray-600">Website Risk Assessment Platform</p>
          <p className="mt-2 text-lg text-gray-500">
            Submit a URL to analyze its security configuration and risk profile
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
          <ScanForm />
        </div>

        <div className="mt-12 text-center">
          <p className="text-gray-500">
            By scanning, you confirm you have authorization to test this website. Tracera performs
            passive analysis only - no exploitation or intrusive testing.
          </p>
        </div>
      </div>
    </main>
  );
}
