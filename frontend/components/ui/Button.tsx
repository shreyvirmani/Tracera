'use client';

import React, { ButtonHTMLAttributes, forwardRef } from 'react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'ghost-danger';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  loading?: boolean;
  fullWidth?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:opacity-50 disabled:cursor-not-allowed';

const variantStyles = {
  primary: 'bg-primary text-background hover:bg-primary-hover active:bg-primary/90 font-semibold',
  secondary: 'bg-surface border border-border text-text-primary hover:bg-elevated active:bg-surface/80',
  outline: 'border border-border bg-transparent text-text-primary hover:bg-surface active:bg-surface/50',
  ghost: 'bg-transparent text-text-primary hover:bg-surface active:bg-surface/50',
  danger: 'bg-danger text-background hover:bg-danger/90 active:bg-danger/80 font-semibold',
  'ghost-danger': 'bg-transparent text-danger hover:bg-danger-light active:bg-danger-light/50 text-danger',
};

const sizeStyles = {
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2',
  icon: 'p-2',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      fullWidth = false,
      leftIcon,
      rightIcon,
      disabled,
      className = '',
      children,
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
          ${baseStyles}
          ${variantStyles[variant]}
          ${sizeStyles[size]}
          ${fullWidth ? 'w-full' : ''}
          ${className}
        `}
        {...props}
      >
        {loading && (
          <svg
            className="animate-spin h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
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
        {!loading && leftIcon && <span aria-hidden="true">{leftIcon}</span>}
        {children}
        {!loading && rightIcon && <span aria-hidden="true">{rightIcon}</span>}
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
      {React.Children.map(children, (child, index) => {
        if (!React.isValidElement(child)) return child;
        const count = React.Children.count(children);
        const childElement = child as React.ReactElement<{ className?: string }>;
        return React.cloneElement(childElement, {
          className: `${(childElement.props as { className?: string }).className || ''} ${
            !vertical
              ? index === 0
                ? 'rounded-r-none'
                : index === count - 1
                ? 'rounded-l-none'
                : 'rounded-none'
              : index === 0
              ? 'rounded-b-none'
              : index === count - 1
              ? 'rounded-t-none'
              : 'rounded-none'
          }`,
        });
      })}
    </div>
  );
}
