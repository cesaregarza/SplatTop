import { safePearsonCorrelation, toCsvRow } from "./competitionVizUtils";

export const createCompetitionVizRuntime = ({
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
}) => {
  const win = view || doc.defaultView || window;

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("Canvas 2D context is not available.");
  }

  let autoRunTimeout = null;
  let resizeTimeout = null;
  let disposed = false;
  let stepInProgress = false;

  const previousTitle = doc.title;

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
      edgeBase: "217, 70, 239",
      particle: "#d946ef",
      text: "#f8fafc",
      highlightIn: "#e879f9",
      highlightOut: "#c026d3",
    },
  };

  const STATUS_CLASS_TEAL =
    "inline-flex items-center leading-none text-[11px] font-semibold text-[#22d3d3] bg-[#22d3d3]/15 px-3 py-1.5 rounded-full border border-[#22d3d3]/25";
  const STATUS_CLASS_PURPLE =
    "inline-flex items-center leading-none text-[11px] font-semibold text-[#d946ef] bg-[#d946ef]/15 px-3 py-1.5 rounded-full border border-[#d946ef]/25";

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
  let canvasRect = null;
  let canvasRectStale = true;

  const convergenceHistory = [];
  const MAX_CONVERGENCE_HISTORY = 60;
  const particlePool = [];

  const resizeMainCanvas = () => {
    const ratio = win.devicePixelRatio || 1;
    const rect = canvasContainer.getBoundingClientRect();
    width = Math.max(1, Math.floor(rect.width));
    height = Math.max(320, Math.floor(rect.height));
    canvas.width = Math.max(1, Math.floor(width * ratio));
    canvas.height = Math.max(1, Math.floor(height * ratio));
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    canvasRectStale = true;
  };

  const getCanvasRect = () => {
    if (!canvasRect || canvasRectStale) {
      canvasRect = canvas.getBoundingClientRect();
      canvasRectStale = false;
    }
    return canvasRect;
  };

  const relayoutNodesAfterResize = (prevWidth, prevHeight) => {
    if (prevWidth <= 0 || prevHeight <= 0) return;
    if (nodes.length === 0) return;

    const prevCx = prevWidth / 2;
    const prevCy = prevHeight / 2;
    const cx = width / 2;
    const cy = height / 2;
    const scaleX = width / prevWidth;
    const scaleY = height / prevHeight;

    nodes.forEach((node) => {
      node.x = (node.x - prevCx) * scaleX + cx;
      node.y = (node.y - prevCy) * scaleY + cy;

      const margin = Math.max(0, node.displayRadius || CONFIG.node.baseRadius);
      node.x = Math.max(margin, Math.min(width - margin, node.x));
      node.y = Math.max(margin, Math.min(height - margin, node.y));
    });
  };

  const resizeChartCanvas = (targetCanvas) => {
    const ratio = win.devicePixelRatio || 1;
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

  const calculateCorrelation = () =>
    safePearsonCorrelation(nodes, (node) => node.trueSkill, (node) => node.rank);

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
    const csvRows = [
      toCsvRow(["Rank", "Player", "Score", "TrueSkill", "TotalWins", "AvgOpponentSkill"]),
      ...sorted.map((node, index) =>
        toCsvRow([
          index + 1,
          node.label,
          node.rank.toFixed(6),
          node.trueSkill,
          node.totalWins,
          node.avgOpponentSkill.toFixed(3),
        ])
      ),
    ];
    const csv = csvRows.join("\n");

    const BlobCtor = win.Blob || Blob;
    const blob = new BlobCtor([csv], { type: "text/csv" });
    const link = doc.createElement("a");
    link.href = win.URL.createObjectURL(blob);
    link.download = `pagerank_iter${iteration}.csv`;
    doc.body.appendChild(link);
    link.click();
    doc.body.removeChild(link);
    win.URL.revokeObjectURL(link.href);
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

      context.fillStyle = "#c9d1d9";
      context.font = "10px ui-sans-serif, system-ui, sans-serif";
      const shortName = this.label.split(" ")[0];
      context.fillText(shortName, this.x, this.y + this.displayRadius + 18);
    }

    getHeatColor(t) {
      const r1 = 192;
      const g1 = 38;
      const b1 = 211;
      const r2 = 232;
      const g2 = 121;
      const b2 = 249;

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
        strokeStyle = `rgba(${CONFIG.colors.edgeBase}, 0.03)`;
        lineWidth = 1;
      } else {
        const alpha = Math.min(0.26, 0.08 + this.weight / 80);
        strokeStyle = `rgba(${CONFIG.colors.edgeBase}, ${alpha})`;
        lineWidth = Math.min(3.5, 0.9 + this.weight * 0.2);
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

  const stopAutoRun = () => {
    autoRun = false;
    ui.btnAuto.textContent = "Auto";
    ui.btnAuto.classList.remove("is-active");
    if (autoRunTimeout) {
      win.clearTimeout(autoRunTimeout);
      autoRunTimeout = null;
    }
  };

  const updateUI = () => {
    ui.iterCount.textContent = iteration;

    if (iteration === 0) {
      ui.deltaValue.textContent = "-";
      ui.deltaBar.style.width = "100%";
    } else {
      ui.deltaValue.textContent = lastDelta.toFixed(4);
      const logDelta = Math.log10(lastDelta + 0.0001);
      const logMax = Math.log10(5);
      const logMin = Math.log10(CONFIG.physics.convergenceThreshold);
      const percent = Math.max(
        0,
        Math.min(100, ((logDelta - logMin) / (logMax - logMin)) * 100)
      );
      ui.deltaBar.style.width = `${percent}%`;
    }

    chartsDirty = true;
  };

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

    const count = sceneData.nodes.length;
    sceneData.nodes.forEach((dataNode, index) => {
      const angle = (index / count) * Math.PI * 2 - Math.PI / 2;
      const radius = Math.min(width, height) * 0.3;
      const x = cx + Math.cos(angle) * radius;
      const y = cy + Math.sin(angle) * radius;
      nodes.push(new Node(dataNode.id, x, y, dataNode.label));
    });

    sceneData.links.forEach((dataLink) => {
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

    ui.nodeCount.textContent = nodes.length;
    ui.edgeCount.textContent = links.length;
    ui.dampingValue.textContent = CONFIG.dampingFactor.toFixed(2);
    ui.thresholdValue.textContent = CONFIG.physics.convergenceThreshold.toFixed(3);

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
        if (totalWeight > 0) {
          outboundLinks.forEach((link) => {
            const share = link.weight / totalWeight;
            const passValue = source.rank * damping * share;
            link.target.nextRank += passValue;
            particles.push(getParticle(link, passValue));
          });
        } else if (count > 0) {
          const distributeToAll = (source.rank * damping) / count;
          nodes.forEach((target) => {
            target.nextRank += distributeToAll;
          });
        }
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
    ui.btnStep.disabled = false;

    if (totalDelta < CONFIG.physics.convergenceThreshold) {
      stopAutoRun();
      ui.statusText.textContent = "Stable";
      ui.statusText.className = STATUS_CLASS_TEAL;
      updateUI();
      return;
    }

    ui.statusText.textContent = "Ready";
    ui.statusText.className = STATUS_CLASS_TEAL;

    updateUI();

    if (autoRun) {
      autoRunTimeout = win.setTimeout(() => {
        if (!disposed && autoRun) performStep();
      }, CONFIG.animation.autoRunDelay);
    }
  };

  const performStep = () => {
    if (disposed) return;
    if (stepInProgress || isAnimating) return;
    stepInProgress = true;
    calculateNextStep();
    isAnimating = true;

    ui.statusText.textContent = "Computing";
    ui.statusText.className = STATUS_CLASS_PURPLE;

    ui.btnStep.disabled = true;
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

    context.fillStyle = "rgba(13, 17, 23, 0.92)";
    context.strokeStyle = "rgba(217, 70, 239, 0.55)";
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
    context.fillStyle = "#8b949e";

    context.fillText(`Score: ${node.rank.toFixed(3)}`, boxX + padding, boxY + padding + 20);
    context.fillText(`True Skill: ${node.trueSkill}`, boxX + padding, boxY + padding + 36);
    context.fillText(`Total Wins: ${node.totalWins}`, boxX + padding, boxY + padding + 52);

    context.fillText("Avg Opp Skill:", boxX + padding, boxY + padding + 68);
    context.fillStyle = "#c9d1d9";
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

      chartCtx.fillStyle = "#8b949e";
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

    chartCtx.strokeStyle = "rgba(255, 255, 255, 0.12)";
    chartCtx.lineWidth = 1;
    chartCtx.beginPath();
    chartCtx.moveTo(marginLeft, marginTop);
    chartCtx.lineTo(marginLeft, chartH - marginBottom);
    chartCtx.lineTo(chartW - marginRight, chartH - marginBottom);
    chartCtx.stroke();

    chartCtx.fillStyle = "#8b949e";
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

      const denom = count * sumX2 - sumX ** 2;
      if (denom !== 0) {
        const slope = (count * sumXY - sumX * sumY) / denom;
        const intercept = (sumY - slope * sumX) / count;

        chartCtx.strokeStyle = "rgba(217, 70, 239, 0.35)";
        chartCtx.lineWidth = 1;
        chartCtx.setLineDash([4, 4]);
        chartCtx.beginPath();

        const x1 = marginLeft;
        const y1 = (chartH - marginBottom) - (intercept / maxRank) * plotH;
        const x2 = chartW - marginRight;
        const y2 =
          (chartH - marginBottom) - ((slope * maxSkill + intercept) / maxRank) * plotH;

        chartCtx.moveTo(x1, Math.max(marginTop, Math.min(chartH - marginBottom, y1)));
        chartCtx.lineTo(x2, Math.max(marginTop, Math.min(chartH - marginBottom, y2)));
        chartCtx.stroke();
        chartCtx.setLineDash([]);
      }
    }

    nodes.forEach((node) => {
      const x = marginLeft + (node.trueSkill / maxSkill) * plotW;
      const y = (chartH - marginBottom) - (node.rank / maxRank) * plotH;
      const heat = Math.min(1, (node.rank - 0.5) / 3);
      chartCtx.fillStyle = node.getHeatColor(heat);
      chartCtx.beginPath();
      chartCtx.arc(x, y, 5, 0, Math.PI * 2);
      chartCtx.fill();

      chartCtx.strokeStyle = "rgba(255, 255, 255, 0.28)";
      chartCtx.lineWidth = 1;
      chartCtx.stroke();
    });

    const correlation = calculateCorrelation();
    ui.correlationValue.textContent = `r = ${correlation.toFixed(3)}`;
  };

  const generateInsight = () => {
    if (iteration === 0) {
      ui.insightText.innerHTML =
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
        ui.insightText.innerHTML = `<strong class="text-[#22d3d3]">Converged.</strong> <strong class="text-fuchsia-300">${top.label.split(" ")[0]}</strong> matches the highest skill player.`;
      } else {
        const topSkillScorePos = scorePosition.get(topSkill.id);
        ui.insightText.innerHTML = `<strong class="text-[#22d3d3]">Converged.</strong> <strong class="text-fuchsia-300">${top.label.split(" ")[0]}</strong> leads. The highest-skill player (${topSkill.label.split(" ")[0]}) is #${topSkillScorePos}.`;
      }
      return;
    }

    if (iteration <= 3) {
      ui.insightText.innerHTML = `<strong class="text-fuchsia-300">Iteration ${iteration}:</strong> scores are redistributing. Beating strong opponents carries more weight.`;
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
      ui.insightText.innerHTML = `<strong class="text-fuchsia-300">${biggestRiser.label.split(" ")[0]}</strong> jumped from #${winsPos} (wins) to <strong class="text-fuchsia-300">#${scorePos}</strong> (score) on quality opponents.`;
      return;
    }

    if (maxFall <= -2 && biggestFaller) {
      const winsPos = winsPosition.get(biggestFaller.id);
      const scorePos = scorePosition.get(biggestFaller.id);
      ui.insightText.innerHTML = `<strong class="text-[#8b949e]">${biggestFaller.label.split(" ")[0]}</strong> slid from #${winsPos} (wins) to <strong class="text-[#8b949e]">#${scorePos}</strong> (score) with weaker matchups.`;
      return;
    }

    const topAvgOpp = top.avgOpponentSkill.toFixed(2);
    ui.insightText.innerHTML = `<strong class="text-white">${top.label.split(" ")[0]}</strong> leads with ${top.totalWins} wins and avg opponent skill ${topAvgOpp}.`;
  };

  const drawConvergenceChart = () => {
    const { ctx: chartCtx, width: chartW, height: chartH } =
      resizeChartCanvas(convergenceCanvas);
    if (!chartCtx) return;

    chartCtx.clearRect(0, 0, chartW, chartH);

    if (convergenceHistory.length < 2) {
      chartCtx.fillStyle = "#8b949e";
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

    chartCtx.strokeStyle = "rgba(255, 255, 255, 0.14)";
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
        padding + (index / (convergenceHistory.length - 1)) * (chartW - padding * 2);
      const y =
        chartH - padding - (point.delta / maxDelta) * (chartH - padding * 2);

      if (index === 0) {
        chartCtx.moveTo(x, y);
      } else {
        chartCtx.lineTo(x, y);
      }
    });

    chartCtx.stroke();

    const gradient = chartCtx.createLinearGradient(0, 0, 0, chartH);
    gradient.addColorStop(0, "rgba(217, 70, 239, 0.3)");
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

    ui.leaderName.textContent = leader.label.split(" ")[0];
    ui.leaderScore.textContent = leader.rank.toFixed(3);
    ui.leaderSkill.textContent = leader.trueSkill.toFixed(2);
    ui.leaderWins.textContent = leader.totalWins;
    ui.leaderOpp.textContent = leader.avgOpponentSkill.toFixed(2);

    ui.leaderOpp.className = "font-data text-white";
  };

  const tick = () => {
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
  };

  const handleMouseMove = (event) => {
    const rect = getCanvasRect();
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
    if (!event) return;
    const tagName = event.target?.tagName;
    if (tagName === "INPUT") return;

    switch (event.key.toLowerCase()) {
      case " ":
      case "s":
        event.preventDefault();
        stopAutoRun();
        performStep();
        break;
      case "a":
        event.preventDefault();
        handleAuto();
        break;
      case "r":
        event.preventDefault();
        handleReset();
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
    canvasRectStale = true;
    if (resizeTimeout) win.clearTimeout(resizeTimeout);
    resizeTimeout = win.setTimeout(() => {
      const prevWidth = width;
      const prevHeight = height;
      resizeMainCanvas();
      relayoutNodesAfterResize(prevWidth, prevHeight);
      chartsDirty = true;
    }, 150);
  };

  const handleScroll = () => {
    canvasRectStale = true;
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

    ui.statusText.textContent = "Ready";
    ui.statusText.className = STATUS_CLASS_TEAL;

    chartsDirty = true;
    updateUI();
    generateInsight();
  };

  const handleAuto = () => {
    if (autoRun) {
      stopAutoRun();
    } else {
      autoRun = true;
      ui.btnAuto.textContent = "Stop";
      ui.btnAuto.classList.add("is-active");
      performStep();
    }
  };

  const handleStep = () => {
    stopAutoRun();
    performStep();
  };

  const handleSpeed = (event) => {
    const nextSpeed = parseFloat(event.target.value);
    if (!Number.isFinite(nextSpeed)) return;
    CONFIG.animation.speed = nextSpeed;
    ui.speedValue.textContent = `${CONFIG.animation.speed}x`;
  };

  const start = () => {
    doc.title = "Ranking Simulator - splat.top";
    resizeMainCanvas();

    const initialSpeed = parseFloat(ui.speedSlider.value);
    if (Number.isFinite(initialSpeed)) {
      CONFIG.animation.speed = initialSpeed;
      ui.speedValue.textContent = `${CONFIG.animation.speed}x`;
    }

    init();
    tick();
  };

  const dispose = () => {
    disposed = true;
    doc.title = previousTitle;
    stopAutoRun();
    if (autoRunTimeout) win.clearTimeout(autoRunTimeout);
    if (resizeTimeout) win.clearTimeout(resizeTimeout);
    autoRunTimeout = null;
    resizeTimeout = null;
  };

  return {
    root,
    canvas,
    start,
    tick,
    dispose,
    handleResize,
    handleScroll,
    handleKeyDown,
    handleMouseMove,
    handleMouseDown,
    handleMouseUp,
    handleMouseLeave,
    handleStep,
    handleAuto,
    handleReset,
    handleSpeed,
    exportRankings,
  };
};
