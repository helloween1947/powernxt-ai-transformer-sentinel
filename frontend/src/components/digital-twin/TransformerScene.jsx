import { useEffect, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, RoundedBox } from '@react-three/drei';
import { PCFShadowMap, Vector3 } from 'three';
import { sceneMaterials as material } from '../../data/sceneMaterials.js';
import { anchors } from '../../data/capabilities.js';
import { sceneAxes } from '../../domain/sceneOrientation.js';
import { cameraResetProgress } from '../../domain/motion.js';

function Box({ position, size, color, radius = 0.035, ...props }) {
  return <RoundedBox args={size} position={position} radius={radius} smoothness={2} castShadow receiveShadow {...props}>
    <meshStandardMaterial color={color} roughness={0.58} metalness={0.42} />
  </RoundedBox>;
}
function Cylinder({ position, radius, length, color, rotation = [0, 0, 0], segments = 16, ...props }) {
  return <mesh position={position} rotation={rotation} castShadow receiveShadow {...props}>
    <cylinderGeometry args={[radius, radius, length, segments]} /><meshStandardMaterial color={color} metalness={0.4} roughness={0.55} />
  </mesh>;
}
function Bushing({ x, z, small = false, onSelect, active }) {
  const height = small ? 0.32 : 0.78;
  return <group position={[x, 2.04, z]} onClick={event => { event.stopPropagation(); onSelect(x < -.3 ? 'voltage_r_v' : x > .3 ? 'voltage_b_v' : 'voltage_y_v'); }}>
    <Cylinder position={[0, 0.05, 0]} radius={small ? 0.09 : 0.15} length={0.12} color={material.steel} />
    <Cylinder position={[0, height / 2, 0]} radius={small ? 0.055 : 0.075} length={height} color={material.porcelain} />
    {Array.from({ length: small ? 4 : 7 }, (_, index) => <mesh key={index} position={[0, 0.1 + index * (height - 0.12) / (small ? 4 : 7), 0]} castShadow>
      <cylinderGeometry args={[small ? 0.10 : 0.145, small ? 0.11 : 0.16, 0.035, 20]} /><meshStandardMaterial color={active ? material['light'].selected : small ? material.porcelainLight : material.porcelain} roughness={0.32} metalness={0.05} />
    </mesh>)}
    <Cylinder position={[0, height + 0.035, 0]} radius={0.035} length={0.14} color={material.brass} />
    <Box position={[0, height + 0.105, 0]} size={[0.14, 0.065, 0.10]} color={material.brass} radius={0.01} />
  </group>;
}

function CoverHardware({ body }) {
  return <group>
    {[-1.13,-.57,0,.57,1.13].flatMap(x => [-.77,.77].map(z => <group key={`${x}:${z}`}>
      <Cylinder position={[x,2.073,z]} radius={.055} length={.025} color={material.darkSteel} segments={12} />
      <Cylinder position={[x,2.095,z]} radius={.033} length={.035} color={material.steel} segments={6} />
    </group>))}
    {[-1,1].map(side => <group key={side}>
      <Box position={[side*1.08,2.14,-.72]} size={[.13,.32,.075]} color={body} radius={.016} />
      <Cylinder position={[side*1.08,2.28,-.72]} radius={.065} length={.08} rotation={[Math.PI/2,0,0]} color={material.steel} />
      <Box position={[side*1.25,.8,-.9]} size={[.14,1.7,.1]} color={material.darkSteel} radius={.015} />
    </group>)}
    <Cylinder position={[1.13,1.4,.6]} radius={.11} length={.08} rotation={[0,0,Math.PI/2]} color={material.steel} />
    <Cylinder position={[1.18,1.4,.6]} radius={.087} length={.01} rotation={[0,0,Math.PI/2]} color={material.gauge} />
    <Box position={[1.195,1.42,.61]} size={[.008,.07,.012]} color={material.base} radius={.002} />
    <Cylinder position={[1.09,.04,.58]} radius={.078} length={.2} rotation={[0,0,Math.PI/2]} color={material.brass} />
    <Box position={[1.25,.11,.58]} size={[.22,.025,.06]} color={material.brass} radius={.012} />
    <Cylinder position={[-1.08,1.7,-.55]} radius={.05} length={.5} color={material.pipe} />
    <Cylinder position={[-1.08,1.46,-.55]} radius={.11} length={.24} color={material.brass} />
    <Cylinder position={[-1.08,1.32,-.55]} radius={.085} length={.13} color={material.steel} />
    {[.1,.21,.32].map(z => <Box key={z} position={[1.205,1.47,z]} size={[.006,.015,.14]} color={material.darkSteel} radius={.002} />)}
  </group>;
}

