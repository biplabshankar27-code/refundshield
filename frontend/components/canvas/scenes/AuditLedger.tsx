"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

/**
 * Scene 06 — Audit & Trust.
 * A slow helix of log entries rises around a calm shield core.
 * Accent (mint) marks verification — the only place it appears in 3D.
 */
const LINES = 18;

export function AuditLedger({ active }: { active: boolean }) {
  const group = useRef<THREE.Group>(null);
  const helix = useRef<THREE.Group>(null);

  const entries = useMemo(
    () =>
      Array.from({ length: LINES }, (_, i) => ({
        y: -2.4 + (i / LINES) * 4.8,
        angle: i * 0.55,
        width: 1.2 + (i % 3) * 0.5,
      })),
    [],
  );

  useFrame((state, delta) => {
    const g = group.current;
    if (!g) return;
    const target = active ? 1 : 0.001;
    g.scale.setScalar(THREE.MathUtils.damp(g.scale.x, target, 3, delta));
    g.visible = g.scale.x > 0.01;
    if (helix.current) {
      helix.current.rotation.y += delta * 0.22;
      helix.current.position.y =
        Math.sin(state.clock.elapsedTime * 0.5) * 0.18;
    }
  });

  return (
    <group ref={group} scale={0.001}>
      {/* shield core */}
      <mesh>
        <octahedronGeometry args={[0.85]} />
        <meshStandardMaterial color="#151C26" metalness={0.4} roughness={0.25} />
      </mesh>
      <lineSegments>
        <edgesGeometry args={[new THREE.OctahedronGeometry(0.85)]} />
        <lineBasicMaterial color="#8AE0B0" transparent opacity={0.85} />
      </lineSegments>

      <group ref={helix}>
        {entries.map((e, i) => (
          <mesh key={i}
            position={[Math.cos(e.angle) * 2.3, e.y, Math.sin(e.angle) * 2.3]}
            rotation={[0, -e.angle, 0]}>
            <planeGeometry args={[e.width, 0.09]} />
            <meshBasicMaterial
              color={i % 4 === 0 ? "#8AE0B0" : "#4C8DFF"}
              transparent
              opacity={0.55}
              side={THREE.DoubleSide}
            />
          </mesh>
        ))}
      </group>
    </group>
  );
}
