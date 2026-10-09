import { createTelemetryClient } from './telemetryClient.js';

// The same client serves telemetry and analytics; fixture APIs remain separate.
export const telemetryClient = createTelemetryClient(import.meta.env.VITE_API_BASE_URL);
export const { getAssetPage, getAssetDetails, getLatestTelemetry, getTelemetryHistory, getReadingAnalytics, getLatestAnalytics } = telemetryClient;
