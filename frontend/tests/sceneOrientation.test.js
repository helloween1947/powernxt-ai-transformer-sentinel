import test from 'node:test';
import assert from 'node:assert/strict';
import { OrthographicCamera } from 'three';
import { sceneAxes } from '../src/domain/sceneOrientation.js';

function cameraAt(x, y, z) {
  const camera = new OrthographicCamera(-5, 5, 5, -5, 0.1, 60);
  camera.position.set(x, y, z);
  camera.lookAt(0, 0, 0);
  return camera;
}
const axis = (camera, label) => sceneAxes(camera).find(item => item.label === label);
test('front and side views project world axes into matching screen directions', () => {
  const front = cameraAt(0, 0, 10);
  assert.equal(axis(front, 'X').x, 1);
  assert.equal(axis(front, 'Y').y, -1);
  assert.equal(axis(front, 'Z').x, 0);
  const side = cameraAt(10, 0, 0);
  assert.equal(axis(side, 'Z').x, -1);
  assert.equal(axis(side, 'Y').y, -1);
  assert.ok(Math.abs(axis(side, 'X').x) === 0);
});
test('orbit changes the axes; zoom and translation preserve orientation; reset restores it', () => {
  const camera = cameraAt(7, 4.7, 9);
  const initial = sceneAxes(camera);
  camera.zoom = 90;
  camera.position.addScalar(2);
  camera.updateProjectionMatrix();
  assert.deepEqual(sceneAxes(camera), initial);
  camera.position.set(-7, 4.7, 9);
  camera.lookAt(0, 0, 0);
  assert.notDeepEqual(sceneAxes(camera), initial);
  camera.position.set(7, 4.7, 9);
  camera.lookAt(0, 0, 0);
  assert.deepEqual(sceneAxes(camera), initial);
});
