"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

import { presenceAt, useStory } from "@/lib/store";

const LINES = 24;

/**
 * Scene 06 — Audit & Trust. A wide helix of log entries rises around a
 * calm shield core wrapped in a slow accent ring.
 */
export function AuditLedger({ index }: { index: number }) {
  const group = useRef<THREE.Group>(null);
  const helix = useRef<THREE.Group>(null);
  const ring = useRef<THREE.Mesh>(null);

  const entries = useMemo(
    () =>
      Array.from({ length: LINES }, (_, i) => ({
        y: -3 + (i / LINES) * 6,
        angle: i * 0.62,
        width: 1.1 + (i % 3) * 0.45,
      })),
    [],
  );

  useFrame((state, delta) => {
    const g = group.current;
    if (!g) return;
    const presence = presenceAt(index, useStory.getState().progress);
    const target = Math.max(0.001, presence);
    g.scale.setScalar(THREE.MathUtils.damp(g.scale.x, target, 3, delta));
    g.visible = presence > 0.02;
    if (helix.current) {
      helix.current.rotation.y += delta * 0.26;
      helix.current.position.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.22;
    }
    if (ring.current) {
      ring.current.rotation.z += delta * 0.4;
      const s = 1 + 0.03 * Math.sin(state.clock.elapsedTime * 1.4);
      ring.current.scale.setScalar(s);
    }
  });

  return (
    <group ref={group} scale={0.001}>
      {/* shield core */}
      <mesh>
        <octahedronGeometry args={[1.15]} />
        <meshStandardMaterial color="#151C26" metalness={0.45} roughness={0.25} />
      </mesh>
      <lineSegments>
        <edgesGeometry args={[new THREE.OctahedronGeometry(1.15)]} />
        <lineBasicMaterial color="#8AE0B0" transparent opacity={0.9} />
      </lineSegments>
      <mesh ref={ring} rotation={[Math.PI / 2.2, 0.2, 0]}>
        <torusGeometry args={[2.1, 0.025, 12, 90]} />
        <meshBasicMaterial color="#8AE0B0" transparent opacity={0.4} />
      </mesh>

      <group ref={helix}>
        {entries.map((e, i) => (
          <mesh key={i}
            position={[Math.cos(e.angle) * 3, e.y, Math.sin(e.angle) * 3]}
            rotation={[0, -e.angle, 0]}>
            <planeGeometry args={[e.width, 0.12]} />
            <meshBasicMaterial
              color={i % 4 === 0 ? "#8AE0B0" : "#4C8DFF"}
              transparent
              opacity={0.6}
              side={THREE.DoubleSide}
            />
          </mesh>
        ))}
      </group>
    </group>
  );
}