export function TransformerModel({ selected, onSelect, dark }) {
  const { body, fin, selected: active } = material[dark ? 'dark' : 'light'];
  return <group>
    <CoverHardware body={body} />
    <group onClick={event => { event.stopPropagation(); onSelect('oil_temperature_c'); }}>
      <Box position={[0, 0.8, 0]} size={[2.35, 2.25, 1.5]} color={selected === 'tank' ? active : body} />
      <Box position={[0, 1.98, 0]} size={[2.62, 0.13, 1.74]} color={material.cover} />
      <Box position={[0, -0.35, 0]} size={[2.6, 0.16, 1.7]} color={material.pipe} />
      {[-1, 1].map(side => <group key={side}>
        <Cylinder position={[0, 1.65, side * 1.03]} rotation={[0, 0, Math.PI / 2]} radius={0.065} length={2.5} color={body} />
        <Cylinder position={[0, -0.15, side * 1.03]} rotation={[0, 0, Math.PI / 2]} radius={0.065} length={2.5} color={body} />
        {Array.from({ length: 19 }, (_, i) => <Box key={i} position={[-1.09 + i * 0.121, 0.75, side * 0.94]} size={[0.045, 1.82, 0.54]} color={selected === 'tank' ? active : fin} radius={0.016} />)}
      </group>)}
      {[-1, 1].map(side => <group key={side}>
        {Array.from({ length: 9 }, (_, i) => <Box key={i} position={[side * 1.37, 0.76, -0.58 + i * 0.145]} size={[0.42, 1.8, 0.046]} color={fin} radius={0.014} />)}
      </group>)}
    </group>
    {[-0.78, 0, 0.78].map(x => <Bushing x={x} z={-0.05} key={x} onSelect={onSelect} active={selected === 'terminals'} />)}
    {[-0.84, -0.28, 0.28, 0.84].map(x => <Bushing x={x} z={0.58} small key={x} onSelect={onSelect} active={selected === 'terminals'} />)}
    <group onClick={event => { event.stopPropagation(); onSelect('oil_level_pct'); }}>
      {[-0.68, 0.68].map(x => <Box key={x} position={[x, 2.2, -0.56]} size={[0.1, 0.6, 0.1]} color={material.pipe} />)}
      <Cylinder position={[0, 2.66, -0.63]} radius={0.32} length={1.95} rotation={[0, 0, Math.PI / 2]} color={selected === 'conservator' ? active : material.cover} segments={32} />
      {[-0.98, 0.98].map(x => <Cylinder key={x} position={[x, 2.66, -0.63]} radius={0.325} length={0.035} rotation={[0, 0, Math.PI / 2]} color={material.pipe} segments={32} />)}
      <Cylinder position={[0.55, 3.03, -0.63]} radius={0.065} length={0.2} color={material.pipe} />
      <Cylinder position={[0.55, 3.14, -0.63]} radius={0.10} length={0.045} color={material.steel} />
      <Cylinder position={[1.02, 2.66, -0.63]} radius={0.15} length={0.03} rotation={[0, 0, Math.PI / 2]} color={material.gauge} />
      <Cylinder position={[0.85, 2.1, -0.63]} radius={0.04} length={0.75} color={material.pipe} />
    </group>
    <group onClick={event => { event.stopPropagation(); onSelect('rated_capacity'); }}>
      {[-0.85, 0.85].map(x => <group key={x}>
        <Box position={[x, -0.54, 0]} size={[0.19, 0.32, 1.75]} color={selected === 'base' ? active : material.base} />
        <Box position={[x, -0.73, 0]} size={[0.42, 0.11, 2.04]} color={material.darkSteel} />
        {[-0.72, 0.72].map(z => <Cylinder key={z} position={[x, -0.66, z]} radius={0.08} length={0.23} color={material.base} rotation={[0, 0, Math.PI / 2]} />)}
      </group>)}
    </group>
    <Box position={[1.18, 1.45, 0.36]} size={[0.04, 0.32, 0.46]} color={material.nameplate} radius={0.008} />
    <Cylinder position={[1.22, 0.02, 0.58]} radius={0.05} length={0.19} rotation={[0, 0, Math.PI / 2]} color={material.brass} />
    <Cylinder position={[-1.05, 2.13, -0.65]} radius={0.045} length={0.28} color={material.pipe} />
    <Box position={[-1.05, 2.23, -0.65]} size={[0.09, 0.2, 0.05]} color={material.pipe} radius={0.01} />
    <Box position={[1.16, 1.78, -0.6]} size={[0.10, 0.28, 0.10]} color={material.pipe} />
    <Cylinder position={[0, -0.24, 1.23]} radius={0.06} length={0.14} color={material.brass} rotation={[Math.PI / 2, 0, 0]} />
  </group>;
}

