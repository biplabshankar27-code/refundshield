"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

import { presenceAt, useStory } from "@/lib/store";

const LEGIT_COUNT = 900;
const FRAUD_COUNT = 70;

/**
 * Scene 01 — The Problem. A vast drifting field of claim fragments around
 * the camera; a red minority pulses. Built on InstancedMesh for scale.
 */
export function ProblemField({ index }: { index: number }) {
  const group = useRef<THREE.Group>(null);
  const legitRef = useRef<THREE.InstancedMesh>(null);
  const fraudRef = useRef<THREE.InstancedMesh>(null);
  const shell = useRef<THREE.Mesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  const legit = useMemo(() => {
    const rng = (s: number) => {
      let x = s;
      return () => {
        x = (x * 9301 + 49297) % 233280;
        return x / 233280;
      };
    };
    const rand = rng(42);
    return Array.from({ length: LEGIT_COUNT }, () => ({
      pos: new THREE.Vector3(
        (rand() - 0.5) * 52,
        (rand() - 0.5) * 26,
        (rand() - 0.5) * 40 - 4,
      ),
      rot: new THREE.Euler(rand() * Math.PI, rand() * Math.PI, rand() * Math.PI),
      speed: 0.4 + rand() * 0.9,
      spin: (rand() - 0.5) * 0.6,
    }));
  }, []);

  const fraud = useMemo(() => {
    const rng = (s: number) => {
      let x = s;
      return () => {
        x = (x * 9301 + 49297) % 233280;
        return x / 233280;
      };
    };
    const rand = rng(7);
    return Array.from({ length: FRAUD_COUNT }, (_, i) => ({
      pos: new THREE.Vector3(
        (rand() - 0.5) * 40,
        (rand() - 0.5) * 18,
        (rand() - 0.5) * 26 - 2,
      ),
      phase: rand() * Math.PI * 2,
      speed: 0.8 + rand() * 1.4,
      i,
    }));
  }, []);

  useFrame((state, delta) => {
    const g = group.current;
    if (!g) return;
    const presence = presenceAt(index, useStory.getState().progress);
    const target = Math.max(0.001, presence);
    g.scale.setScalar(THREE.MathUtils.damp(g.scale.x, target, 3, delta));
    g.visible = presence > 0.02;
    g.rotation.y += delta * 0.02;

    // drift + spin the legit fragments
    const lm = legitRef.current;
    if (lm) {
      for (let i = 0; i < LEGIT_COUNT; i++) {
        const f = legit[i];
        f.pos.y += f.speed * delta * 0.6;
        if (f.pos.y > 13) f.pos.y = -13;
        dummy.position.copy(f.pos);
        dummy.rotation.set(
          f.rot.x + state.clock.elapsedTime * f.spin,
          f.rot.y + state.clock.elapsedTime * f.spin * 0.7,
          f.rot.z,
        );
        dummy.updateMatrix();
        lm.setMatrixAt(i, dummy.matrix);
      }
      lm.instanceMatrix.needsUpdate = true;
    }

    // pulse the fraud fragments
    const fm = fraudRef.current;
    if (fm) {
      for (let i = 0; i < FRAUD_COUNT; i++) {
        const f = fraud[i];
        const pulse = 0.55 + 0.45 * Math.sin(state.clock.elapsedTime * f.speed + f.phase);
        dummy.position.copy(f.pos);
        dummy.rotation.set(0, state.clock.elapsedTime * 0.4, 0);
        dummy.scale.setScalar(0.8 + 0.5 * pulse);
        dummy.updateMatrix();
        fm.setMatrixAt(i, dummy.matrix);
      }
      fm.instanceMatrix.needsUpdate = true;
      const mat = fm.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 1.1 + 0.5 * Math.sin(state.clock.elapsedTime * 0.8);
    }

    if (shell.current) shell.current.rotation.y -= delta * 0.015;
  });

  return (
    <group ref={group} scale={0.001}>
      {/* giant world shell for depth */}
      <mesh ref={shell} scale={1}>
        <icosahedronGeometry args={[26, 1]} />
        <meshBasicMaterial color="#4C8DFF" wireframe transparent opacity={0.05} />
      </mesh>

      <instancedMesh ref={legitRef} args={[undefined, undefined, LEGIT_COUNT]}>
        <tetrahedronGeometry args={[0.22]} />
        <meshStandardMaterial color="#4C8DFF" transparent opacity={0.55}
          emissive="#4C8DFF" emissiveIntensity={0.25} depthWrite={false} />
      </instancedMesh>

      <instancedMesh ref={fraudRef} args={[undefined, undefined, FRAUD_COUNT]}>
        <tetrahedronGeometry args={[0.42]} />
        <meshStandardMaterial color="#FF6B6B" emissive="#FF6B6B"
          emissiveIntensity={1.2} transparent opacity={0.95} />
      </instancedMesh>
    </group>
  );
}
