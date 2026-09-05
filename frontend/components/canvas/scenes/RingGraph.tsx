"use client";

import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";

import { presenceAt, useStory } from "@/lib/store";
import type { Ring } from "@/lib/types";

/**
 * Scene 04 — Stage 2 ring graph, built from real detection results.
 * Wide triangle layout, larger members, glowing orbit guides; its colour
 * encodes the band (danger only for high/critical).
 */
export function RingGraph({ index }: { index: number }) {
  const group = useRef<THREE.Group>(null);
  // IMPORTANT: never return a fresh [] from the selector — an unstable
  // snapshot makes useSyncExternalStore loop (React error #185).
  const rings = useStory((s) => s.rings?.rings);
  const display = useMemo(
    () => (rings && rings.length ? rings : ghostRings()),
    [rings],
  );

  // drei <Html> keeps rendering in the DOM even when its 3D group hides,
  // and projects to screen centre — so mount labels only while present.
  const [showLabels, setShowLabels] = useState(false);
  const labelsShown = useRef(false);

  const layout = useMemo(() => {
    const spaced = display.slice(0, 3);
    // rings live in the left half of the frame — the panel sits right
    const anchors: [number, number][] = [
      [-9.5, 2.5],
      [-3.5, 3],
      [-7, -5.5],
    ];
    return spaced.map((ring, idx) => {
      const [cx, cz] = anchors[idx % anchors.length];
      const radius = 2.1 + Math.min(1.5, ring.size * 0.14);
      const members = ring.member_ids.slice(0, 18).map((id, i, arr) => {
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

  useFrame((state, delta) => {
    const g = group.current;
    if (!g) return;
    const presence = presenceAt(index, useStory.getState().progress);
    const target = Math.max(0.001, presence);
    g.scale.setScalar(THREE.MathUtils.damp(g.scale.x, target, 3, delta));
    g.visible = presence > 0.02;
    g.rotation.y = Math.sin(state.clock.elapsedTime * 0.12) * 0.22;

    const next = presence > 0.15;
    if (next !== labelsShown.current) {
      labelsShown.current = next;
      setShowLabels(next);
    }
  });

  return (
    <group ref={group} scale={0.001}>
      {layout.map(({ ring, cx, cz, radius, members }, ri) => {
        const danger = ring.risk_band === "high" || ring.risk_band === "critical";
        const colour = danger ? "#FF6B6B" : "#4C8DFF";
        return (
          <group key={ring.ring_id ?? ri}>
            {/* orbit guide */}
            <mesh position={[cx, -0.03, cz]} rotation={[-Math.PI / 2, 0, 0]}>
              <ringGeometry args={[radius - 0.09, radius, 72]} />
              <meshBasicMaterial color={colour} transparent opacity={0.3}
                side={THREE.DoubleSide} />
            </mesh>
            <mesh position={[cx, -0.04, cz]} rotation={[-Math.PI / 2, 0, 0]}>
              <circleGeometry args={[radius - 0.12, 48]} />
              <meshBasicMaterial color={colour} transparent opacity={0.05}
                side={THREE.DoubleSide} />
            </mesh>

            {members.map(({ id, pos }, mi) => (
              <group key={`${ri}-${mi}`}>
                <mesh position={pos}>
                  <sphereGeometry args={[0.24, 22, 22]} />
                  <meshStandardMaterial color={colour} emissive={colour}
                    emissiveIntensity={danger ? 1.1 : 0.5} />
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
                    <lineBasicMaterial color={colour} transparent opacity={0.5} />
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
                <lineBasicMaterial color={colour} transparent opacity={0.5} />
              </line>
            )}

            {/* score label — floats above each ring, only while present */}
            {showLabels && (
              <Html position={[cx, 1.7, cz]} center distanceFactor={16}
                zIndexRange={[10, 0]}>
                <div className="pointer-events-none whitespace-nowrap rounded-full
                  border border-text/15 bg-surface/90 px-4 py-1.5 font-mono text-[13px]
                  text-text shadow-xl shadow-black/40 backdrop-blur-md">
                  {ring.ring_id ?? "RING"} · {ring.ring_score.toFixed(2)}
                </div>
              </Html>
            )}
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
