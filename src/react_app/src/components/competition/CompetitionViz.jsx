import React, { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import "./CompetitionViz.css";

const SCENE_DATA = {
  nodes: [
    { id: 0, label: "P0 (Skill 0.22)" },
    { id: 1, label: "P1 (Skill 0.77)" },
    { id: 2, label: "P2 (Skill 0.80)" },
    { id: 3, label: "P3 (Skill 0.84)" },
    { id: 4, label: "P4 (Skill 0.87)" },
    { id: 5, label: "P5 (Skill 0.88)" },
    { id: 6, label: "P6 (Skill 0.89)" },
    { id: 7, label: "P7 (Skill 1.12)" },
    { id: 8, label: "P8 (Skill 1.26)" },
    { id: 9, label: "P9 (Skill 1.39)" },
    { id: 10, label: "P10 (Skill 1.93)" },
    { id: 11, label: "P11 (Skill 2.02)" },
    { id: 12, label: "P12 (Skill 3.20)" },
  ],
  links: [
    { source: 0, target: 1, weight: 1 },
    { source: 0, target: 4, weight: 1 },
    { source: 0, target: 5, weight: 1 },
    { source: 0, target: 6, weight: 1 },
    { source: 0, target: 7, weight: 1 },
    { source: 0, target: 8, weight: 1 },
    { source: 0, target: 9, weight: 1 },
    { source: 1, target: 0, weight: 4 },
    { source: 1, target: 2, weight: 2 },
    { source: 1, target: 3, weight: 3 },
    { source: 1, target: 4, weight: 1 },
    { source: 1, target: 5, weight: 2 },
    { source: 1, target: 7, weight: 4 },
    { source: 1, target: 8, weight: 1 },
    { source: 1, target: 9, weight: 2 },
    { source: 1, target: 10, weight: 2 },
    { source: 1, target: 12, weight: 1 },
    { source: 2, target: 0, weight: 5 },
    { source: 2, target: 1, weight: 1 },
    { source: 2, target: 3, weight: 1 },
    { source: 2, target: 4, weight: 3 },
    { source: 2, target: 5, weight: 3 },
    { source: 2, target: 6, weight: 4 },
    { source: 2, target: 7, weight: 4 },
    { source: 2, target: 8, weight: 1 },
    { source: 2, target: 9, weight: 3 },
    { source: 2, target: 10, weight: 1 },
    { source: 2, target: 12, weight: 2 },
    { source: 3, target: 0, weight: 1 },
    { source: 3, target: 1, weight: 3 },
    { source: 3, target: 2, weight: 3 },
    { source: 3, target: 4, weight: 1 },
    { source: 3, target: 5, weight: 1 },
    { source: 3, target: 6, weight: 4 },
    { source: 3, target: 7, weight: 4 },
    { source: 3, target: 8, weight: 3 },
    { source: 3, target: 9, weight: 3 },
    { source: 3, target: 10, weight: 2 },
    { source: 3, target: 11, weight: 2 },
    { source: 3, target: 12, weight: 2 },
    { source: 4, target: 0, weight: 2 },
    { source: 4, target: 1, weight: 3 },
    { source: 4, target: 2, weight: 5 },
    { source: 4, target: 3, weight: 2 },
    { source: 4, target: 5, weight: 1 },
    { source: 4, target: 6, weight: 4 },
    { source: 4, target: 7, weight: 5 },
    { source: 4, target: 9, weight: 1 },
    { source: 4, target: 10, weight: 3 },
    { source: 4, target: 11, weight: 1 },
    { source: 5, target: 0, weight: 4 },
    { source: 5, target: 1, weight: 5 },
    { source: 5, target: 2, weight: 2 },
    { source: 5, target: 4, weight: 1 },
    { source: 5, target: 6, weight: 1 },
    { source: 5, target: 7, weight: 3 },
    { source: 5, target: 8, weight: 4 },
    { source: 5, target: 9, weight: 2 },
    { source: 5, target: 10, weight: 2 },
    { source: 5, target: 11, weight: 4 },
    { source: 5, target: 12, weight: 1 },
    { source: 6, target: 0, weight: 2 },
    { source: 6, target: 1, weight: 1 },
    { source: 6, target: 3, weight: 4 },
    { source: 6, target: 4, weight: 1 },
    { source: 6, target: 5, weight: 4 },
    { source: 6, target: 7, weight: 1 },
    { source: 6, target: 8, weight: 2 },
    { source: 6, target: 9, weight: 4 },
    { source: 6, target: 10, weight: 1 },
    { source: 6, target: 11, weight: 2 },
    { source: 6, target: 12, weight: 1 },
    { source: 7, target: 0, weight: 7 },
    { source: 7, target: 1, weight: 2 },
    { source: 7, target: 2, weight: 2 },
    { source: 7, target: 4, weight: 2 },
    { source: 7, target: 5, weight: 2 },
    { source: 7, target: 6, weight: 4 },
    { source: 7, target: 8, weight: 3 },
    { source: 7, target: 9, weight: 4 },
    { source: 7, target: 10, weight: 1 },
    { source: 7, target: 11, weight: 4 },
    { source: 7, target: 12, weight: 2 },
    { source: 8, target: 2, weight: 1 },
    { source: 8, target: 3, weight: 4 },
    { source: 8, target: 4, weight: 4 },
    { source: 8, target: 5, weight: 2 },
    { source: 8, target: 6, weight: 5 },
    { source: 8, target: 7, weight: 2 },
    { source: 8, target: 9, weight: 2 },
    { source: 8, target: 10, weight: 5 },
    { source: 8, target: 11, weight: 1 },
    { source: 8, target: 12, weight: 2 },
    { source: 9, target: 0, weight: 2 },
    { source: 9, target: 1, weight: 7 },
    { source: 9, target: 2, weight: 3 },
    { source: 9, target: 3, weight: 5 },
    { source: 9, target: 4, weight: 4 },
    { source: 9, target: 5, weight: 4 },
    { source: 9, target: 7, weight: 2 },
    { source: 9, target: 8, weight: 4 },
    { source: 9, target: 10, weight: 1 },
    { source: 9, target: 12, weight: 2 },
    { source: 10, target: 0, weight: 2 },
    { source: 10, target: 1, weight: 6 },
    { source: 10, target: 2, weight: 4 },
    { source: 10, target: 3, weight: 4 },
    { source: 10, target: 4, weight: 5 },
    { source: 10, target: 5, weight: 6 },
    { source: 10, target: 6, weight: 4 },
    { source: 10, target: 7, weight: 3 },
    { source: 10, target: 9, weight: 4 },
    { source: 10, target: 11, weight: 5 },
    { source: 10, target: 12, weight: 4 },
    { source: 11, target: 0, weight: 4 },
    { source: 11, target: 1, weight: 3 },
    { source: 11, target: 2, weight: 8 },
    { source: 11, target: 3, weight: 6 },
    { source: 11, target: 4, weight: 9 },
    { source: 11, target: 5, weight: 5 },
    { source: 11, target: 6, weight: 5 },
    { source: 11, target: 8, weight: 10 },
    { source: 11, target: 9, weight: 3 },
    { source: 11, target: 10, weight: 4 },
    { source: 11, target: 12, weight: 5 },
    { source: 12, target: 0, weight: 3 },
    { source: 12, target: 1, weight: 4 },
    { source: 12, target: 2, weight: 6 },
    { source: 12, target: 3, weight: 5 },
    { source: 12, target: 4, weight: 4 },
    { source: 12, target: 5, weight: 5 },
    { source: 12, target: 6, weight: 4 },
    { source: 12, target: 7, weight: 5 },
    { source: 12, target: 8, weight: 7 },
    { source: 12, target: 9, weight: 7 },
    { source: 12, target: 10, weight: 7 },
    { source: 12, target: 11, weight: 14 },
  ],
};

const CompetitionViz = () => {
  const rootRef = useRef(null);
  const canvasRef = useRef(null);
  const canvasContainerRef = useRef(null);
  const scatterCanvasRef = useRef(null);
  const barCanvasRef = useRef(null);
  const convergenceCanvasRef = useRef(null);

  useEffect(() => {
    let animationFrameId = null;
    let autoRunTimeout = null;
    let resizeTimeout = null;
    let resizeObserver = null;
    let disposed = false;
    let stepInProgress = false;

    const root = rootRef.current;
    const canvas = canvasRef.current;
    const canvasContainer = canvasContainerRef.current;
    const scatterCanvas = scatterCanvasRef.current;
    const barCanvas = barCanvasRef.current;
    const convergenceCanvas = convergenceCanvasRef.current;
    let btnStep = null;
    let btnAuto = null;
    let btnReset = null;
    let btnExport = null;
    let speedSlider = null;
    let speedValue = null;
    let iterCount = null;
    let statusText = null;
    let deltaValue = null;
    let deltaBar = null;
    let insightText = null;
    let correlationValue = null;
    let nodeCount = null;
    let edgeCount = null;
    let dampingValue = null;
    let thresholdValue = null;
    let leaderName = null;
    let leaderScore = null;
    let leaderSkill = null;
    let leaderWins = null;
    let leaderOpp = null;

    const doc = (root?.ownerDocument || document);
    const previousTitle = doc.title;
    doc.title = "Ranking Simulator - splat.top";

    const baseCleanup = () => {
      disposed = true;
      doc.title = previousTitle;
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
      if (autoRunTimeout) clearTimeout(autoRunTimeout);
      if (resizeTimeout) clearTimeout(resizeTimeout);
      if (resizeObserver) resizeObserver.disconnect();
    };

    if (!root || !canvas || !canvasContainer || !scatterCanvas || !barCanvas || !convergenceCanvas) {
      return baseCleanup;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) return baseCleanup;

    btnStep = root.querySelector("#btnStep");
    btnAuto = root.querySelector("#btnAuto");
    btnReset = root.querySelector("#btnReset");
    btnExport = root.querySelector("#btnExport");
    speedSlider = root.querySelector("#speedSlider");
    speedValue = root.querySelector("#speedValue");
    iterCount = root.querySelector("#iterCount");
    statusText = root.querySelector("#statusText");
    deltaValue = root.querySelector("#deltaValue");
    deltaBar = root.querySelector("#deltaBar");
    insightText = root.querySelector("#insightText");
    correlationValue = root.querySelector("#correlationValue");
    nodeCount = root.querySelector("#nodeCount");
    edgeCount = root.querySelector("#edgeCount");
    dampingValue = root.querySelector("#dampingValue");
    thresholdValue = root.querySelector("#thresholdValue");
    leaderName = root.querySelector("#leaderName");
    leaderScore = root.querySelector("#leaderScore");
    leaderSkill = root.querySelector("#leaderSkill");
    leaderWins = root.querySelector("#leaderWins");
    leaderOpp = root.querySelector("#leaderOpp");

    if (
      !btnStep ||
      !btnAuto ||
      !btnReset ||
      !btnExport ||
      !speedSlider ||
      !speedValue ||
      !iterCount ||
      !statusText ||
      !deltaValue ||
      !deltaBar ||
      !insightText ||
      !correlationValue ||
      !nodeCount ||
      !edgeCount ||
      !dampingValue ||
      !thresholdValue ||
      !leaderName ||
      !leaderScore ||
      !leaderSkill ||
      !leaderWins ||
      !leaderOpp
    ) {
      return baseCleanup;
    }

    const CONFIG = {
      dampingFactor: 0.85,
      node: {
        baseRadius: 18,
        maxRadius: 52,
        radiusLerp: 0.1,
      },
      animation: {
        speed: 2.0,
        autoRunDelay: 450,
        particleBaseSpeed: 0.016,
      },
      physics: {
        hoverRadius: 56,
        curveAmount: 36,
        convergenceThreshold: 0.005,
      },
      colors: {
        edgeBase: "100, 116, 139",
        particle: "#38bdf8",
        text: "#f8fafc",
        highlightIn: "#34d399",
        highlightOut: "#fb7185",
      },
    };

    let width = 0;
    let height = 0;
    let nodes = [];
    let links = [];
    let particles = [];
    let iteration = 0;
    let isAnimating = false;
    let autoRun = false;
    let lastDelta = 0;
    let hoveredNode = null;
    let draggedNode = null;
    let mouseX = 0;
    let mouseY = 0;
    let chartsDirty = true;

    const convergenceHistory = [];
    const MAX_CONVERGENCE_HISTORY = 60;
    const particlePool = [];

    const resizeMainCanvas = () => {
      const ratio = window.devicePixelRatio || 1;
      const rect = canvasContainer.getBoundingClientRect();
      width = Math.max(1, Math.floor(rect.width));
      height = Math.max(320, Math.floor(rect.height));
      canvas.width = Math.max(1, Math.floor(width * ratio));
      canvas.height = Math.max(1, Math.floor(height * ratio));
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    };

    const resizeChartCanvas = (targetCanvas) => {
      const ratio = window.devicePixelRatio || 1;
      const rect = targetCanvas.getBoundingClientRect();
      const w = Math.max(1, rect.width);
      const h = Math.max(1, rect.height);
      targetCanvas.width = Math.max(1, Math.floor(w * ratio));
      targetCanvas.height = Math.max(1, Math.floor(h * ratio));
      const targetCtx = targetCanvas.getContext("2d");
      if (targetCtx) {
        targetCtx.setTransform(ratio, 0, 0, ratio, 0, 0);
      }
      return { ctx: targetCtx, width: w, height: h };
    };

    const calculateCorrelation = () => {
      const count = nodes.length;
      if (count === 0) return 0;

      const sumX = nodes.reduce((sum, node) => sum + node.trueSkill, 0);
      const sumY = nodes.reduce((sum, node) => sum + node.rank, 0);
      const sumXY = nodes.reduce((sum, node) => sum + node.trueSkill * node.rank, 0);
      const sumX2 = nodes.reduce((sum, node) => sum + node.trueSkill ** 2, 0);
      const sumY2 = nodes.reduce((sum, node) => sum + node.rank ** 2, 0);

      const num = count * sumXY - sumX * sumY;
      const den = Math.sqrt((count * sumX2 - sumX ** 2) * (count * sumY2 - sumY ** 2));
      return den === 0 ? 0 : num / den;
    };

    const getRadiusFromRank = (rank) => {
      const scaled = CONFIG.node.baseRadius * Math.sqrt(rank);
      return Math.max(12, Math.min(CONFIG.node.maxRadius, scaled));
    };

    const getParticle = (link, value) => {
      let particle = particlePool.pop();
      if (!particle) {
        particle = new Particle(link, value);
      } else {
        particle.link = link;
        particle.value = value;
        particle.progress = 0;
        particle.active = true;
        particle.speed = CONFIG.animation.particleBaseSpeed * CONFIG.animation.speed;
        particle.radius = Math.max(2, Math.min(6, 3 * Math.sqrt(value)));
      }
      return particle;
    };

    const releaseParticle = (particle) => {
      particlePool.push(particle);
    };

    const exportRankings = () => {
      const sorted = [...nodes].sort((a, b) => b.rank - a.rank);
      const csv =
        "Rank,Player,Score,TrueSkill,TotalWins,AvgOpponentSkill\n" +
        sorted
          .map(
            (node, index) =>
              `${index + 1},${node.label.replace(",", ";")},${node.rank.toFixed(6)},${node.trueSkill},${node.totalWins},${node.avgOpponentSkill.toFixed(3)}`
          )
          .join("\n");

      const blob = new Blob([csv], { type: "text/csv" });
      const link = doc.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `pagerank_iter${iteration}.csv`;
      doc.body.appendChild(link);
      link.click();
      doc.body.removeChild(link);
      URL.revokeObjectURL(link.href);
    };

    class Node {
      constructor(id, x, y, label) {
        this.id = id;
        this.x = x;
        this.y = y;
        this.label = label || id;

        const match = this.label.match(/Skill ([\d.]+)/);
        this.trueSkill = match ? parseFloat(match[1]) : 0;

        this.rank = 1;
        this.nextRank = 1;

        this.displayRadius = CONFIG.node.baseRadius;
        this.targetRadius = CONFIG.node.baseRadius;
        this.pulse = 0;

        this.totalRawWins = 0;
        this.totalWins = 0;
        this.avgOpponentSkill = 0;
      }

      update() {
        this.displayRadius += (this.targetRadius - this.displayRadius) * CONFIG.node.radiusLerp;
        if (this.rank > 2) {
          this.pulse += 0.05;
        }
      }

      draw(context, isDimmed) {
        const heat = Math.min(1, (this.rank - 0.5) / 3);
        context.beginPath();
        context.fillStyle = this.getHeatColor(heat);

        if (!isDimmed) {
          const glow = Math.sin(this.pulse) * 3;
          context.shadowBlur = 18 + glow;
          context.shadowColor = context.fillStyle;
        } else {
          context.shadowBlur = 0;
        }

        context.arc(this.x, this.y, this.displayRadius, 0, Math.PI * 2);
        context.fill();
        context.shadowBlur = 0;

        context.fillStyle = CONFIG.colors.text;
        context.font = '600 12px "FiraMono", ui-monospace, SFMono-Regular, monospace';
        context.textAlign = "center";
        context.textBaseline = "middle";
        context.fillText(this.rank.toFixed(2), this.x, this.y);

        context.fillStyle = "#cbd5f5";
        context.font = "10px ui-sans-serif, system-ui, sans-serif";
        const shortName = this.label.split(" ")[0];
        context.fillText(shortName, this.x, this.y + this.displayRadius + 18);
      }

      getHeatColor(t) {
        const r1 = 124;
        const g1 = 58;
        const b1 = 237;
        const r2 = 217;
        const g2 = 70;
        const b2 = 239;

        const r = Math.round(r1 + (r2 - r1) * t);
        const g = Math.round(g1 + (g2 - g1) * t);
        const b = Math.round(b1 + (b2 - b1) * t);

        return `rgb(${r},${g},${b})`;
      }
    }

    class Link {
      constructor(source, target, weight = 1) {
        this.source = source;
        this.target = target;
        this.weight = weight;
        this.isBidirectional = false;
      }

      draw(context, highlightMode) {
        const dx = this.target.x - this.source.x;
        const dy = this.target.y - this.source.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        const sourceOffset = this.source.displayRadius;
        const targetOffset = this.target.displayRadius + 6;

        if (dist < sourceOffset + targetOffset) return;

        let strokeStyle = null;
        let lineWidth = 1;
        const isHovered = highlightMode === "incoming" || highlightMode === "outgoing";
        const useCurve = isHovered && this.isBidirectional;

        if (highlightMode === "incoming") {
          strokeStyle = CONFIG.colors.highlightIn;
          lineWidth = Math.min(3.5, 1.4 + this.weight * 0.3);
        } else if (highlightMode === "outgoing") {
          strokeStyle = CONFIG.colors.highlightOut;
          lineWidth = Math.min(3.5, 1.4 + this.weight * 0.3);
        } else if (highlightMode === "dimmed") {
          strokeStyle = `rgba(${CONFIG.colors.edgeBase}, 0.05)`;
          lineWidth = 1;
        } else {
          const alpha = Math.min(0.8, 0.12 + this.weight / 16);
          strokeStyle = `rgba(${CONFIG.colors.edgeBase}, ${alpha})`;
          lineWidth = Math.min(5.5, 1 + this.weight * 0.35);
        }

        context.beginPath();
        context.strokeStyle = strokeStyle;
        context.lineWidth = lineWidth;

        let endX;
        let endY;
        let angle;

        if (useCurve) {
          const mx = (this.source.x + this.target.x) / 2;
          const my = (this.source.y + this.target.y) / 2;

          const nx = -dy / dist;
          const ny = dx / dist;

          const cpx = mx + nx * CONFIG.physics.curveAmount;
          const cpy = my + ny * CONFIG.physics.curveAmount;

          const dsx = cpx - this.source.x;
          const dsy = cpy - this.source.y;
          const lenS = Math.sqrt(dsx * dsx + dsy * dsy);

          const startXCurve = this.source.x + (dsx / lenS) * sourceOffset;
          const startYCurve = this.source.y + (dsy / lenS) * sourceOffset;

          const dtx = cpx - this.target.x;
          const dty = cpy - this.target.y;
          const lenT = Math.sqrt(dtx * dtx + dty * dty);

          endX = this.target.x + (dtx / lenT) * targetOffset;
          endY = this.target.y + (dty / lenT) * targetOffset;

          context.moveTo(startXCurve, startYCurve);
          context.quadraticCurveTo(cpx, cpy, endX, endY);

          angle = Math.atan2(endY - cpy, endX - cpx);
        } else {
          const startX = this.source.x + (dx / dist) * sourceOffset;
          const startY = this.source.y + (dy / dist) * sourceOffset;
          endX = this.target.x - (dx / dist) * targetOffset;
          endY = this.target.y - (dy / dist) * targetOffset;

          context.moveTo(startX, startY);
          context.lineTo(endX, endY);
          angle = Math.atan2(dy, dx);
        }

        context.stroke();

        const arrowSize = Math.min(7.5, 3 + lineWidth * 0.6);
        context.save();
        context.translate(endX, endY);
        context.rotate(angle);
        context.beginPath();
        context.moveTo(0, 0);
        context.lineTo(-arrowSize, -arrowSize * 0.5);
        context.lineTo(-arrowSize, arrowSize * 0.5);
        context.closePath();
        context.fillStyle = strokeStyle;
        context.fill();
        context.restore();
      }
    }

    class Particle {
      constructor(link, value) {
        this.link = link;
        this.value = value;
        this.progress = 0;
        this.speed = CONFIG.animation.particleBaseSpeed * CONFIG.animation.speed;
        this.radius = Math.max(2, Math.min(6, 3 * Math.sqrt(value)));
        this.active = true;
      }

      update() {
        this.progress += this.speed;
        if (this.progress >= 1) {
          this.progress = 1;
          this.active = false;
          return true;
        }
        return false;
      }

      draw(context) {
        if (!this.active) return;

        const sx = this.link.source.x;
        const sy = this.link.source.y;
        const tx = this.link.target.x;
        const ty = this.link.target.y;

        const x = sx + (tx - sx) * this.progress;
        const y = sy + (ty - sy) * this.progress;

        context.beginPath();
        context.fillStyle = CONFIG.colors.particle;
        context.shadowBlur = 8;
        context.shadowColor = CONFIG.colors.particle;
        context.arc(x, y, this.radius, 0, Math.PI * 2);
        context.fill();
        context.shadowBlur = 0;
      }
    }

    const init = () => {
      nodes = [];
      links = [];
      particles = [];
      iteration = 0;
      lastDelta = 0;
      isAnimating = false;
      stepInProgress = false;
      convergenceHistory.length = 0;
      stopAutoRun();

      const cx = width / 2;
      const cy = height * 0.5;

      const count = SCENE_DATA.nodes.length;
      SCENE_DATA.nodes.forEach((dataNode, index) => {
        const angle = (index / count) * Math.PI * 2 - Math.PI / 2;
        const radius = Math.min(width, height) * 0.3;
        const x = cx + Math.cos(angle) * radius;
        const y = cy + Math.sin(angle) * radius;
        nodes.push(new Node(dataNode.id, x, y, dataNode.label));
      });

      SCENE_DATA.links.forEach((dataLink) => {
        const sourceNode = nodes.find((node) => node.id === dataLink.source);
        const targetNode = nodes.find((node) => node.id === dataLink.target);

        if (sourceNode && targetNode) {
          const link = new Link(targetNode, sourceNode, dataLink.weight);
          links.push(link);
          targetNode.totalRawWins += dataLink.weight;
        }
      });

      nodes.forEach((node) => {
        const winsAgainst = links.filter((link) => link.target === node);
        node.totalWins = winsAgainst.reduce((sum, link) => sum + link.weight, 0);

        if (node.totalWins > 0) {
          let weightedSkillSum = 0;
          winsAgainst.forEach((link) => {
            weightedSkillSum += link.source.trueSkill * link.weight;
          });
          node.avgOpponentSkill = weightedSkillSum / node.totalWins;
        } else {
          node.avgOpponentSkill = 0;
        }
      });

      links.forEach((link) => {
        const reverse = links.find(
          (candidate) => candidate.source === link.target && candidate.target === link.source
        );
        if (reverse) {
          link.isBidirectional = true;
        }
      });

      nodes.forEach((node) => {
        node.rank = 1.0;
        node.targetRadius = getRadiusFromRank(node.rank);
        node.displayRadius = node.targetRadius;
      });

      nodeCount.textContent = nodes.length;
      edgeCount.textContent = links.length;
      dampingValue.textContent = CONFIG.dampingFactor.toFixed(2);
      thresholdValue.textContent = CONFIG.physics.convergenceThreshold.toFixed(3);

      chartsDirty = true;
      updateUI();
    };

    const calculateNextStep = () => {
      const count = nodes.length;
      const damping = CONFIG.dampingFactor;
      const baseRank = 1 - damping;

      nodes.forEach((node) => {
        node.nextRank = baseRank;
      });
      particles = [];

      nodes.forEach((source) => {
        const outboundLinks = links.filter((link) => link.source === source);
        if (outboundLinks.length > 0) {
          const totalWeight = outboundLinks.reduce((sum, link) => sum + link.weight, 0);
          outboundLinks.forEach((link) => {
            const share = link.weight / totalWeight;
            const passValue = source.rank * damping * share;
            link.target.nextRank += passValue;
            particles.push(getParticle(link, passValue));
          });
        } else {
          const distributeToAll = (source.rank * damping) / count;
          nodes.forEach((target) => {
            target.nextRank += distributeToAll;
          });
        }
      });
    };

    const finishStep = () => {
      let totalDelta = 0;

      nodes.forEach((node) => {
        totalDelta += Math.abs(node.nextRank - node.rank);
        node.rank = node.nextRank;
        node.targetRadius = getRadiusFromRank(node.rank);
      });

      particles.forEach((particle) => releaseParticle(particle));
      particles = [];

      iteration += 1;
      lastDelta = totalDelta;

      convergenceHistory.push({ iteration, delta: totalDelta });
      if (convergenceHistory.length > MAX_CONVERGENCE_HISTORY) {
        convergenceHistory.shift();
      }

      chartsDirty = true;
      isAnimating = false;
      stepInProgress = false;
      btnStep.disabled = false;

      if (totalDelta < CONFIG.physics.convergenceThreshold) {
        stopAutoRun();
        statusText.textContent = "Stable";
        statusText.className =
          "text-[11px] font-semibold text-amber-300 bg-amber-500/15 px-2.5 py-1 rounded-full border border-amber-500/25";
        updateUI();
        return;
      }

      statusText.textContent = "Ready";
      statusText.className =
        "text-[11px] font-semibold text-emerald-300 bg-emerald-500/15 px-2.5 py-1 rounded-full border border-emerald-500/25";

      updateUI();

      if (autoRun) {
        autoRunTimeout = window.setTimeout(() => {
          if (autoRun) performStep();
        }, CONFIG.animation.autoRunDelay);
      }
    };

    const performStep = () => {
      if (stepInProgress || isAnimating) return;
      stepInProgress = true;
      calculateNextStep();
      isAnimating = true;

      statusText.textContent = "Computing";
      statusText.className =
        "text-[11px] font-semibold text-cyan-200 bg-cyan-500/15 px-2.5 py-1 rounded-full border border-cyan-500/25";

      btnStep.disabled = true;
    };

    const drawTooltip = (context, node) => {
      if (!node) return;

      const padding = 10;
      let boxX = node.x + node.displayRadius + 16;
      let boxY = node.y - 62;
      const boxWidth = 180;
      const boxHeight = 112;

      if (boxX + boxWidth > width - 20) {
        boxX = node.x - node.displayRadius - boxWidth - 16;
      }
      if (boxY < 20) {
        boxY = 20;
      }
      if (boxY + boxHeight > height - 20) {
        boxY = height - boxHeight - 20;
      }

      context.fillStyle = "rgba(15, 23, 42, 0.96)";
      context.strokeStyle = "rgba(217, 70, 239, 0.65)";
      context.lineWidth = 1;
      context.beginPath();

      if (typeof context.roundRect === "function") {
        context.roundRect(boxX, boxY, boxWidth, boxHeight, 10);
      } else {
        context.rect(boxX, boxY, boxWidth, boxHeight);
      }

      context.fill();
      context.stroke();

      context.fillStyle = "#f8fafc";
      context.textAlign = "left";
      context.textBaseline = "top";
      context.font = "600 12px ui-sans-serif, system-ui, sans-serif";
      context.fillText(node.label.split(" ")[0], boxX + padding, boxY + padding);

      context.font = "11px ui-sans-serif, system-ui, sans-serif";
      context.fillStyle = "#94a3b8";

      context.fillText(`Score: ${node.rank.toFixed(3)}`, boxX + padding, boxY + padding + 20);
      context.fillText(`True Skill: ${node.trueSkill}`, boxX + padding, boxY + padding + 36);
      context.fillText(`Total Wins: ${node.totalWins}`, boxX + padding, boxY + padding + 52);

      context.fillText("Avg Opp Skill:", boxX + padding, boxY + padding + 68);
      context.fillStyle = node.avgOpponentSkill > 1.2
        ? "#34d399"
        : node.avgOpponentSkill < 0.8
        ? "#fb7185"
        : "#fbbf24";
      context.fillText(node.avgOpponentSkill.toFixed(2), boxX + padding + 86, boxY + padding + 68);

      context.fillStyle = CONFIG.colors.highlightIn;
      context.fillText("Wins", boxX + padding, boxY + padding + 88);
      context.fillStyle = CONFIG.colors.highlightOut;
      context.fillText("Losses", boxX + padding + 62, boxY + padding + 88);
    };

    const drawBarChart = () => {
      const { ctx: chartCtx, width: chartW, height: chartH } = resizeChartCanvas(barCanvas);
      if (!chartCtx) return;

      chartCtx.clearRect(0, 0, chartW, chartH);

      const sortedNodes = [...nodes].sort((a, b) => b.rank - a.rank).slice(0, 12);
      const maxRank = Math.max(sortedNodes[0]?.rank || 1, 0.1) * 1.1;
      const padding = 8;
      const barWidth = chartW / sortedNodes.length - padding;

      sortedNodes.forEach((node, index) => {
        const barHeight = (node.rank / maxRank) * (chartH - 28);
        const x = index * (barWidth + padding) + padding / 2;
        const y = chartH - barHeight - 16;
        const heat = Math.min(1, (node.rank - 0.5) / 3);

        chartCtx.fillStyle = node.getHeatColor(heat);
        chartCtx.fillRect(x, y, barWidth, barHeight);

        chartCtx.fillStyle = "#94a3b8";
        chartCtx.font = "9px ui-sans-serif, system-ui, sans-serif";
        chartCtx.textAlign = "center";
        const shortLabel = node.label.split(" ")[0];
        chartCtx.fillText(shortLabel, x + barWidth / 2, chartH - 4);
      });
    };

    const drawScatterChart = () => {
      const { ctx: chartCtx, width: chartW, height: chartH } = resizeChartCanvas(scatterCanvas);
      if (!chartCtx) return;

      const marginLeft = 30;
      const marginBottom = 22;
      const marginTop = 10;
      const marginRight = 16;
      const plotW = chartW - marginLeft - marginRight;
      const plotH = chartH - marginBottom - marginTop;
      const maxSkill = 3.5;

      let currentMaxRank = 0;
      nodes.forEach((node) => {
        if (node.rank > currentMaxRank) currentMaxRank = node.rank;
      });
      const maxRank = Math.max(currentMaxRank, 1.0) * 1.1;

      chartCtx.clearRect(0, 0, chartW, chartH);

      chartCtx.strokeStyle = "#334155";
      chartCtx.lineWidth = 1;
      chartCtx.beginPath();
      chartCtx.moveTo(marginLeft, marginTop);
      chartCtx.lineTo(marginLeft, chartH - marginBottom);
      chartCtx.lineTo(chartW - marginRight, chartH - marginBottom);
      chartCtx.stroke();

      chartCtx.fillStyle = "#94a3b8";
      chartCtx.font = "9px ui-sans-serif, system-ui, sans-serif";
      chartCtx.textAlign = "center";
      chartCtx.textBaseline = "top";
      for (let i = 0; i <= 3; i += 1) {
        const x = marginLeft + (i / maxSkill) * plotW;
        const y = chartH - marginBottom;
        chartCtx.beginPath();
        chartCtx.moveTo(x, y);
        chartCtx.lineTo(x, y + 4);
        chartCtx.stroke();
        chartCtx.fillText(i, x, y + 6);
      }

      chartCtx.textAlign = "right";
      chartCtx.textBaseline = "middle";
      chartCtx.fillText("0", marginLeft - 6, chartH - marginBottom);
      chartCtx.fillText(maxRank.toFixed(1), marginLeft - 6, marginTop);
      chartCtx.beginPath();
      chartCtx.moveTo(marginLeft, marginTop);
      chartCtx.lineTo(marginLeft - 4, marginTop);
      chartCtx.stroke();

      if (nodes.length > 1) {
        const count = nodes.length;
        const sumX = nodes.reduce((sum, node) => sum + node.trueSkill, 0);
        const sumY = nodes.reduce((sum, node) => sum + node.rank, 0);
        const sumXY = nodes.reduce((sum, node) => sum + node.trueSkill * node.rank, 0);
        const sumX2 = nodes.reduce((sum, node) => sum + node.trueSkill ** 2, 0);

        const slope = (count * sumXY - sumX * sumY) / (count * sumX2 - sumX ** 2);
        const intercept = (sumY - slope * sumX) / count;

        chartCtx.strokeStyle = "rgba(217, 70, 239, 0.35)";
        chartCtx.lineWidth = 1;
        chartCtx.setLineDash([4, 4]);
        chartCtx.beginPath();

        const x1 = marginLeft;
        const y1 = (chartH - marginBottom) - (intercept / maxRank) * plotH;
        const x2 = chartW - marginRight;
        const y2 = (chartH - marginBottom) - ((slope * maxSkill + intercept) / maxRank) * plotH;

        chartCtx.moveTo(x1, Math.max(marginTop, Math.min(chartH - marginBottom, y1)));
        chartCtx.lineTo(x2, Math.max(marginTop, Math.min(chartH - marginBottom, y2)));
        chartCtx.stroke();
        chartCtx.setLineDash([]);
      }

      nodes.forEach((node) => {
        const x = marginLeft + (node.trueSkill / maxSkill) * plotW;
        const y = (chartH - marginBottom) - (node.rank / maxRank) * plotH;
        const heat = Math.min(1, (node.rank - 0.5) / 3);
        chartCtx.fillStyle = node.getHeatColor(heat);
        chartCtx.beginPath();
        chartCtx.arc(x, y, 5, 0, Math.PI * 2);
        chartCtx.fill();

        chartCtx.strokeStyle = "rgba(255, 255, 255, 0.35)";
        chartCtx.lineWidth = 1;
        chartCtx.stroke();
      });

      const correlation = calculateCorrelation();
      correlationValue.textContent = `r = ${correlation.toFixed(3)}`;
    };

    const generateInsight = () => {
      if (iteration === 0) {
        insightText.innerHTML =
          'Tap <strong class="text-white">Step</strong> or <strong class="text-white">Auto Run</strong> to begin. Watch influence flow from losers to winners.';
        return;
      }

      const byScore = [...nodes].sort((a, b) => b.rank - a.rank);
      const bySkill = [...nodes].sort((a, b) => b.trueSkill - a.trueSkill);
      const byWins = [...nodes].sort((a, b) => b.totalWins - a.totalWins);

      const scorePosition = new Map(byScore.map((node, index) => [node.id, index + 1]));
      const winsPosition = new Map(byWins.map((node, index) => [node.id, index + 1]));

      const top = byScore[0];
      const topSkill = bySkill[0];

      if (lastDelta < CONFIG.physics.convergenceThreshold) {
        if (top === topSkill) {
          insightText.innerHTML = `<strong class="text-amber-300">Converged.</strong> <strong class="text-emerald-300">${top.label.split(" ")[0]}</strong> matches the highest skill player.`;
        } else {
          const topSkillScorePos = scorePosition.get(topSkill.id);
          insightText.innerHTML = `<strong class="text-amber-300">Converged.</strong> <strong class="text-white">${top.label.split(" ")[0]}</strong> leads. The highest-skill player (${topSkill.label.split(" ")[0]}) is #${topSkillScorePos}.`;
        }
        return;
      }

      if (iteration <= 3) {
        insightText.innerHTML = `<strong class="text-cyan-300">Iteration ${iteration}:</strong> scores are redistributing. Beating strong opponents carries more weight.`;
        return;
      }

      let biggestRiser = null;
      let biggestFaller = null;
      let maxRise = 0;
      let maxFall = 0;

      nodes.forEach((node) => {
        const winsPos = winsPosition.get(node.id);
        const scorePos = scorePosition.get(node.id);
        const diff = winsPos - scorePos;

        if (diff > maxRise) {
          maxRise = diff;
          biggestRiser = node;
        }
        if (diff < maxFall) {
          maxFall = diff;
          biggestFaller = node;
        }
      });

      if (maxRise >= 2 && biggestRiser) {
        const winsPos = winsPosition.get(biggestRiser.id);
        const scorePos = scorePosition.get(biggestRiser.id);
        insightText.innerHTML = `<strong class="text-cyan-300">${biggestRiser.label.split(" ")[0]}</strong> jumped from #${winsPos} (wins) to <strong class="text-emerald-300">#${scorePos}</strong> (score) on quality opponents.`;
        return;
      }

      if (maxFall <= -2 && biggestFaller) {
        const winsPos = winsPosition.get(biggestFaller.id);
        const scorePos = scorePosition.get(biggestFaller.id);
        insightText.innerHTML = `<strong class="text-rose-300">${biggestFaller.label.split(" ")[0]}</strong> slid from #${winsPos} (wins) to <strong class="text-rose-300">#${scorePos}</strong> (score) with weaker matchups.`;
        return;
      }

      const topAvgOpp = top.avgOpponentSkill.toFixed(2);
      insightText.innerHTML = `<strong class="text-white">${top.label.split(" ")[0]}</strong> leads with ${top.totalWins} wins and avg opponent skill ${topAvgOpp}.`;
    };

    const drawConvergenceChart = () => {
      const { ctx: chartCtx, width: chartW, height: chartH } = resizeChartCanvas(convergenceCanvas);
      if (!chartCtx) return;

      chartCtx.clearRect(0, 0, chartW, chartH);

      if (convergenceHistory.length < 2) {
        chartCtx.fillStyle = "#64748b";
        chartCtx.font = "10px ui-sans-serif, system-ui, sans-serif";
        chartCtx.textAlign = "center";
        chartCtx.fillText("Run the model to see convergence", chartW / 2, chartH / 2);
        return;
      }

      const maxDelta = Math.max(...convergenceHistory.map((point) => point.delta), 0.1);
      const padding = 6;

      const thresholdY =
        chartH -
        padding -
        (CONFIG.physics.convergenceThreshold / maxDelta) * (chartH - padding * 2);

      chartCtx.strokeStyle = "rgba(251, 191, 36, 0.3)";
      chartCtx.lineWidth = 1;
      chartCtx.setLineDash([3, 3]);
      chartCtx.beginPath();
      chartCtx.moveTo(padding, thresholdY);
      chartCtx.lineTo(chartW - padding, thresholdY);
      chartCtx.stroke();
      chartCtx.setLineDash([]);

      chartCtx.strokeStyle = "#d946ef";
      chartCtx.lineWidth = 2;
      chartCtx.beginPath();

      convergenceHistory.forEach((point, index) => {
        const x =
          padding +
          (index / (convergenceHistory.length - 1)) * (chartW - padding * 2);
        const y =
          chartH -
          padding -
          (point.delta / maxDelta) * (chartH - padding * 2);

        if (index === 0) {
          chartCtx.moveTo(x, y);
        } else {
          chartCtx.lineTo(x, y);
        }
      });

      chartCtx.stroke();

      const gradient = chartCtx.createLinearGradient(0, 0, 0, chartH);
      gradient.addColorStop(0, "rgba(217, 70, 239, 0.35)");
      gradient.addColorStop(1, "rgba(217, 70, 239, 0)");

      chartCtx.fillStyle = gradient;
      chartCtx.lineTo(chartW - padding, chartH - padding);
      chartCtx.lineTo(padding, chartH - padding);
      chartCtx.closePath();
      chartCtx.fill();
    };

    const updateLeaderPanel = () => {
      const [leader] = [...nodes].sort((a, b) => b.rank - a.rank);
      if (!leader) return;

      leaderName.textContent = leader.label.split(" ")[0];
      leaderScore.textContent = leader.rank.toFixed(3);
      leaderSkill.textContent = leader.trueSkill.toFixed(2);
      leaderWins.textContent = leader.totalWins;
      leaderOpp.textContent = leader.avgOpponentSkill.toFixed(2);

      const oppClass =
        leader.avgOpponentSkill > 1.2
          ? "text-emerald-300"
          : leader.avgOpponentSkill < 0.8
          ? "text-rose-300"
          : "text-amber-300";
      leaderOpp.className = `font-data ${oppClass}`;
    };

    const animate = () => {
      if (disposed) return;

      ctx.clearRect(0, 0, width, height);
      nodes.forEach((node) => node.update());

      if (hoveredNode) {
        ctx.globalAlpha = 0.1;
        links.forEach((link) => link.draw(ctx, "dimmed"));
        nodes.forEach((node) => {
          if (node !== hoveredNode) node.draw(ctx, true);
        });

        ctx.globalAlpha = 1.0;
        links.forEach((link) => {
          if (link.target === hoveredNode) {
            link.draw(ctx, "incoming");
          } else if (link.source === hoveredNode) {
            link.draw(ctx, "outgoing");
          }
        });

        const neighbors = new Set();
        links.forEach((link) => {
          if (link.target === hoveredNode) neighbors.add(link.source);
          if (link.source === hoveredNode) neighbors.add(link.target);
        });

        nodes.forEach((node) => {
          if (neighbors.has(node)) node.draw(ctx, false);
        });
        hoveredNode.draw(ctx, false);
        drawTooltip(ctx, hoveredNode);
      } else {
        ctx.globalAlpha = 1.0;
        links.forEach((link) => link.draw(ctx, "none"));
        nodes.forEach((node) => node.draw(ctx, false));
      }

      if (isAnimating) {
        let allArrived = true;
        particles.forEach((particle) => {
          const arrived = particle.update();
          particle.draw(ctx);
          if (!arrived) allArrived = false;
        });

        if (allArrived && particles.length > 0) {
          finishStep();
        } else if (particles.length === 0 && isAnimating) {
          finishStep();
        }
      }

      if (chartsDirty) {
        drawBarChart();
        drawScatterChart();
        drawConvergenceChart();
        generateInsight();
        updateLeaderPanel();
        chartsDirty = false;
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    const stopAutoRun = () => {
      autoRun = false;
      btnAuto.textContent = "Auto";
      btnAuto.classList.remove("is-active");
      if (autoRunTimeout) {
        clearTimeout(autoRunTimeout);
        autoRunTimeout = null;
      }
    };

    const updateUI = () => {
      iterCount.textContent = iteration;

      if (iteration === 0) {
        deltaValue.textContent = "-";
        deltaBar.style.width = "100%";
      } else {
        deltaValue.textContent = lastDelta.toFixed(4);
        const logDelta = Math.log10(lastDelta + 0.0001);
        const logMax = Math.log10(5);
        const logMin = Math.log10(CONFIG.physics.convergenceThreshold);
        const percent = Math.max(
          0,
          Math.min(100, ((logDelta - logMin) / (logMax - logMin)) * 100)
        );
        deltaBar.style.width = `${percent}%`;
      }

      chartsDirty = true;
    };

    const handleMouseMove = (event) => {
      const rect = canvas.getBoundingClientRect();
      mouseX = event.clientX - rect.left;
      mouseY = event.clientY - rect.top;

      if (draggedNode) {
        draggedNode.x = mouseX;
        draggedNode.y = mouseY;
        return;
      }

      let closest = null;
      let minDist = CONFIG.physics.hoverRadius;

      nodes.forEach((node) => {
        const dx = mouseX - node.x;
        const dy = mouseY - node.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < minDist) {
          minDist = dist;
          closest = node;
        }
      });

      hoveredNode = closest;
      canvas.style.cursor = hoveredNode ? "grab" : "default";
    };

    const handleMouseDown = () => {
      if (hoveredNode) {
        draggedNode = hoveredNode;
        canvas.style.cursor = "grabbing";
      }
    };

    const handleMouseUp = () => {
      draggedNode = null;
      canvas.style.cursor = hoveredNode ? "grab" : "default";
    };

    const handleMouseLeave = () => {
      draggedNode = null;
      hoveredNode = null;
      canvas.style.cursor = "default";
    };

    const handleKeyDown = (event) => {
      if (event.target.tagName === "INPUT") return;

      switch (event.key.toLowerCase()) {
        case " ":
        case "s":
          event.preventDefault();
          stopAutoRun();
          performStep();
          break;
        case "a":
          event.preventDefault();
          btnAuto.click();
          break;
        case "r":
          event.preventDefault();
          btnReset.click();
          break;
        case "e":
          event.preventDefault();
          exportRankings();
          break;
        default:
          break;
      }
    };

    const handleResize = () => {
      if (resizeTimeout) clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        resizeMainCanvas();
        init();
      }, 150);
    };

    const handleReset = () => {
      if (iteration === 0) {
        init();
        return;
      }

      nodes.forEach((node) => {
        node.rank = 1;
        node.nextRank = 1;
        node.targetRadius = getRadiusFromRank(1);
      });
      iteration = 0;
      lastDelta = 0;
      convergenceHistory.length = 0;
      stopAutoRun();

      statusText.textContent = "Ready";
      statusText.className =
        "text-[11px] font-semibold text-emerald-300 bg-emerald-500/15 px-2.5 py-1 rounded-full border border-emerald-500/25";

      chartsDirty = true;
      updateUI();
      generateInsight();
    };

    const handleAuto = () => {
      if (autoRun) {
        stopAutoRun();
      } else {
        autoRun = true;
        btnAuto.textContent = "Stop";
        btnAuto.classList.add("is-active");
        performStep();
      }
    };

    const handleStep = () => {
      stopAutoRun();
      performStep();
    };

    const handleSpeed = (event) => {
      CONFIG.animation.speed = parseFloat(event.target.value);
      speedValue.textContent = `${CONFIG.animation.speed}x`;
    };

    resizeMainCanvas();
    init();
    animate();

    canvas.addEventListener("mousemove", handleMouseMove);
    canvas.addEventListener("mousedown", handleMouseDown);
    canvas.addEventListener("mouseup", handleMouseUp);
    canvas.addEventListener("mouseleave", handleMouseLeave);
    btnStep.addEventListener("click", handleStep);
    btnReset.addEventListener("click", handleReset);
    btnAuto.addEventListener("click", handleAuto);
    btnExport.addEventListener("click", exportRankings);
    speedSlider.addEventListener("input", handleSpeed);
    resizeObserver = typeof ResizeObserver !== "undefined"
      ? new ResizeObserver(() => handleResize())
      : null;
    if (resizeObserver) {
      resizeObserver.observe(canvasContainer);
    }
    window.addEventListener("resize", handleResize);
    doc.addEventListener("keydown", handleKeyDown);

    const cleanup = () => {
      baseCleanup();
      if (canvas) {
        canvas.removeEventListener("mousemove", handleMouseMove);
        canvas.removeEventListener("mousedown", handleMouseDown);
        canvas.removeEventListener("mouseup", handleMouseUp);
        canvas.removeEventListener("mouseleave", handleMouseLeave);
      }
      if (btnStep) btnStep.removeEventListener("click", handleStep);
      if (btnReset) btnReset.removeEventListener("click", handleReset);
      if (btnAuto) btnAuto.removeEventListener("click", handleAuto);
      if (btnExport) btnExport.removeEventListener("click", exportRankings);
      if (speedSlider) speedSlider.removeEventListener("input", handleSpeed);
      window.removeEventListener("resize", handleResize);
      doc.removeEventListener("keydown", handleKeyDown);
    };

    return cleanup;
  }, []);

  return (
    <div
      ref={rootRef}
      className="comp-viz relative min-h-screen bg-slate-950 text-slate-100 overflow-x-hidden"
      style={{ colorScheme: "dark" }}
    >
      <div className="comp-viz__ambient fixed inset-0 z-0 pointer-events-none" aria-hidden="true">
        <div className="comp-viz__grid" />
      </div>

      <a
        href="#controls"
        className="comp-viz__skip sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50"
      >
        Skip to controls
      </a>

      <div className="relative z-10">
        <header className="px-4 sm:px-6 pt-6">
          <div className="max-w-6xl mx-auto">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <Link
                  to="/"
                  className="rounded-md bg-white/10 px-2.5 py-1 text-xs font-semibold tracking-wide text-white ring-1 ring-white/15 hover:bg-white/15"
                >
                  Back to leaderboard
                </Link>
                <span className="text-xs text-slate-400">Ranking Simulator</span>
              </div>
            </div>

            <div className="mt-6">
              <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
                Ranking Simulator
              </h1>
              <p className="mt-3 max-w-2xl text-slate-300">
                An explorable view of the competitive ranking engine. Scores flow from losers to
                winners, amplifying victories over strong opponents while dampening farmed wins.
              </p>
            </div>
          </div>
        </header>

        <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-6 pb-16 space-y-6">
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(320px,1fr)] items-start">
            <section className="space-y-4">
              <div className="comp-viz__panel comp-viz__panel--accent pointer-events-auto p-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-semibold text-white">Influence Graph</h2>
                    <p className="text-sm text-slate-300">
                      Watch score flow across recent matchups as PageRank iterates.
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs text-slate-400 min-w-[240px]">
                    <div className="flex items-center justify-between">
                      <span>Players</span>
                      <span id="nodeCount" className="font-data text-sm text-white">-</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Matchups</span>
                      <span id="edgeCount" className="font-data text-sm text-white">-</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Damping</span>
                      <span id="dampingValue" className="font-data text-sm text-white">-</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Threshold</span>
                      <span id="thresholdValue" className="font-data text-sm text-white">-</span>
                    </div>
                  </div>
                </div>

                <div
                  ref={canvasContainerRef}
                  className="comp-viz__canvas-shell mt-4"
                  role="img"
                  aria-label="Ranking graph simulation"
                >
                  <canvas ref={canvasRef} id="simCanvas" className="comp-viz__canvas" />
                  <div className="comp-viz__canvas-hint">
                    Drag nodes and hover edges
                    <span>Step / Auto to iterate</span>
                  </div>
                </div>
              </div>
            </section>

            <aside className="space-y-4" id="controls">
              <div className="comp-viz__panel comp-viz__panel--accent pointer-events-auto p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-white">
                      Controls <span className="text-fuchsia-300 font-light">/</span>
                    </h2>
                    <p className="text-[11px] text-slate-400">
                      Step through the ranking loop or auto-run to convergence.
                    </p>
                  </div>
                  <div className="flex items-center gap-1 text-[11px] text-slate-500">
                    <span className="rounded bg-slate-800/80 px-2 py-1">S</span>
                    <span className="rounded bg-slate-800/80 px-2 py-1">A</span>
                    <span className="rounded bg-slate-800/80 px-2 py-1">R</span>
                    <span className="rounded bg-slate-800/80 px-2 py-1">E</span>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-2">
                  <button
                    id="btnStep"
                    className="comp-viz__button comp-viz__button--primary"
                    aria-label="Step forward one iteration (S or Space)"
                  >
                    Step
                  </button>
                  <button
                    id="btnAuto"
                    className="comp-viz__button comp-viz__button--secondary comp-viz__button--auto"
                    aria-label="Toggle auto run (A)"
                  >
                    Auto
                  </button>
                </div>

                <div className="mt-4">
                  <div className="flex items-center justify-between text-[10px] text-slate-400 uppercase tracking-widest">
                    <label htmlFor="speedSlider">Speed</label>
                    <span id="speedValue" className="font-data text-slate-200">2x</span>
                  </div>
                  <input
                    type="range"
                    id="speedSlider"
                    min="0.5"
                    max="4"
                    step="0.5"
                    defaultValue="2"
                    className="comp-viz__slider mt-3"
                    aria-label="Animation speed"
                  />
                </div>

                <div className="mt-4 grid grid-cols-2 gap-2">
                  <button
                    id="btnReset"
                    className="comp-viz__button comp-viz__button--ghost"
                    aria-label="Reset simulation (R)"
                  >
                    Reset
                  </button>
                  <button
                    id="btnExport"
                    className="comp-viz__button comp-viz__button--ghost"
                    aria-label="Export rankings as CSV (E)"
                  >
                    Export
                  </button>
                </div>

                <div className="mt-4 border-t border-white/10 pt-4 text-[11px] text-slate-400">
                  Wins against strong opponents send more score. The loop repeats until the graph
                  stabilizes.
                </div>
              </div>

              <div className="comp-viz__panel pointer-events-auto p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                      Simulation State
                    </h3>
                    <div className="mt-1 text-2xl font-semibold text-white font-data" id="iterCount">
                      0
                    </div>
                  </div>
                  <div>
                    <span
                      id="statusText"
                      className="text-[11px] font-semibold text-emerald-300 bg-emerald-500/15 px-2.5 py-1 rounded-full border border-emerald-500/25"
                    >
                      Ready
                    </span>
                  </div>
                </div>

                <div className="mt-4">
                  <div className="flex items-center justify-between text-[10px] uppercase tracking-widest text-slate-400">
                    <span>Convergence</span>
                    <span id="deltaValue" className="font-data text-slate-200">-</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-slate-900/80 overflow-hidden">
                    <div
                      id="deltaBar"
                      className="h-full w-full bg-gradient-to-r from-fuchsia-500/80 to-purple-400/80 transition-all duration-300"
                    />
                  </div>
                </div>
              </div>

              <div className="comp-viz__panel pointer-events-auto p-4">
                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                  Convergence History
                </h3>
                <canvas ref={convergenceCanvasRef} id="convergenceCanvas" className="mt-3 h-16 w-full" />
              </div>

              <div className="comp-viz__panel pointer-events-auto p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                    Insight
                  </h3>
                  <span className="text-[10px] text-slate-500">Realtime</span>
                </div>
                <p id="insightText" className="mt-3 text-sm text-slate-200 leading-relaxed">
                  Tap Step or Auto Run to begin. Watch how scores flow from losers to winners.
                </p>
              </div>

              <div className="comp-viz__panel pointer-events-auto p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                    Current Leader
                  </h3>
                  <span className="text-[10px] text-fuchsia-200/70">Top Rank</span>
                </div>
                <div className="mt-2">
                  <div id="leaderName" className="text-xl font-semibold text-white">
                    -
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-3 text-[11px] text-slate-400">
                    <div>
                      Score <span id="leaderScore" className="font-data text-slate-100">-</span>
                    </div>
                    <div>
                      Skill <span id="leaderSkill" className="font-data text-slate-100">-</span>
                    </div>
                    <div>
                      Wins <span id="leaderWins" className="font-data text-slate-100">-</span>
                    </div>
                    <div>
                      Avg Opp <span id="leaderOpp" className="font-data">-</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="comp-viz__panel pointer-events-auto p-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                    Interaction Guide
                  </h3>
                </div>
                <div className="mt-2 grid gap-2 text-[11px] text-slate-400">
                  <div className="flex items-center justify-between">
                    <span>Drag nodes to reposition the graph</span>
                    <span className="text-slate-500">Mouse</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Highlight wins (green) and losses (red)</span>
                    <span className="text-slate-500">Hover</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Export the current ranking snapshot</span>
                    <span className="text-slate-500">E key</span>
                  </div>
                </div>
              </div>
            </aside>
          </div>

          <div>
            <div className="comp-viz__panel pointer-events-auto grid gap-6 lg:grid-cols-2 p-4">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                    Skill vs Score
                  </h3>
                  <span id="correlationValue" className="font-data text-fuchsia-200 text-xs">
                    r = -
                  </span>
                </div>
                <canvas ref={scatterCanvasRef} id="scatterCanvas" className="h-36 w-full" />
                <div className="mt-2 text-[10px] text-slate-500">True Skill -&gt;</div>
              </div>

              <div>
                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">
                  Score Ranking
                </h3>
                <canvas ref={barCanvasRef} id="barCanvas" className="h-36 w-full" />
                <div className="mt-2 text-[10px] text-slate-500">Top 12 by score</div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default CompetitionViz;
