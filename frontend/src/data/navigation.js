import { Activity, Bell, Box, FileDown, FlaskConical, Wrench, ScanSearch } from 'lucide-react';

export const navigation = [
  { id: 'twin', label: 'Digital twin', icon: Box },
  { id: 'capabilities', label: 'Condition explorer', icon: ScanSearch },
  { id: 'trends', label: 'Trends & history', icon: Activity },
  { id: 'incidents', label: 'Alerts & incidents', icon: Bell },
  { id: 'maintenance', label: 'Maintenance', icon: Wrench },
  { id: 'whatif', label: 'What-if analysis', icon: FlaskConical },
  { id: 'reports', label: 'Reports', icon: FileDown },
];
