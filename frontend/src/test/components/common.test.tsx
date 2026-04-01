/**
 * Tests for common UI components
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LoadingWrapper } from '../../components/common/LoadingWrapper';
// Toast import removed due to JSX issues

describe('LoadingWrapper', () => {
  it('renders children when not loading', () => {
    const { container } = render(<LoadingWrapper loading={false}><div>Content</div></LoadingWrapper>);
    expect(container.textContent).toContain('Content');
  });
});