"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

import { useStory } from "@/lib/store";

/**
 * Scene 05 — Cost of Delay.
 * Three columns grow with the 7/14/30-day exposure scenarios.
 * The 30-day bar is danger-coloured; the rest primary. No other hues.
 */
export function CostBars({ active }: { active: boolean }) {
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
      height: 1.2 + (values[i] / max) * 3.2,
      x: (i - 1) * 2.6,
      danger: k === "30",
    }));
  }, [scenarios]);

  useFrame((state, delta) => {
    const g = group.current;
    if (!g) return;
    const target = active ? 1 : 0.001;
    g.scale.setScalar(THREE.MathUtils.damp(g.scale.x, target, 3, delta));
    g.visible = g.scale.x > 0.01;
    g.rotation.y = THREE.MathUtils.damp(g.rotation.y,
      Math.sin(state.clock.elapsedTime * 0.2) * 0.18, 2, delta);

    g.children.forEach((child, i) => {
      const bar = bars[i];
      if (!bar || i > 2) return;
      const mesh = child as THREE.Mesh;
      const grow = active ? 1 : 0.05;
      mesh.scale.y = THREE.MathUtils.damp(mesh.scale.y, grow, 2.2, delta);
      mesh.position.y = (bar.height * mesh.scale.y) / 2 - 1.4;
    });
  });

  return (
    <group ref={group} scale={0.001}>
      {bars.map((bar) => (
        <mesh key={bar.key} position={[bar.x, -1.4, 0]}>
          <boxGeometry args={[1.1, bar.height, 1.1]} />
          <meshStandardMaterial
            color={bar.danger ? "#FF6B6B" : "#4C8DFF"}
            emissive={bar.danger ? "#FF6B6B" : "#4C8DFF"}
            emissiveIntensity={bar.danger ? 0.7 : 0.35}
            transparent
            opacity={0.92}
          />
        </mesh>
      ))}
      {/* base line */}
      <mesh position={[0, -1.42, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[8.2, 2.2]} />
        <meshBasicMaterial color="#4C8DFF" transparent opacity={0.12} />
      </mesh>
    </group>
  );
}
