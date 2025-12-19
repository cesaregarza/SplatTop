export const escapeCsvCell = (value) => {
  if (value === null || value === undefined) return "";
  const stringValue = String(value);

  const needsFormulaEscape = /^[\s]*[=+\-@]/.test(stringValue) || /^[\t\r\n]/.test(stringValue);
  const safeValue = needsFormulaEscape ? `'${stringValue}` : stringValue;
  const escapedValue = safeValue.replace(/"/g, '""');
  const needsQuotes = /[",\r\n]/.test(escapedValue);
  return needsQuotes ? `"${escapedValue}"` : escapedValue;
};

export const toCsvRow = (cells) => cells.map(escapeCsvCell).join(",");

export const safePearsonCorrelation = (items, getX, getY) => {
  let count = 0;

  let sumX = 0;
  let sumY = 0;
  let sumXY = 0;
  let sumX2 = 0;
  let sumY2 = 0;

  items.forEach((item) => {
    const x = getX(item);
    const y = getY(item);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;

    count += 1;
    sumX += x;
    sumY += y;
    sumXY += x * y;
    sumX2 += x * x;
    sumY2 += y * y;
  });

  if (count === 0) return 0;

  const num = count * sumXY - sumX * sumY;
  const termX = count * sumX2 - sumX * sumX;
  const termY = count * sumY2 - sumY * sumY;
  const denSq = termX * termY;
  if (!Number.isFinite(num) || !Number.isFinite(denSq) || denSq <= 0) return 0;

  const den = Math.sqrt(denSq);
  if (!Number.isFinite(den) || den === 0) return 0;

  const correlation = num / den;
  if (!Number.isFinite(correlation)) return 0;
  return Math.max(-1, Math.min(1, correlation));
};
