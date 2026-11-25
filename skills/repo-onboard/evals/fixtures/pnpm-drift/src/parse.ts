export function parseAmount(raw: string): number {
  return Math.round(Number(raw.replace(/[^0-9.-]/g, "")) * 100);
}
