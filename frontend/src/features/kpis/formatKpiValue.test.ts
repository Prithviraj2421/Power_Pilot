import { describe, expect, it } from 'vitest';
import { formatKpiValue } from './formatKpiValue';

describe('formatKpiValue', () => {
  it('formats large values without decimals and small ones with precision', () => {
    expect(formatKpiValue({ computed_value: 2297200.8603 })).toBe('2,297,201');
    expect(formatKpiValue({ computed_value: 459.48 })).toBe('459.48');
    expect(formatKpiValue({ computed_value: 0.04321 })).toBe('0.0432');
  });

  it('returns null when there is no verified value, so nothing is invented', () => {
    expect(formatKpiValue({})).toBeNull();
    expect(formatKpiValue({ computed_value: null })).toBeNull();
    expect(formatKpiValue({ computed_value: Number.NaN })).toBeNull();
    expect(formatKpiValue({ computed_value: Infinity })).toBeNull();
  });

  it('keeps a genuine zero', () => {
    expect(formatKpiValue({ computed_value: 0 })).toBe('0');
  });
});
