"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

import { presenceAt, spotlightClaim, useStory } from "@/lib/store";
import type { Signal } from "@/lib/types";

/**
 * Scene 02 — Stage 1 spotlight. A big claim card with its four signals
 * orbiting on a tilted ring; the strongest-risk signal burns danger-red.
 */
export function ClaimSpotlight({ index }: { index: number }) {
  const group = useRef<THREE.Group>(null);
  const orbit = useRef<THREE.Group>(null);
  const ringA = useRef<THREE.Mesh>(null);
  const ringB = useRef<THREE.Mesh>(null);
  const claims = useStory((s) => s.claims);
  const claim = spotlightClaim(claims);

  const signals: Signal[] = useMemo(() => {
    if (claim?.payload?.signals) return claim.payload.signals;
    return ["image_evidence", "history_evidence", "payment_delivery_evidence", "text_evidence"]
      .map((name) => ({ name, score: 0.2, weight: 0.25, contribution: 0.05, detail: "" }));
  }, [claim]);

  const hottest = signals.reduce(
    (best, s) => (s.score > best.score ? s : best),
    signals[0],
  );

  const RADIUS = 4.6;
  const nodes = useMemo(
    () =>
      signals.map((s, i) => {
        const angle = (i / signals.length) * Math.PI * 2 + Math.PI / 4;
        return {
          signal: s,
          pos: [
            Math.cos(angle) * RADIUS,
            Math.sin(angle) * RADIUS * 0.5,
            Math.sin(angle * 2) * 0.9,
          ] as [number, number, number],
        };
      }),
    [signals],
  );

  useFrame((state, delta) => {
    const g = group.current;
    if (!g) return;
    const presence = presenceAt(index, useStory.getState().progress);
    const target = Math.max(0.001, presence);
    g.scale.setScalar(THREE.MathUtils.damp(g.scale.x, target, 3, delta));
    g.visible = presence > 0.02;
    g.rotation.y = Math.sin(state.clock.elapsedTime * 0.15) * 0.28;

    if (orbit.current) orbit.current.rotation.z += delta * 0.16;
    if (ringA.current) ringA.current.rotation.x += delta * 0.22;
    if (ringB.current) ringB.current.rotation.y -= delta * 0.18;
  });

  return (
    <group ref={group} scale={0.001}>
      {/* claim card */}
      <group>
        <mesh>
          <boxGeometry args={[2.8, 3.9, 0.18]} />
          <meshStandardMaterial color="#151C26" metalness={0.25} roughness={0.3} />
        </mesh>
        <lineSegments>
          <edgesGeometry args={[new THREE.BoxGeometry(2.8, 3.9, 0.18)]} />
          <lineBasicMaterial color="#4C8DFF" transparent opacity={0.95} />
        </lineSegments>
        <pointLight position={[0, 0, 2]} intensity={6} color="#4C8DFF" />
        {/* pseudo text lines */}
        {[1.2, 0.65, 0.1, -0.45].map((y, i) => (
          <mesh key={i} position={[i === 3 ? -0.75 : -0.4, y, 0.1]}>
            <planeGeometry args={[i === 3 ? 1.3 : 1.9, 0.09]} />
            <meshBasicMaterial color="#E8EEF6" transparent opacity={0.28} />
          </mesh>
        ))}
        <mesh position={[-0.8, -1.2, 0.1]}>
          <planeGeometry args={[0.9, 0.3]} />
          <meshBasicMaterial color={hottest.score >= 0.6 ? "#FF6B6B" : "#4C8DFF"} />
        </mesh>
      </group>

      {/* halo rings */}
      <mesh ref={ringA} rotation={[Math.PI / 2.4, 0.3, 0]}>
        <torusGeometry args={[4.1, 0.02, 12, 96]} />
        <meshBasicMaterial color="#4C8DFF" transparent opacity={0.35} />
      </mesh>
      <mesh ref={ringB} rotation={[Math.PI / 2.8, -0.4, 0.4]}>
        <torusGeometry args={[4.7, 0.012, 12, 96]} />
        <meshBasicMaterial color="#8AE0B0" transparent opacity={0.18} />
      </mesh>

      {/* orbiting signal satellites + spokes */}
      <group ref={orbit}>
        {nodes.map(({ signal, pos }, i) => {
          const hot = signal.name === hottest.name && signal.score >= 0.55;
          return (
            <group key={i}>
              <mesh position={pos}>
                <icosahedronGeometry args={[hot ? 0.44 : 0.34]} />
                <meshStandardMaterial
                  color={hot ? "#FF6B6B" : "#4C8DFF"}
                  emissive={hot ? "#FF6B6B" : "#4C8DFF"}
                  emissiveIntensity={hot ? 1.3 : 0.4}
                />
              </mesh>
              <line>
                <bufferGeometry>
                  <bufferAttribute
                    attach="attributes-position"
                    args={[new Float32Array([0, 0, 0.09, ...pos]), 3]}
                  />
                </bufferGeometry>
                <lineBasicMaterial
                  color={hot ? "#FF6B6B" : "#4C8DFF"}
                  transparent
                  opacity={hot ? 0.85 : 0.35}
                />
              </line>
            </group>
          );
        })}
      </group>
    </group>
  );
}
