"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

import { presenceAt, useStory } from "@/lib/store";

const COUNT = 72;

/**
 * Scene 03 — transition: one claim becomes a wide network of linked
 * customers. Nodes bloom outward on a large Fibonacci sphere as the
 * section scrolls into view; the camera passes near the outer shell.
 */
const FRAUD_SET = new Set([3, 9, 14, 22, 27, 33, 38, 44, 51, 58, 63, 69]);

export function NetworkTransition({ index }: { index: number }) {
  const group = useRef<THREE.Group>(null);
  const bloom = useRef(0);

  const nodes = useMemo(() => {
    const pts: [number, number, number][] = [];
    const golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < COUNT; i++) {
      const y = 1 - (i / (COUNT - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const theta = golden * i;
      pts.push([
        Math.cos(theta) * r * 6.4,
        y * 3.6,
        Math.sin(theta) * r * 6.4,
      ]);
    }
    return pts;
  }, []);

  useFrame((state, delta) => {
    const g = group.current;
    if (!g) return;
    const presence = presenceAt(index, useStory.getState().progress);
    const target = Math.max(0.001, presence);
    g.scale.setScalar(THREE.MathUtils.damp(g.scale.x, target, 3, delta));
    g.visible = presence > 0.02;
    g.rotation.y += delta * 0.07;

    if (presence > 0.05) {
      bloom.current = Math.min(1, bloom.current + delta * 0.6);
    } else {
      bloom.current = Math.max(0, bloom.current - delta * 1.2);
    }

    g.children.forEach((child, i) => {
      if (i === 0) return;
      const stagger = THREE.MathUtils.clamp(
        (bloom.current - (i / COUNT) * 0.6) / 0.4, 0, 1);
      child.scale.setScalar(THREE.MathUtils.damp(
        child.scale.x, 0.15 + stagger * 0.85, 4, delta));
    });
    void state;
  });

  return (
    <group ref={group} scale={0.001}>
      <mesh>
        <icosahedronGeometry args={[0.8]} />
        <meshStandardMaterial color="#4C8DFF" emissive="#4C8DFF"
          emissiveIntensity={1.1} />
      </mesh>
      <lineSegments>
        <edgesGeometry args={[new THREE.IcosahedronGeometry(0.8)]} />
        <lineBasicMaterial color="#E8EEF6" transparent opacity={0.5} />
      </lineSegments>

      {nodes.map((pos, i) => {
        const fraud = FRAUD_SET.has(i);
        return (
          <group key={i} scale={0.001}>
            <mesh position={pos}>
              <sphereGeometry args={[fraud ? 0.24 : 0.16, 18, 18]} />
              <meshStandardMaterial
                color={fraud ? "#FF6B6B" : "#4C8DFF"}
                emissive={fraud ? "#FF6B6B" : "#4C8DFF"}
                emissiveIntensity={fraud ? 1.2 : 0.35}
                transparent
                opacity={0.95}
              />
            </mesh>
            <line>
              <bufferGeometry>
                <bufferAttribute
                  attach="attributes-position"
                  args={[new Float32Array([0, 0, 0, ...pos]), 3]}
                />
              </bufferGeometry>
              <lineBasicMaterial
                color={fraud ? "#FF6B6B" : "#4C8DFF"}
                transparent
                opacity={fraud ? 0.5 : 0.14}
              />
            </line>
          </group>
        );
      })}
    </group>
  );
}
