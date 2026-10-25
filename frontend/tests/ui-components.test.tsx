import { render, screen, fireEvent } from '@testing-library/react';
import { Button, ButtonGroup } from '@/components/ui/Button';
import { IconButton } from '@/components/ui/IconButton';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Modal, ConfirmModal } from '@/components/ui/Modal';

describe('Button', () => {
  it('renders button with children', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: /Click me/i })).toBeInTheDocument();
  });

  it('applies variant classes', () => {
    render(<Button variant="secondary">Secondary</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-surface');
  });

  it('applies size classes', () => {
    render(<Button size="lg">Large</Button>);
    expect(screen.getByRole('button')).toHaveClass('px-6');
  });

  it('shows loading state', () => {
    render(<Button loading>Loading</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByRole('button')).toContainHTML('svg');
  });

  it('handles disabled state', () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('applies fullWidth class', () => {
    render(<Button fullWidth>Full Width</Button>);
    expect(screen.getByRole('button')).toHaveClass('w-full');
  });
});

describe('ButtonGroup', () => {
  it('renders buttons in a group', () => {
    render(
      <ButtonGroup>
        <Button>One</Button>
        <Button>Two</Button>
        <Button>Three</Button>
      </ButtonGroup>
    );
    expect(screen.getByRole('group')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /One/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Two/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Three/i })).toBeInTheDocument();
  });

  it('applies vertical layout', () => {
    render(
      <ButtonGroup vertical>
        <Button>One</Button>
        <Button>Two</Button>
      </ButtonGroup>
    );
    expect(screen.getByRole('group')).toHaveClass('flex-col');
  });
});

describe('IconButton', () => {
  it('renders with aria-label', () => {
    render(
      <IconButton ariaLabel="Close" variant="ghost">
        <svg data-testid="icon" />
      </IconButton>
    );
    expect(screen.getByRole('button', { name: /Close/i })).toBeInTheDocument();
  });
});

describe('Card', () => {
  it('renders card with children', () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('applies variant classes', () => {
    render(<Card variant="elevated">Elevated</Card>);
    expect(screen.getByText('Elevated').closest('div')).toHaveClass('shadow-lg');
  });

  it('applies padding', () => {
    render(<Card padding="sm">Small padding</Card>);
    expect(screen.getByText('Small padding').closest('div')).toHaveClass('p-4');
  });

  it('applies hover effect', () => {
    render(<Card hover>Hoverable</Card>);
    expect(screen.getByText('Hoverable').closest('div')).toHaveClass('hover:shadow-md');
  });
});

describe('Card sub-components', () => {
  it('renders CardHeader', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Title</CardTitle>
          <CardDescription>Description</CardDescription>
        </CardHeader>
      </Card>
    );
    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Description')).toBeInTheDocument();
  });

  it('renders CardContent', () => {
    render(
      <Card>
        <CardContent>Content here</CardContent>
      </Card>
    );
    expect(screen.getByText('Content here')).toBeInTheDocument();
  });

  it('renders CardFooter', () => {
    render(
      <Card>
        <CardFooter>Footer content</CardFooter>
      </Card>
    );
    expect(screen.getByText('Footer content')).toBeInTheDocument();
  });
});

describe('Badge', () => {
  it('renders badge with text', () => {
    render(<Badge>Test</Badge>);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });

  it('applies variant classes', () => {
    render(<Badge variant="success">Success</Badge>);
    expect(screen.getByText('Success').closest('span')).toHaveClass('bg-success-light');
  });

  it('applies size classes', () => {
    render(<Badge size="lg">Large</Badge>);
    expect(screen.getByText('Large').closest('span')).toHaveClass('px-3');
  });

  it('shows dot indicator', () => {
    render(<Badge dot>With dot</Badge>);
    expect(screen.getByText('With dot').closest('span')).toContainHTML('w-1.5');
  });

  it('renders as a span with accessible content', () => {
    render(<Badge>Plain badge</Badge>);
    expect(screen.getByText('Plain badge').closest('span')).toBeInTheDocument();
  });
});

describe('StatusBadge', () => {
  it('renders correct variant for each scan status', () => {
    render(
      <div>
        <StatusBadge status="failed" />
        <StatusBadge status="pending" />
        <StatusBadge status="completed" />
        <StatusBadge status="something-new" />
      </div>
    );
    expect(screen.getByText('Failed').closest('span')).toHaveClass('bg-danger-light');
    expect(screen.getByText('Pending').closest('span')).toHaveClass('bg-warning-light');
    expect(screen.getByText('Completed').closest('span')).toHaveClass('bg-success-light');
    expect(screen.getByText('something-new').closest('span')).toHaveClass('bg-muted');
  });
});

describe('Modal', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders when open', () => {
    render(
      <Modal isOpen={true} onClose={jest.fn()} title="Test Modal">
        Modal content
      </Modal>
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Test Modal')).toBeInTheDocument();
    expect(screen.getByText('Modal content')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <Modal isOpen={false} onClose={jest.fn()} title="Test Modal">
        Modal content
      </Modal>
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    const onClose = jest.fn();
    render(
      <Modal isOpen={true} onClose={onClose} title="Test Modal">
        Modal content
      </Modal>
    );
    fireEvent.click(screen.getByRole('button', { name: /Close modal/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it('renders with description', () => {
    render(
      <Modal isOpen={true} onClose={jest.fn()} title="Test Modal" description="Modal description">
        Modal content
      </Modal>
    );
    expect(screen.getByText('Modal description')).toBeInTheDocument();
  });

  it('renders footer when provided', () => {
    render(
      <Modal isOpen={true} onClose={jest.fn()} title="Test Modal" footer={<Button>Action</Button>}>
        Modal content
      </Modal>
    );
    expect(screen.getByRole('button', { name: /Action/i })).toBeInTheDocument();
  });
});

describe('ConfirmModal', () => {
  it('renders confirm dialog', () => {
    render(
      <ConfirmModal
        isOpen={true}
        onClose={jest.fn()}
        onConfirm={jest.fn()}
        title="Confirm Action"
        message="Are you sure?"
      />
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Confirm Action')).toBeInTheDocument();
    expect(screen.getByText('Are you sure?')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Confirm/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
  });

  it('calls onConfirm when confirm button clicked', () => {
    const onConfirm = jest.fn();
    const onClose = jest.fn();
    render(
      <ConfirmModal
        isOpen={true}
        onClose={onClose}
        onConfirm={onConfirm}
        title="Confirm"
        message="Sure?"
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /Confirm/i }));
    expect(onConfirm).toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
  });

  it('calls onClose when cancel button clicked', () => {
    const onConfirm = jest.fn();
    const onClose = jest.fn();
    render(
      <ConfirmModal
        isOpen={true}
        onClose={onClose}
        onConfirm={onConfirm}
        title="Confirm"
        message="Sure?"
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));
    expect(onClose).toHaveBeenCalled();
    expect(onConfirm).not.toHaveBeenCalled();
  });
});