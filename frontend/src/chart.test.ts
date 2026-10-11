import { describe, expect, it } from 'vitest';

import { holdRange } from './chart';

describe('chart range', () => {
  it('widens at once when a bar would not fit', () => {
    const narrow = holdRange(null, 2, 0);

    const wide = holdRange(narrow, 7, 1_000);

    expect(wide.limit).toBeGreaterThanOrEqual(7);
    expect(narrow.limit).toBeLessThan(wide.limit);
  });

  it('keeps a wider range while smaller readings arrive within a minute', () => {
    const wide = holdRange(null, 7, 0);

    const held = holdRange(holdRange(wide, 2, 1_000), 2, 59_000);

    expect(held.limit).toBe(wide.limit);
  });

  it('narrows once the data has fitted the smaller range for a minute', () => {
    const wide = holdRange(null, 7, 0);

    const narrowed = holdRange(holdRange(wide, 2, 1_000), 2, 61_000);

    expect(narrowed.limit).toBe(holdRange(null, 2, 0).limit);
  });

  it('restarts the wait when a reading needs the current range again', () => {
    const wide = holdRange(null, 7, 0);
    const waiting = holdRange(wide, 2, 1_000);
    const needed = holdRange(waiting, 7, 30_000);

    const held = holdRange(holdRange(needed, 2, 31_000), 2, 70_000);

    expect(held.limit).toBe(wide.limit);
  });
});
