import { ButtonHTMLAttributes, forwardRef, ReactElement, isValidElement, Children, cloneElement } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  fullWidth?: boolean;
}

const variantStyles = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
  secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200 focus:ring-gray-500',
  outline: 'border-2 border-gray-300 text-gray-700 hover:bg-gray-50 focus:ring-gray-500',
  ghost: 'text-gray-600 hover:bg-gray-100 focus:ring-gray-500',
  danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
};

const sizeStyles = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      fullWidth = false,
      disabled,
      children,
      className = '',
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={`
          inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200
          focus:outline-none focus:ring-2 focus:ring-offset-2
          disabled:opacity-50 disabled:cursor-not-allowed
          ${variantStyles[variant]}
          ${sizeStyles[size]}
          ${fullWidth ? 'w-full' : ''}
          ${className}
        `}
        {...props}
      >
        {loading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

interface ButtonGroupProps {
  children: React.ReactNode;
  className?: string;
  vertical?: boolean;
}

export function ButtonGroup({ children, className = '', vertical = false }: ButtonGroupProps) {
  return (
    <div
      className={`
        inline-flex ${vertical ? 'flex-col' : ''} rounded-lg overflow-hidden
        ${className}
      `}
      role="group"
      aria-label="Button group"
    >
{Children.map(children, (child, index) => {
        if (!isValidElement(child)) return child;
        const count = Children.count(children);
        const isFirst = index === 0;
        const isLast = index === count - 1;
        const extraClassName = !vertical
          ? isFirst
            ? 'rounded-r-none'
            : isLast
            ? 'rounded-l-none'
            : 'rounded-none'
          : isFirst
          ? 'rounded-b-none'
          : isLast
          ? 'rounded-t-none'
          : 'rounded-none';
        const childElement = child as ReactElement<Record<string, unknown>>;
        const childClassName = (childElement.props.className as string) || '';
        return cloneElement(childElement, {
          className: `${childClassName} ${extraClassName}`,
        });
      })}
    </div>
  );
}

export function IconButton({
  children,
  ariaLabel,
  variant = 'ghost',
  size = 'md',
  className = '',
  ...props
}: {
  children: React.ReactNode;
  ariaLabel: string;
  variant?: 'ghost' | 'outline' | 'primary';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
} & Omit<ButtonProps, 'children' | 'variant' | 'size'>) {
  return (
    <Button
      variant={variant}
      size={size}
      className={`p-0 ${size === 'sm' ? 'w-8 h-8' : size === 'md' ? 'w-10 h-10' : 'w-12 h-12'} ${className}`}
      aria-label={ariaLabel}
      {...props}
    >
      {children}
    </Button>
  );
}