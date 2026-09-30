const NARROW_NBSP = " ";

/** French typography: narrow no-break space before ; : ! ? and inside « ». */
export function fr(text: string): string {
  return text
    .replace(/\s+([;:!?»])/g, `${NARROW_NBSP}$1`)
    .replace(/«\s+/g, `«${NARROW_NBSP}`)
    .replace(/'/g, "’");
}
