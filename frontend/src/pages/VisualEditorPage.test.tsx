import React from 'react';
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import VisualEditorPage from '../pages/VisualEditorPage';

describe('VisualEditorPage', () => {
  it('renders without crashing', () => {
    const { container } = render(<VisualEditorPage />);
    expect(container).toBeDefined();
  });
});
