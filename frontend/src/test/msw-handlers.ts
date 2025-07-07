import { http, HttpResponse } from 'msw';
import { ConversionStatus } from '../types/api';

const API_BASE_URL = 'http://localhost:8000/api/v1'; // Assuming this is the base URL

let conversionState: {
  status: ConversionStatus;
  progress: number;
  conversionId?: string;
  error?: string | null;
} = {
  status: ConversionStatus.PENDING,
  progress: 0,
  error: null,
};

export const resetConversionState = () => {
  conversionState = {
    status: ConversionStatus.PENDING,
    progress: 0,
    conversionId: undefined,
    error: null,
  };
};

export const setServerConversionId = (id: string) => {
  conversionState.conversionId = id;
};

export const handlers = [
  // Handles a POST /api/v1/convert request
  http.post(`${API_BASE_URL}/convert`, async ({ request }) => {
    resetConversionState(); // Reset state for new conversion
    const formData = await request.formData();
    const file = formData.get('mod_file');
    // const modUrl = formData.get('mod_url');

    if (!file /* && !modUrl */) { // Simplified check for this example
      return HttpResponse.json({ detail: 'No file or URL provided' }, { status: 400 });
    }

    conversionState.conversionId = `mock-${Date.now()}`;
    conversionState.status = ConversionStatus.PENDING; // Or ANALYZING if it starts quickly
    conversionState.progress = 10;

    return HttpResponse.json({
      conversionId: conversionState.conversionId,
      status: conversionState.status,
      progress: conversionState.progress,
      overallSuccessRate: 0,
      convertedMods: [],
      failedMods: [],
      smartAssumptionsApplied: [],
      detailedReport: { stage: 'Pending', progress: 0, logs: [], technicalDetails: {} },
    });
  }),

  // Handles a GET /api/v1/convert/:id/status request
  http.get(`${API_BASE_URL}/convert/:id/status`, ({ params }) => {
    const { id } = params;
    if (id !== conversionState.conversionId) {
      return HttpResponse.json({ detail: 'Conversion not found' }, { status: 404 });
    }

    // Simulate progress
    if (conversionState.status === ConversionStatus.PENDING) {
      conversionState.status = ConversionStatus.ANALYZING;
      conversionState.progress = 25;
    } else if (conversionState.status === ConversionStatus.ANALYZING) {
      conversionState.status = ConversionStatus.CONVERTING;
      conversionState.progress = 50;
    } else if (conversionState.status === ConversionStatus.CONVERTING) {
      conversionState.status = ConversionStatus.PACKAGING;
      conversionState.progress = 75;
    } else if (conversionState.status === ConversionStatus.PACKAGING) {
      conversionState.status = ConversionStatus.COMPLETED;
      conversionState.progress = 100;
    }

    return HttpResponse.json({
      conversionId: conversionState.conversionId,
      status: conversionState.status,
      progress: conversionState.progress,
      // Other fields can be added as needed for COMPLETED state
      overallSuccessRate: conversionState.status === ConversionStatus.COMPLETED ? 100 : 0,
      convertedMods: conversionState.status === ConversionStatus.COMPLETED ? [{ name: 'Test Mod', version: '1.0', status: 'success', features: [], warnings: [] }] : [],
      failedMods: [],
      smartAssumptionsApplied: [],
      error: conversionState.error,
      detailedReport: { stage: conversionState.status, progress: conversionState.progress, logs: [], technicalDetails: {} },
    });
  }),

  // Handles a GET /api/v1/convert/:id/download request
  http.get(`${API_BASE_URL}/convert/:id/download`, ({ params }) => {
    const { id } = params;
    if (id !== conversionState.conversionId || conversionState.status !== ConversionStatus.COMPLETED) {
      return HttpResponse.json({ detail: 'File not ready or not found' }, { status: 404 });
    }
    const blob = new Blob(['mock file content'], { type: 'application/octet-stream' });
    return new HttpResponse(blob, {
        headers: {
            'Content-Type': 'application/octet-stream',
            'Content-Disposition': `attachment; filename="${id}_converted.mcaddon"`,
        }
    });
  }),

  // Handles a DELETE /api/v1/convert/:id request
  http.delete(`${API_BASE_URL}/convert/:id`, ({ params }) => {
    const { id } = params;
    if (id !== conversionState.conversionId) {
      return HttpResponse.json({ detail: 'Conversion not found' }, { status: 404 });
    }
    conversionState.status = ConversionStatus.CANCELLED;
    conversionState.progress = 0; // Or whatever progress it was at
    return HttpResponse.json(null, { status: 204 }); // No content
  }),
];
