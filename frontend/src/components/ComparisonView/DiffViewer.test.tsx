import { render, screen } from '@testing-library/react';
import { describe, test, expect } from 'vitest';
import DiffViewer from './DiffViewer';

describe('DiffViewer', () => {
  test('renders diff viewer with title', () => {
    const mockCodeDiff = {
      added: ['+ console.log("new line");'],
      removed: ['- console.log("old line");'],
      unchanged: ['  const x = 1;'],
    };

    render(<DiffViewer codeDiff={mockCodeDiff} />);

    expect(screen.getByText('Code Differences (DiffViewer)')).toBeInTheDocument();
    expect(screen.getByText('Interactive diff view will be implemented here.')).toBeInTheDocument();
  });

  test('displays code diff data as JSON', () => {
    const mockCodeDiff = {
      file: 'test.js',
      changes: [
        { type: 'addition', line: '+ function newFunction() {}' },
        { type: 'deletion', line: '- function oldFunction() {}' },
      ],
    };

    render(<DiffViewer codeDiff={mockCodeDiff} />);

    // Check that pre element exists and contains expected content
    const preElement = document.querySelector('pre');
    expect(preElement).toBeInTheDocument();
    expect(preElement?.textContent).toContain('test.js');
    expect(preElement?.textContent).toContain('addition');
    expect(preElement?.textContent).toContain('deletion');
  });

  test('handles null code diff', () => {
    render(<DiffViewer codeDiff={null} />);

    expect(screen.getByText('Code Differences (DiffViewer)')).toBeInTheDocument();
    expect(screen.getByText('null')).toBeInTheDocument();
  });

  test('handles undefined code diff', () => {
    render(<DiffViewer codeDiff={undefined} />);

    expect(screen.getByText('Code Differences (DiffViewer)')).toBeInTheDocument();
  });

  test('handles empty object code diff', () => {
    const emptyDiff = {};

    render(<DiffViewer codeDiff={emptyDiff} />);

    expect(screen.getByText('Code Differences (DiffViewer)')).toBeInTheDocument();
    expect(screen.getByText('{}')).toBeInTheDocument();
  });

  test('handles complex nested code diff structure', () => {
    const complexDiff = {
      metadata: {
        fileA: 'original.java',
        fileB: 'converted.js',
        timestamp: '2024-01-01T00:00:00Z',
      },
      hunks: [
        {
          oldStart: 10,
          newStart: 12,
          oldLines: 5,
          newLines: 7,
          lines: [
            { type: 'context', content: '  public class Example {' },
            { type: 'deletion', content: '-   private int value;' },
            { type: 'addition', content: '+   let value;' },
            { type: 'context', content: '  }' },
          ],
        },
      ],
      statistics: {
        additions: 3,
        deletions: 2,
        modifications: 5,
      },
    };

    render(<DiffViewer codeDiff={complexDiff} />);

    expect(screen.getByText('Code Differences (DiffViewer)')).toBeInTheDocument();
    
    // Verify that the complex structure is displayed in the pre element
    const preElement = document.querySelector('pre');
    expect(preElement).toBeInTheDocument();
    expect(preElement?.textContent).toContain('original.java');
    expect(preElement?.textContent).toContain('converted.js');
    expect(preElement?.textContent).toContain('additions');
    expect(preElement?.textContent).toContain('deletions');
  });

  test('handles array of diff entries', () => {
    const arrayDiff = [
      { file: 'file1.java', status: 'modified' },
      { file: 'file2.java', status: 'added' },
      { file: 'file3.java', status: 'deleted' },
    ];

    render(<DiffViewer codeDiff={arrayDiff} />);

    expect(screen.getByText('Code Differences (DiffViewer)')).toBeInTheDocument();
    
    const preElement = document.querySelector('pre');
    expect(preElement).toBeInTheDocument();
    expect(preElement?.textContent).toContain('file1.java');
    expect(preElement?.textContent).toContain('file2.java');
    expect(preElement?.textContent).toContain('modified');
    expect(preElement?.textContent).toContain('added');
    expect(preElement?.textContent).toContain('deleted');
  });

  test('handles string code diff', () => {
    const stringDiff = 'Simple diff string representation';

    render(<DiffViewer codeDiff={stringDiff} />);

    expect(screen.getByText('Code Differences (DiffViewer)')).toBeInTheDocument();
    expect(screen.getByText(`"${stringDiff}"`)).toBeInTheDocument();
  });

  test('renders with proper HTML structure', () => {
    const mockCodeDiff = { test: 'data' };

    render(<DiffViewer codeDiff={mockCodeDiff} />);

    const container = screen.getByText('Code Differences (DiffViewer)').closest('div');
    expect(container).toBeInTheDocument();

    const heading = screen.getByRole('heading', { level: 2 });
    expect(heading).toHaveTextContent('Code Differences (DiffViewer)');

    const paragraph = screen.getByText('Interactive diff view will be implemented here.');
    expect(paragraph.tagName).toBe('P');

    const preElement = container?.querySelector('pre');
    expect(preElement).toBeInTheDocument();
  });

  test('formats JSON with proper indentation', () => {
    const mockCodeDiff = {
      deeply: {
        nested: {
          object: {
            with: ['array', 'elements'],
            and: 'string values',
          },
        },
      },
    };

    render(<DiffViewer codeDiff={mockCodeDiff} />);

    const preElement = document.querySelector('pre');
    expect(preElement).toBeInTheDocument();
    expect(preElement?.textContent).toContain('deeply');
    expect(preElement?.textContent).toContain('nested');
    expect(preElement?.textContent).toContain('array');
    expect(preElement?.textContent).toContain('elements');
    
    // Verify proper JSON formatting (should contain indentation)
    expect(preElement?.textContent).toMatch(/\s{2,}/); // Contains multiple spaces (indentation)
  });
});