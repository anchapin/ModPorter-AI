# Frontend MVP Implementation

This document describes the complete frontend MVP implementation for ModPorter AI's upload-to-download flow.

## Overview

The MVP provides a complete user flow from uploading a Java mod to downloading the converted Bedrock add-on, with real-time progress tracking and detailed reporting.

## Architecture

### Core Components

1. **ConversionFlowManager** (`/components/ConversionFlow/`)
   - Orchestrates the complete upload-to-download experience
   - Manages state transitions: idle → uploading → converting → completed/failed
   - Handles error recovery and retry logic
   - Provides auto-reset functionality

2. **ConversionUploadEnhanced** (`/components/ConversionUpload/ConversionUploadEnhanced.tsx`)
   - Enhanced upload component with drag-drop support
   - File validation (type, size)
   - URL input for CurseForge/Modrinth links
   - Smart Assumptions and Dependencies options
   - Real-time upload progress indication

3. **ConversionProgress** (`/components/ConversionProgress/`)
   - Real-time progress tracking via WebSocket
   - Fallback polling when WebSocket unavailable
   - Visual progress bar with percentage
   - Agent status display
   - Estimated time remaining

4. **ConversionReportContainer** (`/components/ConversionReport/`)
   - Fetches and displays conversion results
   - Shows Smart Assumptions applied
   - Displays feature analysis and developer logs
   - Provides download link for .mcaddon file

### Services

1. **WebSocket Service** (`/services/websocket.ts`)
   - Real-time bidirectional communication
   - Automatic reconnection with exponential backoff
   - Graceful fallback to HTTP polling
   - Connection status tracking

2. **API Service** (`/services/api.ts`)
   - All backend communication
   - File upload, conversion initiation
   - Status polling, result download
   - Error handling with detailed messages

## User Flow

```
1. User arrives on ConvertPage (/)
   ↓
2. Drag-drop JAR file or paste URL
   ↓
3. Configure options (Smart Assumptions, Dependencies)
   ↓
4. Click "Upload"
   ↓
5. See upload progress (0-100%)
   ↓
6. Real-time conversion progress:
   - Agent status updates
   - Progress percentage
   - Current stage
   - Estimated time remaining
   ↓
7. Conversion Complete screen:
   - Success animation
   - Download .mcaddon button
   - View Report button
   - Convert Another button
   ↓
8. View detailed report (optional):
   - Summary statistics
   - Smart Assumptions applied
   - Feature analysis
   - Developer logs
   ↓
9. Download .mcaddon file
```

## Error Handling

### Upload Errors
- File too large (>500MB)
- Unsupported file type
- Corrupted file
- Network timeout

### Conversion Errors
- Failed agent execution
- Incompatible features
- Missing dependencies
- Server errors

### Recovery Options
- Try Again button (preserves file)
- Start New Conversion (reset)
- View Partial Report (for failed conversions)

## WebSocket Communication

### Connection URL
```
ws://localhost:8080/api/v1/conversions/{jobId}/ws
```

### Message Format
```typescript
{
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0-100
  message: string;
  stage: string; // Agent name
  estimated_time_remaining: number | null; // seconds
  result_url: string | null;
  error: string | null;
  created_at: string; // ISO date
}
```

### Fallback Polling
If WebSocket fails to connect within 5 seconds, automatically switches to HTTP polling:
- Endpoint: `GET /api/v1/conversions/{jobId}`
- Interval: 3 seconds
- Max retries: Unlimited (until terminal state)

## State Management

### Local Component State
Each component manages its own state using React hooks:
- `useState` for local state
- `useCallback` for event handlers
- `useEffect` for side effects
- `useRef` for WebSocket and timer references

### History Storage
Conversion history stored in `localStorage`:
- Key: `modporter_conversion_history`
- Format: Array of conversion objects
- Max items: 100
- Persistence: Browser-local only

### State Transitions
```
idle → uploading → converting → completed
                    ↓
                  failed
                    ↓
                  idle (after retry)
```

## Responsive Design

### Breakpoints
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

### Mobile Optimizations
- Single column layout
- Full-width buttons
- Stacked action items
- Simplified progress display
- Touch-friendly targets (min 44x44px)

## Accessibility

### Keyboard Navigation
- Tab order: Upload zone → Options → Buttons → Progress → Actions
- Enter/Space to activate buttons
- Escape to cancel modals

### Screen Reader Support
- ARIA labels on inputs
- Role attributes on interactive elements
- Live regions for progress updates
- Alt text for icons

### Color Contrast
- All text meets WCAG AA standards (4.5:1)
- Status colors: Green (success), Red (error), Blue (info)
- Error messages have high contrast backgrounds

## Performance Optimizations

### Code Splitting
- Lazy loaded routes with React.lazy()
- Suspense boundaries for loading states
- Separate chunks for heavy components

