import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const css = readFileSync(new URL('../src/index.css', import.meta.url), 'utf8');
const luminance = hex => {
  const rgb = hex.match(/[a-f\d]{2}/gi).map(v => parseInt(v, 16) / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
  return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
};
const ratio = (a,b) => (Math.max(luminance(a), luminance(b))+.05)/(Math.min(luminance(a),luminance(b))+.05);
test('text, navigation and semantic state tokens meet 4.5:1 in both solid themes', () => {
  for (const block of css.matchAll(/:root(?:\[data-theme='dark'\])?\s*\{([^}]+)\}/g)) {
    const tokens = Object.fromEntries([...block[1].matchAll(/--([\w-]+):\s*(#[\da-f]{6})/gi)].map(m => [m[1],m[2]]));
    for (const [foreground,background] of [['text','surface'],['muted','surface'],['muted','surface-soft'],['accent-text','accent-soft'],['sidebar-muted','sidebar'],['warning','warning-bg'],['critical','critical-bg'],['normal','normal-bg'],['sample','sample-bg']]) {
      assert.ok(ratio(tokens[foreground],tokens[background]) >= 4.5, `${foreground}/${background}: ${ratio(tokens[foreground],tokens[background])}`);
    }
  }
});
