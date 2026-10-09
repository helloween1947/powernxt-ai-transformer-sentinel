export const demoAssets = [
  { id: 'TR-001', name: 'Central distribution transformer', rating: '500 kVA' },
  { id: 'TR-002', name: 'East distribution transformer', rating: '250 kVA' },
];

export function makeDemoDashboard(assetId = 'TR-001', scenario = 'overload') {
  const asset = demoAssets.find(item => item.id === assetId) ?? demoAssets[0];
  const fault = scenario === 'overload';
  const lost = scenario === 'sensor-loss';
  const now = Date.now();
  const observed = fault ? [58, 61, 65, 70, 76, 82] : [56, 57, 58, 58, 59, 59];
  const predicted = fault ? [58, 60, 63, 66, 69, 72] : [56, 57, 57, 58, 58, 59];
  const history = observed.map((oil, index) => ({
    timestamp: new Date(now - (5 - index) * 60000).toISOString(),
    measuredOil: lost && index >= 4 ? null : oil,
    predictedOil: predicted[index],
  }));
  return {
    asset, timestamp: new Date(now).toISOString(), staleAfterSeconds: 30,
    source: 'simulated', dataQuality: lost ? 'Oil sensor unavailable' : 'Sample readings available',
    readings: {
      voltage: [230, 231, 229], current: fault ? [780, 750, 800] : [320, 325, 318],
      loading: fault ? 122 : 52, oilTemperature: lost ? null : observed[5], ambientTemperature: 30,
    },
    analytics: {
      condition: fault ? 'Needs attention' : lost ? 'Assessment limited' : 'Normal',
      confidence: lost ? 'Low' : 'High',
      contributors: fault ? ['Loading above the sample rating limit', 'Oil temperature exceeds the sample twin prediction'] : lost ? ['Oil sensor data is missing; condition cannot be fully assessed'] : ['Sample temperatures and loading are within the configured range'],
    },
    history,
    alerts: fault || lost ? [{
      id: `${asset.id}-${lost ? 'SENSOR' : 'HEAT'}`, assetId: asset.id,
      type: lost ? 'Oil sensor unavailable' : 'Persistent temperature deviation',
      severity: lost ? 'Warning' : 'High', status: 'Active',
      firstSeen: history[3].timestamp,
      evidence: lost ? 'The last two sample oil-temperature readings are missing.' : 'Sample measured oil temperature is 82 C; sample twin prediction is 72 C.',
      recommendation: lost ? 'Inspect the sensor connection and verify the reading.' : 'Review loading and cooling, then arrange an inspection.',
    }] : [],
  };
}

export function makeDemoComparison(assetId, alternative) {
  const baseline = [82, 85, 88, 90, 91];
  const changed = alternative === 'lower-load' ? [82, 80, 78, 76, 75] : [82, 81, 79, 78, 77];
  return {
    assetId, explanation: 'These are fixed illustrative curves for UI development. They are not calculated by the Digital Twin model.',
    assumptions: alternative === 'lower-load' ? 'Illustrative reduced-load scenario' : 'Illustrative restored-cooling scenario',
    points: baseline.map((temperature, index) => ({
      timestamp: new Date(Date.now() + index * 15 * 60000).toISOString(),
      baseline: temperature, alternative: changed[index],
    })),
  };
}
