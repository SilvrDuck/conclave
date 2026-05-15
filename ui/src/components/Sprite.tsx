export const DOMUS_WIDTH = 24;
export const DOMUS_HEIGHT = 32;

const ROOF = "#8a3a1f";
const WALL = "#e6c98a";
const DOOR = "#3a2410";
const TRIM = "#5d534a";

function hashString(s: string): number {
  let h = 5381;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) + h) ^ s.charCodeAt(i);
  }
  return h >>> 0;
}

export function spritePosition(
  name: string,
  canvasWidth: number,
  canvasHeight: number,
) {
  const margin = DOMUS_WIDTH + 16;
  const usableW = canvasWidth - margin * 2;
  const usableH = canvasHeight - margin * 2;
  const h = hashString(name);
  const x = margin + (h % usableW);
  const y = margin + ((h >>> 8) % usableH);
  return { x, y };
}

export function drawDomus(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  options: { glow?: boolean; tint?: string; label?: string } = {},
) {
  const { glow = false, tint, label } = options;

  if (glow) {
    ctx.strokeStyle = "var(--gold)";
    ctx.strokeStyle = "#ffd84a";
    ctx.lineWidth = 2;
    ctx.strokeRect(x - 3, y - 3, DOMUS_WIDTH + 6, DOMUS_HEIGHT + 6);
  }

  ctx.fillStyle = tint ?? WALL;
  ctx.fillRect(x, y + 10, DOMUS_WIDTH, DOMUS_HEIGHT - 10);

  ctx.fillStyle = ROOF;
  ctx.beginPath();
  ctx.moveTo(x - 2, y + 12);
  ctx.lineTo(x + DOMUS_WIDTH / 2, y);
  ctx.lineTo(x + DOMUS_WIDTH + 2, y + 12);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = DOOR;
  ctx.fillRect(x + DOMUS_WIDTH / 2 - 3, y + DOMUS_HEIGHT - 10, 6, 10);

  ctx.fillStyle = TRIM;
  ctx.fillRect(x + 4, y + 16, 4, 4);
  ctx.fillRect(x + DOMUS_WIDTH - 8, y + 16, 4, 4);

  if (label) {
    ctx.fillStyle = "#f4ecd8";
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.textAlign = "center";
    ctx.fillText(label, x + DOMUS_WIDTH / 2, y + DOMUS_HEIGHT + 12);
  }
}
