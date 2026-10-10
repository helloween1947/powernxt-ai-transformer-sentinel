// A chart represents one immutable configuration/model. Other records stay
// in the history/evidence list and can be inspected separately.
export function chartPointsForContext(points, configurationVersion, modelVersion) {
  return points.filter(point => point.configurationVersion === configurationVersion &&
    (point.modelVersion == null || point.modelVersion === modelVersion));
}
