import { useEffect, useRef } from "react";

const DEFAULT_SELECTOR = ".crackle";
const DEFAULT_COLOR = "#a78bfa";
const SVG_NS = "http://www.w3.org/2000/svg";
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

const exponentialInterval = (rate) => {
  const safeRate = Math.max(rate ?? 0, 0);
  if (safeRate === 0) return Infinity;
  const u = Math.random();
  return -Math.log(1 - u) / safeRate;
};

const createSparkPath = () => {
  const R = 47;
  const amp = 1.7 + Math.random() * 2.1;
  const segments = 5 + ((Math.random() * 3) | 0);
  const arc = ((8 + Math.random() * 18) * Math.PI) / 180;
  const startAngle = Math.random() * Math.PI * 2;

  const points = [];
  for (let i = 0; i <= segments; i++) {
    const t = i / segments;
    const angle = startAngle + (t - 0.5) * arc;
    const radiusVariation = (Math.random() * 2 - 1) * amp + (Math.random() < 0.5 ? -0.2 : 0.2);
    const radius = R + radiusVariation;
    points.push([50 + radius * Math.cos(angle), 50 + radius * Math.sin(angle)]);
  }

  let d = `M${points[0][0].toFixed(2)} ${points[0][1].toFixed(2)}`;
  for (let i = 1; i < points.length; i++) {
    d += `L${points[i][0].toFixed(2)} ${points[i][1].toFixed(2)}`;
  }

  if (Math.random() < 0.6) {
    const branchIndex = 1 + Math.floor(Math.random() * Math.max(points.length - 2, 1));
    const base = points[branchIndex];
    const t = branchIndex / segments;
    const branchAngle = startAngle + (t - 0.5) * arc + (Math.random() * 0.6 - 0.3);
    const branchRadius1 = R + amp * (0.6 + Math.random() * 0.8);
    const branchRadius2 = branchRadius1 + Math.random() * amp * 0.9;
    const angleOffset = Math.random() < 0.5 ? 0.8 : -0.8;
    const branchPoint1 = [50 + branchRadius1 * Math.cos(branchAngle), 50 + branchRadius1 * Math.sin(branchAngle)];
    const branchPoint2 = [
      50 + branchRadius2 * Math.cos(branchAngle + angleOffset),
      50 + branchRadius2 * Math.sin(branchAngle + angleOffset),
    ];
    d += `M${base[0].toFixed(2)} ${base[1].toFixed(2)} L${branchPoint1[0].toFixed(2)} ${branchPoint1[1].toFixed(2)} L${branchPoint2[0].toFixed(2)} ${branchPoint2[1].toFixed(2)}`;
  }

  return d;
};

const attachSparkLayer = ({
  element,
  color,
  rate,
  reducedMotion,
}) => {
  const state = {
    cancelled: false,
    timers: [],
    layer: null,
    svg: null,
    pool: [],
    rate,
  };

  const layer = document.createElement("span");
  layer.className = "crackle-layer";

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("preserveAspectRatio", "none");
  layer.appendChild(svg);
  element.appendChild(layer);

  state.layer = layer;
  state.svg = svg;

  if (reducedMotion || rate === 0) {
    state.cancelled = true;
    return state;
  }

  const pixelRatio = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
  const hairline = 1 / pixelRatio;
  const poolSize = 12;

  for (let i = 0; i < poolSize; i++) {
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("class", "spark");
    path.setAttribute("stroke", color);
    const strokeWidth = hairline * (0.9 + Math.random() * 0.2);
    path.setAttribute("stroke-width", strokeWidth.toFixed(3));
    svg.appendChild(path);
    state.pool.push({ el: path, busy: false });
  }

  const flashOne = () => {
    const slot = state.pool.find((candidate) => !candidate.busy);
    if (!slot) return;
    slot.busy = true;
    slot.el.setAttribute("d", createSparkPath());
    slot.el.classList.add("show");
    const lifetime = 50 + Math.random() * 120;
    const hideTimer = setTimeout(() => {
      slot.el.classList.remove("show");
      const releaseTimer = setTimeout(() => {
        slot.busy = false;
      }, 110);
      state.timers.push(releaseTimer);
    }, lifetime);
    state.timers.push(hideTimer);
  };

  const tick = () => {
    if (state.cancelled) return;
    const interval = exponentialInterval(state.rate || 1) * 1000;
    const timer = setTimeout(() => {
      if (state.cancelled) return;
      const burst = Math.random() < 0.25 ? 2 + (Math.random() < 0.35 ? 1 : 0) : 1;
      for (let i = 0; i < burst; i++) {
        const burstTimer = setTimeout(() => {
          if (!state.cancelled) flashOne();
        }, i * 22 + Math.random() * 18);
        state.timers.push(burstTimer);
      }
      tick();
    }, interval);
    state.timers.push(timer);
  };

  tick();
  return state;
};

const destroySparkState = (state) => {
  if (!state) return;
  state.cancelled = true;
  for (const timer of state.timers) clearTimeout(timer);
  if (state.layer?.parentNode) {
    try {
      state.layer.parentNode.removeChild(state.layer);
    } catch {
      /* no-op */
    }
  }
};

const getReducedMotionPreference = () => {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  try {
    return window.matchMedia(REDUCED_MOTION_QUERY).matches;
  } catch {
    return false;
  }
};

const resolveAttribute = (element, attr, fallback) => {
  const raw = element.getAttribute(attr);
  if (raw == null) return fallback;
  return raw;
};

const resolveRate = (element, attr, fallbackRate) => {
  const raw = element.getAttribute(attr);
  if (raw == null) return fallbackRate;
  const parsed = parseFloat(raw);
  if (!Number.isFinite(parsed) || parsed < 0) return fallbackRate;
  return parsed;
};

const useCrackleEffect = (rootRef, deps = [], options = {}) => {
  const {
    selector = DEFAULT_SELECTOR,
    colorAttr = "data-color",
    rateAttr = "data-rate",
    defaultColor = DEFAULT_COLOR,
  } = options;
  const statesRef = useRef(new Map());

  useEffect(() => {
    const root = rootRef?.current;
    if (!root) return undefined;

    const reducedMotion = getReducedMotionPreference();
    const states = statesRef.current;

    const cleanupNode = (element) => {
      const state = states.get(element);
      if (!state) return;
      destroySparkState(state);
      states.delete(element);
    };

    const initNode = (element) => {
      if (states.has(element)) return;
      const color = resolveAttribute(element, colorAttr, defaultColor).trim();
      const rate = resolveRate(element, rateAttr, 3);
      element.style.setProperty("--zap-color", color);
      const state = attachSparkLayer({
        element,
        color,
        rate,
        reducedMotion,
      });
      states.set(element, state);
    };

    const candidates = selector
      ? Array.from(root.querySelectorAll(selector))
      : [];
    candidates.forEach(initNode);

    for (const element of Array.from(states.keys())) {
      if (!root.contains(element) || (selector && !element.matches(selector))) {
        cleanupNode(element);
      }
    }

    return () => {
      for (const element of Array.from(states.keys())) {
        cleanupNode(element);
      }
      states.clear();
    };
  }, [rootRef, selector, colorAttr, rateAttr, defaultColor, ...deps]);
};

export default useCrackleEffect;
