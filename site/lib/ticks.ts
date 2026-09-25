// Clean axis ticks (0 / 2,000 / 4,000 ...). Shared by server charts and client tools.
export function niceTicks(min: number, max: number, count = 5): number[] {
  const span = max - min || Math.abs(max) || 1;
  const raw = span / count;
  const pow = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * pow).find((s) => span / s <= count) ?? 10 * pow;
  // a dip just below zero shouldn't add a whole empty band under the axis
  const lo = min < 0 && -min < step * 0.15 ? 0 : Math.floor(min / step) * step;
  const hi = Math.ceil(max / step) * step;
  const out: number[] = [];
  for (let v = lo; v <= hi + step / 2; v += step) out.push(Number(v.toFixed(10)));
  return out;
}
