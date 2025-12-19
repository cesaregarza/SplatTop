import { useCallback, useEffect, useRef, useState } from "react";

import { createCompetitionVizRuntime } from "./competitionVizRuntime";

const useCompetitionVizRuntime = ({
  sceneData,
  rootRef,
  canvasRef,
  canvasContainerRef,
  scatterCanvasRef,
  barCanvasRef,
  convergenceCanvasRef,
  btnStepRef,
  btnAutoRef,
  btnResetRef,
  btnExportRef,
  speedSliderRef,
  speedValueRef,
  iterCountRef,
  statusTextRef,
  deltaValueRef,
  deltaBarRef,
  insightTextRef,
  correlationValueRef,
  nodeCountRef,
  edgeCountRef,
  dampingValueRef,
  thresholdValueRef,
  leaderNameRef,
  leaderScoreRef,
  leaderSkillRef,
  leaderWinsRef,
  leaderOppRef,
}) => {
  const [unsupported, setUnsupported] = useState(null);
  const [ready, setReady] = useState(false);
  const runtimeRef = useRef(null);

  useEffect(() => {
    const resizeSupported = typeof ResizeObserver !== "undefined";
    const contextSupported = Boolean(canvasRef.current?.getContext?.("2d"));
    if (!resizeSupported) {
      setUnsupported(
        "This interactive explainer needs a modern browser that supports ResizeObserver."
      );
      return undefined;
    }
    if (!contextSupported) {
      setUnsupported("Canvas rendering is not available in this browser.");
      return undefined;
    }

    const root = rootRef.current;
    const canvas = canvasRef.current;
    const canvasContainer = canvasContainerRef.current;
    const scatterCanvas = scatterCanvasRef.current;
    const barCanvas = barCanvasRef.current;
    const convergenceCanvas = convergenceCanvasRef.current;

    const ui = {
      btnStep: btnStepRef.current,
      btnAuto: btnAutoRef.current,
      btnReset: btnResetRef.current,
      btnExport: btnExportRef.current,
      speedSlider: speedSliderRef.current,
      speedValue: speedValueRef.current,
      iterCount: iterCountRef.current,
      statusText: statusTextRef.current,
      deltaValue: deltaValueRef.current,
      deltaBar: deltaBarRef.current,
      insightText: insightTextRef.current,
      correlationValue: correlationValueRef.current,
      nodeCount: nodeCountRef.current,
      edgeCount: edgeCountRef.current,
      dampingValue: dampingValueRef.current,
      thresholdValue: thresholdValueRef.current,
      leaderName: leaderNameRef.current,
      leaderScore: leaderScoreRef.current,
      leaderSkill: leaderSkillRef.current,
      leaderWins: leaderWinsRef.current,
      leaderOpp: leaderOppRef.current,
    };

    const hasAllRequiredElements =
      root &&
      canvas &&
      canvasContainer &&
      scatterCanvas &&
      barCanvas &&
      convergenceCanvas &&
      Object.values(ui).every(Boolean);
    if (!hasAllRequiredElements) {
      setUnsupported("Unable to mount the ranking simulator UI.");
      return undefined;
    }

    const doc = root.ownerDocument || document;
    const view = doc.defaultView || window;

    const runtime = createCompetitionVizRuntime({
      sceneData,
      root,
      canvas,
      canvasContainer,
      scatterCanvas,
      barCanvas,
      convergenceCanvas,
      ui,
      doc,
      view,
    });
    runtimeRef.current = runtime;
    runtime.start();
    setReady(true);

    return () => {
      runtime.dispose();
      runtimeRef.current = null;
    };
    // Refs are stable; this init is intentionally one-time.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { unsupported, ready, runtimeRef };
};

const useCompetitionVizAnimationLoop = (runtimeRef, enabled) => {
  useEffect(() => {
    if (!enabled) return undefined;

    let rafId = null;
    const step = () => {
      runtimeRef.current?.tick();
      rafId = window.requestAnimationFrame(step);
    };

    rafId = window.requestAnimationFrame(step);
    return () => {
      if (rafId) window.cancelAnimationFrame(rafId);
    };
  }, [enabled, runtimeRef]);
};

const useCompetitionVizCanvasResize = (runtimeRef, canvasContainerRef, enabled) => {
  useEffect(() => {
    if (!enabled) return undefined;

    const canvasContainer = canvasContainerRef.current;
    if (!canvasContainer) return undefined;

    const observer = new ResizeObserver(() => runtimeRef.current?.handleResize());
    observer.observe(canvasContainer);

    return () => observer.disconnect();
  }, [enabled, runtimeRef, canvasContainerRef]);
};

const useCompetitionVizKeyboardShortcuts = (runtimeRef, enabled) => {
  useEffect(() => {
    if (!enabled) return undefined;

    const doc = runtimeRef.current?.root?.ownerDocument || document;
    const handler = (event) => runtimeRef.current?.handleKeyDown(event);
    doc.addEventListener("keydown", handler);
    return () => doc.removeEventListener("keydown", handler);
  }, [enabled, runtimeRef]);
};

const useCompetitionVizScrollTracking = (runtimeRef, enabled) => {
  useEffect(() => {
    if (!enabled) return undefined;

    const handler = () => runtimeRef.current?.handleScroll();
    window.addEventListener("scroll", handler, { passive: true, capture: true });
    return () => window.removeEventListener("scroll", handler, { capture: true });
  }, [enabled, runtimeRef]);
};

const useCompetitionVizControls = (runtimeRef) => {
  const onCanvasMouseMove = useCallback(
    (event) => runtimeRef.current?.handleMouseMove(event),
    [runtimeRef]
  );
  const onCanvasMouseDown = useCallback(
    (event) => runtimeRef.current?.handleMouseDown(event),
    [runtimeRef]
  );
  const onCanvasMouseUp = useCallback(
    (event) => runtimeRef.current?.handleMouseUp(event),
    [runtimeRef]
  );
  const onCanvasMouseLeave = useCallback(
    (event) => runtimeRef.current?.handleMouseLeave(event),
    [runtimeRef]
  );
  const onStepClick = useCallback(() => runtimeRef.current?.handleStep(), [runtimeRef]);
  const onAutoClick = useCallback(() => runtimeRef.current?.handleAuto(), [runtimeRef]);
  const onResetClick = useCallback(() => runtimeRef.current?.handleReset(), [runtimeRef]);
  const onExportClick = useCallback(
    () => runtimeRef.current?.exportRankings(),
    [runtimeRef]
  );
  const onSpeedInput = useCallback(
    (event) => runtimeRef.current?.handleSpeed(event),
    [runtimeRef]
  );

  return {
    onCanvasMouseMove,
    onCanvasMouseDown,
    onCanvasMouseUp,
    onCanvasMouseLeave,
    onStepClick,
    onAutoClick,
    onResetClick,
    onExportClick,
    onSpeedInput,
  };
};

export const useCompetitionVizSimulation = (params) => {
  const { unsupported, ready, runtimeRef } = useCompetitionVizRuntime(params);

  useCompetitionVizCanvasResize(runtimeRef, params.canvasContainerRef, ready);
  useCompetitionVizAnimationLoop(runtimeRef, ready);
  useCompetitionVizKeyboardShortcuts(runtimeRef, ready);
  useCompetitionVizScrollTracking(runtimeRef, ready);

  const controls = useCompetitionVizControls(runtimeRef);
  return { unsupported, controls };
};

