"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

import { presenceAt, useStory } from "@/lib/store";

/**
 * Scene 05 — Cost of Delay. Tall columns grow with the 7/14/30-day
 * exposure scenarios on a wide base grid. The 30-day bar is danger-red.
 */
export function CostBars({ index }: { index: number }) {
  const group = useRef<THREE.Group>(null);
  const scenarios = useStory((s) => s.rings?.cost_of_delay.scenarios ?? null);

  const bars = useMemo(() => {
    const order = ["7", "14", "30"];
    const values = scenarios
      ? order.map((k) => scenarios[k] ?? 0)
      : [42000, 68000, 131000]; // placeholder shape before data arrives
    const max = Math.max(...values, 1);
    return order.map((k, i) => ({
      key: k,
      value: values[i],
      height: 1.6 + (values[i] / max) * 4.4,
      x: (i - 1) * 3.4,
      danger: k === "30",
    }));
  }, [scenarios]);

  useFrame((state, delta) => {
    const g = group.current;
    if (!g) return;
    const presence = presenceAt(index, useStory.getState().progress);
    const target = Math.max(0.001, presence);
    g.scale.setScalar(THREE.MathUtils.damp(g.scale.x, target, 3, delta));
    g.visible = presence > 0.02;
    g.rotation.y = Math.sin(state.clock.elapsedTime * 0.2) * 0.16;

    g.children.forEach((child, i) => {
      const bar = bars[i];
      if (!bar || i > 2) return;
      const mesh = child as THREE.Mesh;
      const grow = Math.max(0.04, presence);
      mesh.scale.y = THREE.MathUtils.damp(mesh.scale.y, grow, 2.4, delta);
      mesh.position.y = (bar.height * mesh.scale.y) / 2 - 1.8;
    });
  });

  return (
    <group ref={group} scale={0.001}>
      {bars.map((bar) => (
        <mesh key={bar.key} position={[bar.x, -1.8, 0]}>
          <boxGeometry args={[1.5, bar.height, 1.5]} />
          <meshStandardMaterial
            color={bar.danger ? "#FF6B6B" : "#4C8DFF"}
            emissive={bar.danger ? "#FF6B6B" : "#4C8DFF"}
            emissiveIntensity={bar.danger ? 0.8 : 0.4}
            transparent
            opacity={0.94}
          />
        </mesh>
      ))}
      {/* base grid plane */}
      <mesh position={[0, -1.84, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[11.5, 3]} />
        <meshBasicMaterial color="#4C8DFF" transparent opacity={0.1} />
      </mesh>
      <lineSegments position={[0, -1.83, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <edgesGeometry args={[new THREE.PlaneGeometry(11.5, 3)]} />
        <lineBasicMaterial color="#4C8DFF" transparent opacity={0.25} />
      </lineSegments>
    </group>
  );
}
