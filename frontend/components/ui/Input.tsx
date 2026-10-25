'use client';

import { InputHTMLAttributes, TextareaHTMLAttributes, forwardRef } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  classNameWrapper?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      className = '',
      classNameWrapper = '',
      id,
      required,
      ...props
    },
    ref
  ) => {
    const hasError = !!error;
    const hasHelper = !!helperText && !error;

    return (
      <div className={classNameWrapper}>
        {label && (
          <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-text-secondary">
            {required && (
              <span className="ml-0.5 text-danger" aria-hidden="true">
                *
              </span>
            )}
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-text-muted">
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            id={id}
            required={required}
            className={`w-full rounded-lg border bg-card py-2.5 text-sm text-text-primary placeholder:text-text-muted transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary disabled:cursor-not-allowed disabled:bg-muted ${
              hasError
                ? 'border-danger focus:ring-danger focus:border-danger'
                : 'border-border focus:border-primary'
            } ${leftIcon ? 'pl-10' : 'pl-4'} ${rightIcon ? 'pr-10' : 'pr-4'} ${className}`}
            aria-invalid={hasError}
            aria-describedby={
              hasError ? `${id}-error` : hasHelper ? `${id}-helper` : undefined
            }
            {...props}
          />
          {rightIcon && (
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-text-muted">
              {rightIcon}
            </div>
          )}
        </div>
        {hasError && (
          <p id={`${id}-error`} className="mt-1.5 text-sm text-danger" role="alert">
            {error}
          </p>
        )}
        {hasHelper && (
          <p id={`${id}-helper`} className="mt-1.5 text-sm text-text-muted">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
  error?: string;
  helperText?: string;
};

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, helperText, className = '', id, required, ...props }, ref) => {
    const hasError = !!error;
    const hasHelperText = !!helperText && !error;

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-text-secondary">
            {required && (
              <span className="ml-0.5 text-danger" aria-hidden="true">
                *
              </span>
            )}
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={id}
          required={required}
          className={`min-h-[100px] w-full resize-y rounded-lg border bg-card p-4 text-sm text-text-primary placeholder:text-text-muted transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary disabled:cursor-not-allowed disabled:bg-muted ${
            hasError
              ? 'border-danger focus:ring-danger focus:border-danger'
              : 'border-border focus:border-primary'
          } ${className}`}
          aria-invalid={hasError}
          aria-describedby={
            hasError ? `${id}-error` : hasHelperText ? `${id}-helper` : undefined
          }
          {...props}
        />
        {hasError && (
          <p id={`${id}-error`} className="mt-1.5 text-sm text-danger" role="alert">
            {error}
          </p>
        )}
        {hasHelperText && (
          <p id={`${id}-helper`} className="mt-1.5 text-sm text-text-muted">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
