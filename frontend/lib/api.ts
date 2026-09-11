export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function createScan(url: string) {
  const response = await fetch(`${API_BASE_URL}/api/v1/scans`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail?.message || 'Scan failed');
  }

  return response.json();
}

export async function getScan(scanId: string) {
  const response = await fetch(`${API_BASE_URL}/api/v1/scans/${scanId}`);
  
  if (!response.ok) {
    throw new Error('Scan not found');
  }

  return response.json();
}

export async function getReport(scanId: string) {
  const response = await fetch(`${API_BASE_URL}/api/v1/scans/${scanId}/report`);
  
  if (!response.ok) {
    throw new Error('Report not found');
  }

  return response.json();
}