"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

import { spotlightClaim, useStory } from "@/lib/store";
import type { Signal } from "@/lib/types";

/**
 * Scene 02 — Stage 1 spotlight.
 * One claim card in the centre; its four signals orbit as satellites.
 * The strongest-risk signal burns danger-coloured; the rest stay primary.
 */
export function ClaimSpotlight({ active }: { active: boolean }) {
  const group = useRef<THREE.Group>(null);
  const orbit = useRef<THREE.Group>(null);
  const claims = useStory((s) => s.claims);
  const claim = spotlightClaim(claims);

  const signals: Signal[] = useMemo(() => {
    if (claim?.payload?.signals) return claim.payload.signals;
    // graceful placeholder while data loads
    return ["image_evidence", "history_evidence", "payment_delivery_evidence", "text_evidence"]
      .map((name) => ({ name, score: 0.2, weight: 0.25, contribution: 0.05, detail: "" }));
  }, [claim]);

  const hottest = signals.reduce(
    (best, s) => (s.score > best.score ? s : best),
    signals[0],
  );

  const RADIUS = 3.1;
  const nodes = useMemo(
    () =>
      signals.map((s, i) => {
        const angle = (i / signals.length) * Math.PI * 2 + Math.PI / 4;
        return {
          signal: s,
          pos: [
            Math.cos(angle) * RADIUS,
            Math.sin(angle) * RADIUS * 0.55,
            Math.sin(angle * 2) * 0.8,
          ] as [number, number, number],
        };
      }),
    [signals],
  );

  useFrame((state, delta) => {
    const g = group.current;
    if (g) {
      const target = active ? 1 : 0.001;
      g.scale.setScalar(THREE.MathUtils.damp(g.scale.x, target, 3, delta));
      g.visible = g.scale.x > 0.01;
      g.rotation.y = THREE.MathUtils.damp(
        g.rotation.y, Math.sin(state.clock.elapsedTime * 0.15) * 0.25, 2, delta);
    }
    if (orbit.current) orbit.current.rotation.z += delta * 0.12;
  });

  return (
    <group ref={group} scale={0.001}>
      {/* claim card */}
      <group>
        <mesh>
          <boxGeometry args={[2.1, 2.9, 0.14]} />
          <meshStandardMaterial color="#151C26" metalness={0.2} roughness={0.35} />
        </mesh>
        <lineSegments>
          <edgesGeometry args={[new THREE.BoxGeometry(2.1, 2.9, 0.14)]} />
          <lineBasicMaterial color="#4C8DFF" transparent opacity={0.9} />
        </lineSegments>
        {/* pseudo text lines on the card */}
        {[0.9, 0.5, 0.1, -0.3].map((y, i) => (
          <mesh key={i} position={[i === 3 ? -0.55 : -0.3, y, 0.08]}>
            <planeGeometry args={[i === 3 ? 1.0 : 1.4, 0.07]} />
            <meshBasicMaterial color="#E8EEF6" transparent opacity={0.25} />
          </mesh>
        ))}
        <mesh position={[-0.62, -0.62, 0.08]}>
          <planeGeometry args={[0.7, 0.22]} />
          <meshBasicMaterial color={hottest.score >= 0.6 ? "#FF6B6B" : "#4C8DFF"} />
        </mesh>
      </group>

      {/* orbiting signal satellites + spokes (static inside rotating group) */}
      <group ref={orbit}>
        {nodes.map(({ signal, pos }, i) => {
          const hot = signal.name === hottest.name && signal.score >= 0.55;
          return (
            <group key={i}>
              <mesh position={pos}>
                <icosahedronGeometry args={[hot ? 0.34 : 0.26]} />
                <meshStandardMaterial
                  color={hot ? "#FF6B6B" : "#4C8DFF"}
                  emissive={hot ? "#FF6B6B" : "#4C8DFF"}
                  emissiveIntensity={hot ? 1.1 : 0.35}
                />
              </mesh>
              <line>
                <bufferGeometry>
                  <bufferAttribute
                    attach="attributes-position"
                    args={[new Float32Array([0, 0, 0.07, ...pos]), 3]}
                  />
                </bufferGeometry>
                <lineBasicMaterial
                  color={hot ? "#FF6B6B" : "#4C8DFF"}
                  transparent
                  opacity={hot ? 0.8 : 0.3}
                />
              </line>
            </group>
          );
        })}
      </group>
    </group>
  );
}
