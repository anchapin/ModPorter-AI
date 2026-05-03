/**
 * Tests for common UI components
 */

import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { LoadingWrapper } from '../../components/common/LoadingWrapper';
// Toast import removed due to JSX issues

describe('LoadingWrapper', () => {
  it('renders children when not loading', () => {
    const { container } = render(
      <LoadingWrapper loading={false}>
        <div>Content</div>
      </LoadingWrapper>
    );
    expect(container.textContent).toContain('Content');
  });
});
