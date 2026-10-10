// Transcribed from Sheet1 A1:H35; no asset IDs or timestamps are invented.
export const benchMeasurements = [
  { row: 4, label: 'R-phase current', unit: 'A', reference: 49.79, software: 49.92 },
  { row: 5, label: 'Y-phase current', unit: 'A', reference: 49.78, software: 49.91 },
  { row: 6, label: 'B-phase current', unit: 'A', reference: 49.8, software: 49.89 },
  { row: 8, label: 'R-phase voltage', unit: 'V', reference: 259.05, software: 259.15 },
  { row: 9, label: 'Y-phase voltage', unit: 'V', reference: 259.91, software: 259.98 },
  { row: 10, label: 'B-phase voltage', unit: 'V', reference: 264.4, software: 264.52 },
].map(item => ({ ...item, difference: item.reference - item.software, percent: (item.reference - item.software) * 100 / item.reference, withinTolerance: Math.abs((item.reference - item.software) * 100 / item.reference) <= 1 }));
export const tripEvidence = {
  current: [{ phase: 'R', reference: 50.14, software: 50.33 }, { phase: 'Y', reference: 50.13, software: 50.34 }, { phase: 'B', reference: 49.81, software: 49.98 }],
  temperature: [{ setting: 60, reference: 59.9, software: 60.25 }, { setting: 60, reference: 59.45, software: 60 }, { setting: 60, reference: 59.5, software: 59.75 }],
};
