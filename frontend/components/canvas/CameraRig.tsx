"use client";

import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";

import { SECTIONS, useStory } from "@/lib/store";

/**
 * Cinematic camera: eases to the active section's position/target and adds
 * a subtle pointer parallax. Transitions between sections are the story.
 */
export function CameraRig() {
  const section = useStory((s) => s.section);
  const target = useRef(new THREE.Vector3(0, 0, 0));
  const desiredPos = useRef(new THREE.Vector3(...SECTIONS[0].camera.pos));
  const desiredLook = useRef(new THREE.Vector3(...SECTIONS[0].camera.look));

  useFrame((state, delta) => {
    const cam = SECTIONS[section].camera;
    desiredPos.current.set(...cam.pos);
    desiredLook.current.set(...cam.look);

    const parallaxX = state.pointer.x * 0.6;
    const parallaxY = state.pointer.y * 0.35;

    state.camera.position.x = THREE.MathUtils.damp(
      state.camera.position.x, desiredPos.current.x + parallaxX, 2.2, delta);
    state.camera.position.y = THREE.MathUtils.damp(
      state.camera.position.y, desiredPos.current.y + parallaxY, 2.2, delta);
    state.camera.position.z = THREE.MathUtils.damp(
      state.camera.position.z, desiredPos.current.z, 2.2, delta);

    target.current.x = THREE.MathUtils.damp(
      target.current.x, desiredLook.current.x, 2.4, delta);
    target.current.y = THREE.MathUtils.damp(
      target.current.y, desiredLook.current.y, 2.4, delta);
    target.current.z = THREE.MathUtils.damp(
      target.current.z, desiredLook.current.z, 2.4, delta);

    state.camera.lookAt(target.current);
  });

  return null;
}
