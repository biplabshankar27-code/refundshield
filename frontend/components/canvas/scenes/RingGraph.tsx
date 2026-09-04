"use client";

import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

import { useStory } from "@/lib/store";
import type { Ring } from "@/lib/types";

/**
 * Scene 04 — Stage 2 ring graph, built from real detection results.
 * Each ring is a circle of member nodes; its colour encodes the band
 * (danger only for high/critical). Ghost rings appear when no data yet.
 */
export function RingGraph({ active }: { active: boolean }) {
  const group = useRef<THREE.Group>(null);
  // IMPORTANT: never return a fresh [] from the selector — an unstable
  // snapshot makes useSyncExternalStore loop (React error #185).
  const rings = useStory((s) => s.rings?.rings);
  const display = useMemo(
    () => (rings && rings.length ? rings : ghostRings()),
    [rings],
  );

  const layout = useMemo(() => {
    const spaced = display.slice(0, 4);
    return spaced.map((ring, idx) => {
      const cols = Math.min(3, Math.ceil(spaced.length / 2));
      const row = Math.floor(idx / cols);
      const col = idx % cols;
      const cx = (col - (cols - 1) / 2) * 7.2;
      const cz = (row - 0.5) * 7.2;
      const radius = 1.6 + Math.min(1.4, ring.size * 0.12);
      const members = ring.member_ids.slice(0, 16).map((id, i, arr) => {
        const a = (i / Math.max(1, arr.length)) * Math.PI * 2;
        return {
          id,
          pos: [cx + Math.cos(a) * radius, 0, cz + Math.sin(a) * radius] as [
            number, number, number,
          ],
        };
      });
      return { ring, cx, cz, radius, members };
    });
  }, [display]);

  useFrame((_, delta) => {
    const g = group.current;
    if (!g) return;
    const target = active ? 1 : 0.001;
    g.scale.setScalar(THREE.MathUtils.damp(g.scale.x, target, 3, delta));
    g.visible = g.scale.x > 0.01;
    g.rotation.y = THREE.MathUtils.damp(g.rotation.y,
      Math.sin(Date.now() * 0.0001) * 0.35, 1.5, delta);
  });

  return (
    <group ref={group} scale={0.001}>
      {layout.map(({ ring, cx, cz, radius, members }, ri) => {
        const danger = ring.risk_band === "high" || ring.risk_band === "critical";
        const colour = danger ? "#FF6B6B" : "#4C8DFF";
        return (
          <group key={ring.ring_id ?? ri}>
            {/* ring orbit guide */}
            <mesh position={[cx, -0.02, cz]} rotation={[-Math.PI / 2, 0, 0]}>
              <ringGeometry args={[radius - 0.05, radius, 64]} />
              <meshBasicMaterial color={colour} transparent opacity={0.25}
                side={THREE.DoubleSide} />
            </mesh>

            {members.map(({ id, pos }, mi) => (
              <group key={`${ri}-${mi}`}>
                <mesh position={pos}>
                  <sphereGeometry args={[0.16, 20, 20]} />
                  <meshStandardMaterial color={colour} emissive={colour}
                    emissiveIntensity={danger ? 0.9 : 0.4} />
                </mesh>
                {mi > 0 && (
                  <line>
                    <bufferGeometry>
                      <bufferAttribute
                        attach="attributes-position"
                        args={[new Float32Array([
                          ...members[mi - 1].pos, ...pos,
                        ]), 3]}
                      />
                    </bufferGeometry>
                    <lineBasicMaterial color={colour} transparent opacity={0.45} />
                  </line>
                )}
              </group>
            ))}
            {/* closing edge */}
            {members.length > 2 && (
              <line>
                <bufferGeometry>
                  <bufferAttribute
                    attach="attributes-position"
                    args={[new Float32Array([
                      ...members[members.length - 1].pos, ...members[0].pos,
                    ]), 3]}
                  />
                </bufferGeometry>
                <lineBasicMaterial color={colour} transparent opacity={0.45} />
              </line>
            )}

            {/* score label */}
            <Html position={[cx, 1.15, cz]} center distanceFactor={12}
              zIndexRange={[10, 0]}>
              <div className="pointer-events-none whitespace-nowrap rounded-full
                border border-text/15 bg-surface/85 px-3 py-1 font-mono text-[11px]
                text-text backdrop-blur-md">
                {ring.ring_id ?? "RING"} · {ring.ring_score.toFixed(2)}
              </div>
            </Html>
          </group>
        );
      })}
    </group>
  );
}

/** Placeholder rings so the story works before the first detection run. */
function ghostRings(): Ring[] {
  return [0, 1, 2].map((i) => ({
    ring_id: `GHOST-${i + 1}`,
    member_ids: Array.from({ length: 6 }, (_, m) => `ghost-${i}-${m}`),
    size: 6,
    avg_stage1_risk: 0.5,
    graph_density: 0.9,
    temporal_coordination_score: 0.6,
    ring_score: 0.66,
    risk_band: i === 0 ? "critical" : "high",
    estimated_exposure_inr: 0,
    shared_entities: {},
    adversarial_flags: [],
    explanation: "",
    members: [],
  }));
}
