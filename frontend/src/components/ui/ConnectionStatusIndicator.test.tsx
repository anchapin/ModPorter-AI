/**
 * Connection Status Indicator Tests
 * Tests for the ConnectionStatusIndicator component
 */

import { render, screen } from '@testing-library/react';
import { describe, beforeEach, test, expect } from 'vitest';
import { ConnectionStatusIndicator } from './ConnectionStatusIndicator';

describe('ConnectionStatusIndicator', () => {
  beforeEach(() => {
    // Suppress console warnings during tests
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  test('renders connected status with WebSocket', () => {
    render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={true}
      />
    );

    expect(screen.getByText('Real-time updates active')).toBeInTheDocument();
  });

  test('renders connected status without WebSocket', () => {
    render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={false}
      />
    );

    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  test('renders connecting status', () => {
    render(
      <ConnectionStatusIndicator
        status="connecting"
        usingWebSocket={true}
      />
    );

    expect(screen.getByText('Connecting...')).toBeInTheDocument();
  });

  test('renders disconnected status with WebSocket', () => {
    render(
      <ConnectionStatusIndicator
        status="disconnected"
        usingWebSocket={true}
      />
    );

    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });

  test('renders polling status without WebSocket', () => {
    render(
      <ConnectionStatusIndicator
        status="disconnected"
        usingWebSocket={false}
      />
    );

    expect(screen.getByText('Using fallback polling')).toBeInTheDocument();
  });

  test('renders error status', () => {
    render(
      <ConnectionStatusIndicator
        status="error"
        usingWebSocket={true}
        error="Connection timeout"
      />
    );

    expect(screen.getByText('Connection Error')).toBeInTheDocument();
    expect(screen.getByText('Connection timeout')).toBeInTheDocument();
  });

  test('hides label when showLabel is false', () => {
    render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={true}
        showLabel={false}
      />
    );

    expect(screen.queryByText('Real-time updates active')).not.toBeInTheDocument();
  });

  test('renders small size variant', () => {
    const { container } = render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={true}
        size="small"
      />
    );

    expect(container.querySelector('.size-small')).toBeInTheDocument();
  });

  test('renders medium size variant (default)', () => {
    const { container } = render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={true}
        size="medium"
      />
    );

    expect(container.querySelector('.size-medium')).toBeInTheDocument();
  });

  test('renders large size variant', () => {
    const { container } = render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={true}
        size="large"
      />
    );

    expect(container.querySelector('.size-large')).toBeInTheDocument();
  });

  test('applies custom className', () => {
    const { container } = render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={true}
        className="custom-class"
      />
    );

    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });

  test('calls onClick handler when clicked', () => {
    const handleClick = vi.fn();

    render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={true}
        onClick={handleClick}
      />
    );

    const indicator = screen.getByText('Real-time updates active').closest('.connection-status-indicator');
    indicator?.click();

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  test('displays tooltip when showTooltip is true (default)', () => {
    render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={true}
        showTooltip={true}
      />
    );

    const indicator = screen.getByText('Real-time updates active').closest('.connection-status-indicator');
    expect(indicator).toHaveAttribute('title', 'Connected via WebSocket - Real-time updates');
  });

  test('hides tooltip when showTooltip is false', () => {
    render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={true}
        showTooltip={false}
      />
    );

    const indicator = screen.getByText('Real-time updates active').closest('.connection-status-indicator');
    expect(indicator).not.toHaveAttribute('title');
  });

  test('does not show error message when status is not error', () => {
    render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={true}
        error="This should not show"
      />
    );

    expect(screen.queryByText('This should not show')).not.toBeInTheDocument();
  });

  test('has correct class for connected status', () => {
    const { container } = render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={true}
      />
    );

    expect(container.querySelector('.connected')).toBeInTheDocument();
  });

  test('has correct class for connecting status', () => {
    const { container } = render(
      <ConnectionStatusIndicator
        status="connecting"
        usingWebSocket={true}
      />
    );

    expect(container.querySelector('.connecting')).toBeInTheDocument();
  });

  test('has correct class for disconnected WebSocket status', () => {
    const { container } = render(
      <ConnectionStatusIndicator
        status="disconnected"
        usingWebSocket={true}
      />
    );

    expect(container.querySelector('.disconnected-websocket')).toBeInTheDocument();
  });

  test('has correct class for polling status', () => {
    const { container } = render(
      <ConnectionStatusIndicator
        status="disconnected"
        usingWebSocket={false}
      />
    );

    expect(container.querySelector('.polling')).toBeInTheDocument();
  });

  test('has correct class for error status', () => {
    const { container } = render(
      <ConnectionStatusIndicator
        status="error"
        usingWebSocket={true}
      />
    );

    expect(container.querySelector('.error')).toBeInTheDocument();
  });

  test('is clickable when onClick is provided', () => {
    const { container } = render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={true}
        onClick={() => {}}
      />
    );

    expect(container.querySelector('.clickable')).toBeInTheDocument();
  });

  test('is not clickable when onClick is not provided', () => {
    const { container } = render(
      <ConnectionStatusIndicator
        status="connected"
        usingWebSocket={true}
      />
    );

    expect(container.querySelector('.clickable')).not.toBeInTheDocument();
  });
});
