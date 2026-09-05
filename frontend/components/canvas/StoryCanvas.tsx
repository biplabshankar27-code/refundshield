"use client";

import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";
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

/**
 * The 3D stage. Fixed behind the scrolling page; every scene reads the
 * store's scroll progress imperatively inside useFrame (no re-renders on
 * scroll) and reveals itself by presence.
 */
export default function StoryCanvas() {
  return (
    <Canvas
      dpr={[1, 1.75]}
      camera={{ position: [0, 2, 20], fov: 50, near: 0.1, far: 120 }}
      gl={{ antialias: false, alpha: false, powerPreference: "high-performance" }}
      style={{ touchAction: "pan-y" }}
    >
      <color attach="background" args={[PALETTE.background]} />
      <fog attach="fog" args={[PALETTE.background, 24, 60]} />

      <ambientLight intensity={0.45} />
      <directionalLight position={[8, 12, 5]} intensity={1.2} />
      <directionalLight position={[-8, -4, -6]} intensity={0.3} color={PALETTE.primary} />
      <pointLight position={[0, 2, 6]} intensity={12} color={PALETTE.primary} />

      <CameraRig />
      <AmbientDust count={420} />

      <ProblemField index={0} />
      <ClaimSpotlight index={1} />
      <NetworkTransition index={2} />
      <RingGraph index={3} />
      <CostBars index={4} />
      <AuditLedger index={5} />

      <EffectComposer multisampling={4}>
        <Bloom intensity={0.55} luminanceThreshold={0.25} luminanceSmoothing={0.2} mipmapBlur />
        <Vignette eskil={false} offset={0.25} darkness={0.6} />
      </EffectComposer>
    </Canvas>
  );
}
