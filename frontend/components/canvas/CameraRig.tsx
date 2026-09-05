"use client";

import { useFrame } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import * as THREE from "three";

import { cameraAt, useStory } from "@/lib/store";

/**
 * Scroll-driven cinematic camera. The whole scroll range maps to a smooth
 * path through the six chapter keyframes; pointer movement adds parallax.
 */
export function CameraRig() {
  const pos = useRef(new THREE.Vector3(0, 2, 20));
  const look = useRef(new THREE.Vector3(0, 0, 0));
  const targetPos = useRef(new THREE.Vector3());
  const targetLook = useRef(new THREE.Vector3());
  const pointer = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const onMove = (e: PointerEvent | MouseEvent) => {
      pointer.current.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.current.y = (e.clientY / window.innerHeight) * 2 - 1;
    };
    window.addEventListener("pointermove", onMove);
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  useFrame((state, delta) => {
    const { pos: p, look: l } = cameraAt(useStory.getState().progress);
    const px = pointer.current.x * 0.9;
    const py = pointer.current.y * 0.5;

    targetPos.current.set(p[0] + px, p[1] + py, p[2]);
    targetLook.current.set(...l);

    pos.current.x = THREE.MathUtils.damp(pos.current.x, targetPos.current.x, 3, delta);
    pos.current.y = THREE.MathUtils.damp(pos.current.y, targetPos.current.y, 3, delta);
    pos.current.z = THREE.MathUtils.damp(pos.current.z, targetPos.current.z, 3, delta);

    look.current.x = THREE.MathUtils.damp(look.current.x, targetLook.current.x, 3, delta);
    look.current.y = THREE.MathUtils.damp(look.current.y, targetLook.current.y, 3, delta);
    look.current.z = THREE.MathUtils.damp(look.current.z, targetLook.current.z, 3, delta);

    state.camera.position.copy(pos.current);
    state.camera.lookAt(look.current);
  });

  return null;
}
