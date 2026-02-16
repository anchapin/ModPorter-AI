import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Button } from './button';

describe('Button Component', () => {
  it('renders correctly', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  it('handles loading state', () => {
    render(<Button loading>Click me</Button>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
    // Check if spinner is present (SVG)
    expect(button.querySelector('svg')).toBeInTheDocument();
  });

  it('handles loading state with custom text', () => {
    render(<Button loading loadingText="Saving...">Click me</Button>);
    expect(screen.getByRole('button', { name: /saving.../i })).toBeInTheDocument();
    expect(screen.queryByText(/click me/i)).not.toBeInTheDocument();
  });

  it('handles icon button loading state (hides children)', () => {
    render(
      <Button size="icon" loading>
        <span data-testid="icon">Icon</span>
      </Button>
    );
    // When loading and icon size, we render just the spinner inside the button
    expect(screen.queryByTestId('icon')).not.toBeInTheDocument();
    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByRole('button').querySelector('svg')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('does not call onClick when disabled', () => {
    const handleClick = vi.fn();
    render(<Button disabled onClick={handleClick}>Click me</Button>);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('does not call onClick when loading', () => {
    const handleClick = vi.fn();
    render(<Button loading onClick={handleClick}>Click me</Button>);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('applies variant props correctly', () => {
    const { getByRole } = render(<Button variant="destructive">Delete</Button>);
    const button = getByRole('button');
    // Check for destructive class (bg-red-600)
    expect(button.className).toContain('bg-red-600');
  });

  it('applies custom className', () => {
    const { getByRole } = render(<Button className="custom-class">Click me</Button>);
    const button = getByRole('button');
    expect(button.className).toContain('custom-class');
  });
});
