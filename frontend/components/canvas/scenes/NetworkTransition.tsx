"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

/**
 * Scene 03 — transition: one claim becomes a network of linked customers.
 * Nodes bloom outward on a Fibonacci sphere; spokes stay subtle.
 */
const COUNT = 42;

export function NetworkTransition({ active }: { active: boolean }) {
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
        Math.cos(theta) * r * 4.4,
        y * 2.6,
        Math.sin(theta) * r * 4.4,
      ]);
    }
    return pts;
  }, []);

  const fraudSet = useMemo(
    () => new Set([3, 9, 14, 22, 27, 33, 38]),
    [],
  );

  useFrame((state, delta) => {
    const g = group.current;
    if (!g) return;
    const target = active ? 1 : 0.001;
    g.scale.setScalar(THREE.MathUtils.damp(g.scale.x, target, 3, delta));
    g.visible = g.scale.x > 0.01;
    g.rotation.y += delta * 0.06;
    if (active) bloom.current = Math.min(1, bloom.current + delta * 0.5);
    else bloom.current = Math.max(0, bloom.current - delta * 0.8);

    g.children.forEach((child, i) => {
      if (i === 0) return; // centre node
      const stagger = THREE.MathUtils.clamp(
        (bloom.current - (i / COUNT) * 0.6) / 0.4, 0, 1);
      child.scale.setScalar(THREE.MathUtils.damp(
        child.scale.x, 0.2 + stagger * 0.8, 4, delta));
    });
    void state;
  });

  return (
    <group ref={group} scale={0.001}>
      <mesh>
        <icosahedronGeometry args={[0.5]} />
        <meshStandardMaterial color="#4C8DFF" emissive="#4C8DFF"
          emissiveIntensity={0.9} />
      </mesh>

      {nodes.map((pos, i) => {
        const fraud = fraudSet.has(i);
        return (
          <group key={i} scale={0.001}>
            <mesh position={pos}>
              <sphereGeometry args={[fraud ? 0.17 : 0.12, 16, 16]} />
              <meshStandardMaterial
                color={fraud ? "#FF6B6B" : "#4C8DFF"}
                emissive={fraud ? "#FF6B6B" : "#4C8DFF"}
                emissiveIntensity={fraud ? 1.0 : 0.3}
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
                opacity={fraud ? 0.5 : 0.16}
              />
            </line>
          </group>
        );
      })}
    </group>
  );
}