### Asset Optimization
- SVG icons (inline for immediate render)
- CSS modules for scoped styles
- Minimal external dependencies

### Network Optimization
- WebSocket reduces polling overhead
- Debounced URL input validation
- Progress throttling (100ms intervals)

## API Integration

### Required Backend Endpoints

#### 1. Upload File
```
POST /api/v1/upload
Content-Type: multipart/form-data

Response:
{
  file_id: string;
  original_filename: string;
  saved_filename: string;
  size: number;
  message: string;
}
```

#### 2. Start Conversion
```
POST /api/v1/convert
Content-Type: application/json

Request:
{
  file_id: string;
  original_filename: string;
  target_version?: string;
  options: {
    smartAssumptions: boolean;
    includeDependencies: boolean;
  };
}

Response:
{
  job_id: string;
  status: string;
  message: string;
  estimated_time?: number;
}
```

#### 3. Get Status (Polling)
```
GET /api/v1/conversions/{jobId}

Response:
{
  job_id: string;
  status: string;
  progress: number;
  message: string;
  stage?: string;
  estimated_time_remaining?: number;
  result_url?: string;
  error?: string;
  created_at: string;
}
```

#### 4. WebSocket Progress
```
WS /api/v1/conversions/{jobId}/ws

Message: Same as GET /api/v1/conversions/{jobId}
Frequency: Real-time (on state change)
```

#### 5. Download Result
```
GET /api/v1/conversions/{jobId}/download

Response: Binary file (.mcaddon)
Headers:
  Content-Disposition: attachment; filename="{name}.mcaddon"
  Content-Type: application/zip
```

#### 6. Get Report
```
GET /api/v1/jobs/{jobId}/report

Response:
{
  job_id: string;
  report_generation_date: string;
  summary: { ... };
  converted_mods: [ ... ];
  failed_mods: [ ... ];
  feature_analysis?: { ... };
  smart_assumptions_report?: { ... };
  developer_log?: { ... };
}
```

## Testing

### Manual Testing Checklist
- [ ] Upload .jar file via drag-drop
- [ ] Upload .jar file via file picker
- [ ] Paste CurseForge URL
- [ ] Paste Modrinth URL
- [ ] Toggle Smart Assumptions
- [ ] Toggle Dependencies
- [ ] See upload progress
- [ ] See real-time progress updates
- [ ] Cancel conversion in progress
- [ ] View completion screen
- [ ] Download .mcaddon file
- [ ] View conversion report
- [ ] Start new conversion
- [ ] Handle large file (>100MB)
- [ ] Handle invalid file type
- [ ] Handle network error
- [ ] Handle conversion failure
- [ ] Test on mobile device
- [ ] Test with screen reader

### Automated Testing
```bash
# Unit tests
pnpm test

# Coverage report
pnpm test:coverage

# E2E tests (if configured)
pnpm test:e2e
```

## Deployment

### Environment Variables
```bash
# Required
VITE_API_URL=http://localhost:8080/api/v1
VITE_API_BASE_URL=http://localhost:8080

# Optional
VITE_WS_RECONNECT_DELAY=1000
VITE_WS_MAX_RECONNECT_ATTEMPTS=5
VITE_MAX_FILE_SIZE_MB=500
```

### Build for Production
```bash
cd frontend
pnpm install
pnpm build
# Output: dist/
```

### Docker Deployment
```bash
# Build image
docker build -t modporter-frontend .

# Run container
docker run -p 3000:80 modporter-frontend
```

## Future Enhancements

### Planned Features
1. Batch conversion (multiple files)
2. Conversion templates
3. User accounts and cloud history
4. Shareable conversion reports
5. Advanced options panel
6. Real-time log streaming
7. Conversion comparison
8. A/B testing UI

### Performance Improvements
1. Service Worker for offline support
2. IndexedDB for large file caching
3. Web Workers for file validation
4. Virtual scrolling for history
5. Image lazy loading in reports

### UX Improvements
1. Onboarding tour
2. Contextual help tooltips
3. Keyboard shortcuts
4. Dark mode support
5. Progress notifications
6. Download queue management

## Troubleshooting

### Common Issues

#### WebSocket Connection Fails
- Symptom: Falls back to polling
- Cause: Proxy/NAT not supporting WebSocket
- Solution: Configure proxy to allow WebSocket upgrade

#### File Upload Hangs
- Symptom: Progress stuck at 0%
- Cause: Backend timeout or CORS issue
- Solution: Check nginx proxy timeout (recommend 30min)

#### Download Returns 404
- Symptom: Download button fails
- Cause: File not generated or cleaned up
- Solution: Check backend storage and cleanup policies

#### Report Not Loading
- Symptom: Loading spinner forever
- Cause: Report generation failed
- Solution: Check backend logs for report generation errors

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/modporter-ai/issues
- Documentation: /docs
- API Reference: /docs/api
