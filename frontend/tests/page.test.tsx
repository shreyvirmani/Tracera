import { render, screen, waitFor } from '@testing-library/react';
import Home from '@/app/page';

global.fetch = jest.fn();

describe('Dashboard page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        scans: [],
        total: 0,
        limit: 5,
        offset: 0,
      }),
    });
  });

  it('renders Dashboard title', () => {
    render(<Home />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('renders overview description', () => {
    render(<Home />);
    expect(screen.getByText(/Overview of your security scanning activity/i)).toBeInTheDocument();
  });

  it('renders stats cards after loading', async () => {
    render(<Home />);
    await waitFor(() => {
      expect(screen.getByText('Total Scans')).toBeInTheDocument();
      expect(screen.getByText('Total Findings')).toBeInTheDocument();
      expect(screen.getByText('Critical Issues')).toBeInTheDocument();
      expect(screen.getByText('Avg Risk Score')).toBeInTheDocument();
    });
  });

  it('renders quick actions section after loading', async () => {
    render(<Home />);
    await waitFor(() => {
      expect(screen.getByText('Quick Actions')).toBeInTheDocument();
      expect(screen.getByText('Start New Scan')).toBeInTheDocument();
      expect(screen.getByText('View Scan History')).toBeInTheDocument();
    });
  });

  it('renders recent scans section after loading', async () => {
    render(<Home />);
    await waitFor(() => {
      expect(screen.getByText('Recent Scans')).toBeInTheDocument();
    });
  });

  it('shows empty state when no scans', async () => {
    render(<Home />);
    await waitFor(() => {
      expect(screen.getByText('No scans yet')).toBeInTheDocument();
    });
  });

  it('shows new scan button after loading', async () => {
    render(<Home />);
    await waitFor(() => {
      const links = screen.getAllByRole('link', { name: /New Scan/i });
      expect(links.length).toBeGreaterThan(0);
    });
  });
});