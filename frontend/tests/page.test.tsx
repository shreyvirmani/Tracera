import { render, screen } from '@testing-library/react';
import Home from '@/app/page';

describe('Home page', () => {
  it('renders Tracera title', () => {
    render(<Home />);
    expect(screen.getByText('Tracera')).toBeInTheDocument();
  });

  it('renders subtitle', () => {
    render(<Home />);
    expect(screen.getByText('Website Risk Assessment Platform')).toBeInTheDocument();
  });

  it('renders scan form', () => {
    render(<Home />);
    expect(screen.getByLabelText('Website URL')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Start Scan/i })).toBeInTheDocument();
  });

  it('renders authorization notice', () => {
    render(<Home />);
    expect(screen.getByText(/authorization to test/i)).toBeInTheDocument();
  });
});
