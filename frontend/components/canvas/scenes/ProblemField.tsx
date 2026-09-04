"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

import { useStory } from "@/lib/store";

/**
 * Scene 01 — The Problem.
 * A slow river of claim fragments; a red minority pulses (fraudulent ones).
 */
export function ProblemField({ active }: { active: boolean }) {
  const group = useRef<THREE.Group>(null);
  const fraud = useRef<THREE.Mesh>(null);
  const section = useStory((s) => s.section);

  const legit = useMemo(() => {
    const positions = new Float32Array(340 * 3);
    for (let i = 0; i < 340; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 30;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 14;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 14;
    }
    return positions;
  }, []);

  const fraudSeeds = useMemo(
    () =>
      Array.from({ length: 26 }, () => ({
        pos: [
          (Math.random() - 0.5) * 22,
          (Math.random() - 0.5) * 10,
          (Math.random() - 0.5) * 10,
        ] as [number, number, number],
        phase: Math.random() * Math.PI * 2,
        speed: 0.5 + Math.random(),
      })),
    [],
  );

  useFrame((state, delta) => {
    const g = group.current;
    if (g) {
      const target = active ? 1 : 0.001;
      g.scale.setScalar(THREE.MathUtils.damp(g.scale.x, target, 3, delta));
      g.rotation.y += delta * 0.03;
      g.visible = g.scale.x > 0.01;
    }
    fraud.current?.children.forEach((child, i) => {
      const seed = fraudSeeds[i];
      if (!seed) return;
      const pulse = 0.55 + 0.45 * Math.sin(state.clock.elapsedTime * seed.speed + seed.phase);
      const mesh = child as THREE.Mesh;
      const mat = mesh.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = pulse * 1.4;
      mesh.scale.setScalar(0.9 + 0.25 * pulse);
    });
    void section;
  });

  return (
    <group ref={group} scale={0.001}>
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[legit, 3]} />
        </bufferGeometry>
        <pointsMaterial size={0.09} color="#4C8DFF" transparent opacity={0.5}
          sizeAttenuation depthWrite={false} />
      </points>

      <group ref={fraud}>
        {fraudSeeds.map((s, i) => (
          <mesh key={i} position={s.pos}>
            <tetrahedronGeometry args={[0.16]} />
            <meshStandardMaterial color="#FF6B6B" emissive="#FF6B6B"
              emissiveIntensity={0.8} transparent opacity={0.9} />
          </mesh>
        ))}
      </group>
    </group>
  );
}