function Projection({ onProject }) {
  const previous = useRef('');
  useFrame(({ camera, size }) => {
    const projected = Object.fromEntries(Object.entries(anchors).map(([id, anchor]) => {
      const point = new Vector3(...anchor.position).project(camera);
      return [id, { x: Math.round((point.x + 1) * size.width / 2), y: Math.round((1 - point.y) * size.height / 2) }];
    }));
    projected.axes = sceneAxes(camera);
    const next = JSON.stringify(projected);
    if (next !== previous.current) { previous.current = next; onProject(projected); }
  });
  return null;
}
function SceneControls({ interactive, reset, reduced }) {
  const controls = useRef();
  const previous = useRef(null);
  const resetMotion = useRef(null);
  const { invalidate, size } = useThree();
  useEffect(() => {
    const control = controls.current;
    if (!control) return;
    const zoom = Math.min(78, size.height / (size.width < 620 ? 7.2 : 5.5));
    const last = previous.current;
    if (!last || last.reset !== reset) {
      control.enableDamping = false;
      control.update();
      if (last && !reduced) {
        resetMotion.current = { elapsed: 0, started: false, position: control.object.position.clone(), zoom: control.object.zoom, targetZoom: zoom };
      } else {
        resetMotion.current = null;
        control.object.position.set(7, 5.6, 9);
        control.object.zoom = zoom;
        control.target.set(0, 0.9, 0);
        control.object.updateProjectionMatrix();
        control.update();
        control.enableDamping = !reduced;
      }
    } else if (last.zoom !== zoom) {
      // Resizing the rail keeps the chosen view and relative zoom intact.
      control.object.zoom *= zoom / last.zoom;
      control.object.updateProjectionMatrix();
      if (resetMotion.current) resetMotion.current.targetZoom = zoom;
    }
    previous.current = { reset, zoom };
    invalidate();
  }, [reset, reduced, invalidate, size.height, size.width]);
  useFrame((_, delta) => {
    const tween = resetMotion.current;
    const control = controls.current;
    if (!tween || !control) return;
    // The first demand-rendered frame can follow a long idle interval.
    if (tween.started) tween.elapsed += Math.min(delta, 0.05);
    else tween.started = true;
    const progress = cameraResetProgress(tween.elapsed);
    control.enableDamping = false;
    control.object.position.lerpVectors(tween.position, new Vector3(7, 5.6, 9), progress);
    control.object.zoom = tween.zoom + (tween.targetZoom - tween.zoom) * progress;
    control.target.set(0, 0.9, 0);
    control.object.updateProjectionMatrix();
    control.update();
    if (progress === 1) { resetMotion.current = null; control.enableDamping = !reduced; }
    else invalidate();
  });
  return <OrbitControls ref={controls} enabled={interactive} enablePan={false} enableDamping={!reduced} dampingFactor={0.12} minZoom={Math.min(42, size.height / 8)} maxZoom={size.height / 4.6} minPolarAngle={0.55} maxPolarAngle={1.5} target={[0, 0.9, 0]} />;
}

function ContextGuard({ onProject }) {
  const { gl } = useThree();
  useEffect(() => {
    const lost = event => { event.preventDefault(); onProject(null); };
    const canvas = gl.domElement;
    canvas.addEventListener('webglcontextlost', lost);
    return () => canvas.removeEventListener('webglcontextlost', lost);
  }, [gl, onProject]);
  return null;
}
export default function TransformerScene({ selected, onSelect, onProject, dark, interactive, reset, reduced }) {
  return <Canvas orthographic frameloop="demand" shadows={{ type: PCFShadowMap }} dpr={[1, window.innerWidth < 760 ? 1.2 : 1.5]} camera={{ position: [7, 5.6, 9], zoom: 60, near: 0.1, far: 60 }} gl={{ antialias: true, powerPreference: 'low-power', alpha: true }}>
    <ContextGuard onProject={onProject} />
    <ambientLight intensity={dark ? 1.5 : 1.8} />
    <directionalLight position={[3, 8, 5]} intensity={3.1} castShadow shadow-mapSize={window.innerWidth < 760 ? [512, 512] : [1024, 1024]} shadow-camera-left={-5} shadow-camera-right={5} shadow-camera-top={6} shadow-camera-bottom={-4} shadow-bias={-0.0004} />
    <directionalLight position={[-5, 3, -2]} intensity={1.5} color="#d2e0f1" />
    <TransformerModel selected={selected} onSelect={onSelect} dark={dark} />
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.79, 0]} receiveShadow><planeGeometry args={[200, 200]} /><shadowMaterial transparent opacity={dark ? 0.2 : 0.12} /></mesh>
    <SceneControls interactive={interactive} reset={reset} reduced={reduced} />
    <Projection onProject={onProject} />
  </Canvas>;
}
