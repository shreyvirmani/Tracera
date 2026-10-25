import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import Home from '@/app/page';

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

const mockRouter = useRouter as jest.Mock;

describe('Landing page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRouter.mockReturnValue({ push: jest.fn() });
  });

  it('renders the product proposition', () => {
    render(<Home />);
    expect(screen.getByText(/Understand your website's security posture/i)).toBeInTheDocument();
  });

  it('renders the URL scan input', () => {
    render(<Home />);
    expect(screen.getByLabelText(/Website URL to scan/i)).toBeInTheDocument();
  });

  it('renders the how-it-works section', () => {
    render(<Home />);
    expect(screen.getByText('How Tracera works')).toBeInTheDocument();
    expect(screen.getByText('Validate the target')).toBeInTheDocument();
    expect(screen.getByText('Run deterministic rules')).toBeInTheDocument();
  });

  it('renders the finding areas section based on real rule categories', () => {
    render(<Home />);
    expect(screen.getByText('What Tracera checks')).toBeInTheDocument();
    expect(screen.getByText('Security headers')).toBeInTheDocument();
    expect(screen.getByText('Cookie handling')).toBeInTheDocument();
  });

  it('explains risk scoring honestly', () => {
    render(<Home />);
    expect(screen.getByText('Risk scoring you can reason about')).toBeInTheDocument();
    expect(
      screen.getByText(/not a probability of compromise/i)
    ).toBeInTheDocument();
  });

  it('marks the product preview as illustrative', () => {
    render(<Home />);
    expect(screen.getByText('Illustrative preview')).toBeInTheDocument();
  });

  it('navigates to the scan page with a valid URL', () => {
    const push = jest.fn();
    mockRouter.mockReturnValue({ push });
    render(<Home />);
    const input = screen.getByLabelText(/Website URL to scan/i);
    fireEvent.change(input, { target: { value: 'https://example.com' } });
    fireEvent.submit(input.closest('form')!);
    expect(push).toHaveBeenCalledWith('/scan?url=https%3A%2F%2Fexample.com');
  });

  it('shows a validation error for an invalid URL', () => {
    render(<Home />);
    const input = screen.getByLabelText(/Website URL to scan/i);
    fireEvent.change(input, { target: { value: 'not a url' } });
    fireEvent.submit(input.closest('form')!);
    expect(screen.getByRole('alert')).toHaveTextContent(/valid HTTP or HTTPS URL/i);
    expect(mockRouter().push).not.toHaveBeenCalled();
  });

  it('renders footer navigation', () => {
    render(<Home />);
    expect(screen.getByLabelText('Footer navigation')).toBeInTheDocument();
  });
});
