import React from 'react';
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { TeamManagement } from './TeamManagement';

describe('TeamManagement', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <TeamManagement />
    );
    expect(container).toBeDefined();
  });

  it('has correct export', () => {
    expect(TeamManagement).toBeDefined();
  });
});
