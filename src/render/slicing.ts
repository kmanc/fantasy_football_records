/** Equivalent of Python's `list[:10]` - the first 10 elements. */
export function top10<T>(items: T[]): T[] {
  return items.slice(0, 10);
}

/**
 * Equivalent of Python's `list[:-10:-1]` - the bottom 9 elements (not 10; the original app.py's
 * slice excludes the 10th-from-last), reversed so the most extreme value comes first.
 */
export function bottom9Reversed<T>(items: T[]): T[] {
  return items.slice(-9).reverse();
}
