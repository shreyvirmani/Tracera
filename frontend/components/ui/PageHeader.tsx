'use client';

import { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  breadcrumbs?: Array<{ label: string; href?: string }>;
  className?: string;
}

export function PageHeader({
  title,
  description,
  actions,
  breadcrumbs,
  className = '',
}: PageHeaderProps) {
  return (
    <div className={`mb-8 ${className}`}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="mb-4 flex items-center gap-2 text-sm text-text-muted" aria-label="Breadcrumb">
          {breadcrumbs.map((crumb, index) => (
            <span key={index} className="flex items-center gap-2">
              {index > 0 && (
                <svg className="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              )}
              {crumb.href ? (
                <a href={crumb.href} className="text-text-secondary hover:text-text-primary transition-colors">
                  {crumb.label}
                </a>
              ) : (
                <span className="text-text-primary font-medium">{crumb.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text-primary tracking-tight">{title}</h1>
          {description && (
            <p className="mt-1 text-base text-text-secondary">{description}</p>
          )}
        </div>
        {actions && (
          <div className="flex-shrink-0 mt-4 sm:mt-0">{actions}</div>
        )}
      </div>
    </div>
  );
}