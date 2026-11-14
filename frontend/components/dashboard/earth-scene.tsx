"use client";

import { useEffect, useRef, useState } from "react";

type SceneStatus = "loading" | "ready" | "fallback";

export default function EarthScene() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [status, setStatus] = useState<SceneStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    let animationFrame = 0;
    let renderer: import("three").WebGLRenderer | null = null;
    let resizeObserver: ResizeObserver | null = null;

    let cleanupScene: (() => void) | null = null;

    const container = containerRef.current;

    if (!container) {
      setStatus("fallback");
      return;
    }

    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    );

    const navigatorCapabilities = navigator as Navigator & {
      deviceMemory?: number;
    };

    const lowPerformance =
      (navigatorCapabilities.hardwareConcurrency || 2) <= 2 ||
      (navigatorCapabilities.deviceMemory || 4) <= 4;

    if (reducedMotion.matches || lowPerformance) {
      setStatus("fallback");
      return;
    }

    async function initialize() {
      try {
        const THREE = await import("three");

        if (cancelled || !container) return;

        const scene = new THREE.Scene();
        scene.background = new THREE.Color("#07101d");

        const camera = new THREE.PerspectiveCamera(
          38,
          1,
          0.1,
          100
        );

        camera.position.z = 4.2;

        renderer = new THREE.WebGLRenderer({
          alpha: true,
          antialias: false,
          powerPreference: "low-power"
        });

        renderer.setPixelRatio(
          Math.min(window.devicePixelRatio || 1, 1.25)
        );

        renderer.setSize(
          Math.max(container.clientWidth, 1),
          Math.max(container.clientHeight, 1)
        );

        container.appendChild(renderer.domElement);

        const geometry = new THREE.SphereGeometry(1.15, 36, 28);

        const material = new THREE.MeshBasicMaterial({
          color: "#1c6994",
          wireframe: true,
          transparent: true,
          opacity: 0.72
        });

        const earth = new THREE.Mesh(geometry, material);
        scene.add(earth);

        const atmosphereGeometry = new THREE.SphereGeometry(
          1.19,
          28,
          20
        );

        const atmosphereMaterial = new THREE.MeshBasicMaterial({
          color: "#4a9bd2",
          wireframe: true,
          transparent: true,
          opacity: 0.12
        });

        const atmosphere = new THREE.Mesh(
          atmosphereGeometry,
          atmosphereMaterial
        );

        scene.add(atmosphere);

        const resize = () => {
          if (!container || !renderer) return;

          const width = Math.max(container.clientWidth, 1);
          const height = Math.max(container.clientHeight, 1);

          camera.aspect = width / height;
          camera.updateProjectionMatrix();

          renderer.setSize(width, height, false);
        };

        resizeObserver = new ResizeObserver(resize);
        resizeObserver.observe(container);

        const render = () => {
          if (cancelled || !renderer) return;

          earth.rotation.y += 0.0008;
          atmosphere.rotation.y -= 0.0003;

          renderer.render(scene, camera);
          animationFrame = window.requestAnimationFrame(render);
        };

        render();

        cleanupScene = () => {
          geometry.dispose();
          material.dispose();
          atmosphereGeometry.dispose();
          atmosphereMaterial.dispose();
          renderer?.dispose();
        };

        if (!cancelled) {
          setStatus("ready");
        }
      } catch {
        if (!cancelled) {
          setStatus("fallback");
        }
      }
    }

    void initialize();

    return () => {
      cancelled = true;

      window.cancelAnimationFrame(animationFrame);
      resizeObserver?.disconnect();

      cleanupScene?.();

      renderer?.dispose();

      if (renderer?.domElement.parentElement === container) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  if (status === "fallback") {
    return (
      <div className="ag-earth-fallback">
        <div className="ag-earth-fallback-globe" aria-hidden="true">
          ◉
        </div>
        <strong>CONCEPTUAL RENDER</strong>
        <span>NOT LIVE ORBITAL TELEMETRY</span>
        <small>Static mode enabled for performance or accessibility.</small>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="ag-earth-scene"
      data-scene-status={status}
      role="img"
      aria-label="Abstract conceptual wireframe Earth visualization"
    />
  );
}