import { getScan } from '@/lib/api';
import { ScanResultsClient } from './ScanResultsClient';
import { notFound } from 'next/navigation';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ScanPage({ params }: PageProps) {
  const { id } = await params;

  try {
    const scan = await getScan(id);
    return <ScanResultsClient initialScan={scan} />;
  } catch {
    notFound();
  }
}