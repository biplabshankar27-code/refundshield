"use client";

import { Canvas } from "@react-three/fiber";
import { PALETTE } from "@/lib/theme";

import { AmbientDust } from "./AmbientDust";
import { CameraRig } from "./CameraRig";
import { AuditLedger } from "./scenes/AuditLedger";
import { ClaimSpotlight } from "./scenes/ClaimSpotlight";
import { CostBars } from "./scenes/CostBars";
import { NetworkTransition } from "./scenes/NetworkTransition";
import { ProblemField } from "./scenes/ProblemField";
import { RingGraph } from "./scenes/RingGraph";
import { useStory } from "@/lib/store";

/**
 * The 3D stage. Every scene stays mounted (cheap) and scales itself in
 * only while its story section is active — camera motion carries the tale.
 */
export default function StoryCanvas() {
  const section = useStory((s) => s.section);
  const active = (i: number) => section === i;

  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ position: [0, 3, 16], fov: 42, near: 0.1, far: 100 }}
      gl={{ antialias: true, alpha: false }}
    >
      <color attach="background" args={[PALETTE.background]} />
      <fog attach="fog" args={[PALETTE.background, 20, 46]} />

      <ambientLight intensity={0.4} />
      <directionalLight position={[6, 10, 4]} intensity={1.15} />
      <directionalLight position={[-6, -4, -6]} intensity={0.25} color={PALETTE.primary} />

      <CameraRig />
      <AmbientDust />

      <ProblemField active={active(0)} />
      <ClaimSpotlight active={active(1)} />
      <NetworkTransition active={active(2)} />
      <RingGraph active={active(3)} />
      <CostBars active={active(4)} />
      <AuditLedger active={active(5)} />
    </Canvas>
  );
}
