// ── Key label formatting ──────────────────────────────────────
// "invoice_number" → "Invoice Number"
// "customerName"   → "Customer Name"
export const formatKey = (key) => {
  if (!key || typeof key !== 'string') return key;
  return key
    .replace(/([a-z])([A-Z])/g, '$1 $2')   // camelCase split
    .replace(/[_\-]+/g, ' ')               // snake_case / kebab
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
};

// ── Currency keys detection ───────────────────────────────────
const CURRENCY_KEYS = [
  'amount', 'total', 'price', 'fee', 'charge', 'tax',
  'subtotal', 'discount', 'balance', 'cost', 'rate',
  'payment', 'paid', 'due', 'value', 'sum',
];

export const isCurrencyKey = (key) => {
  if (!key) return false;
  const lower = key.toLowerCase();
  return CURRENCY_KEYS.some((k) => lower.includes(k));
};

// ── Currency formatter ────────────────────────────────────────
// 25000 → "₹25,000"  |  25000.50 → "₹25,000.50"
export const formatCurrency = (value) => {
  const num = parseFloat(value);
  if (isNaN(num)) return String(value);
  return '₹' + num.toLocaleString('en-IN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
};

// ── Date detection & formatting ───────────────────────────────
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}(T[\d:.Z+\-]*)?$/;
const SLASH_DATE_RE = /^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}$/;

export const isDateString = (value) => {
  if (typeof value !== 'string') return false;
  return ISO_DATE_RE.test(value) || SLASH_DATE_RE.test(value);
};

export const formatDate = (value) => {
  try {
    const d = new Date(value);
    if (isNaN(d.getTime())) return value;
    return d.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return value;
  }
};

// ── Master value formatter ────────────────────────────────────
// Applies all rules: null, currency, date, else pass-through
export const formatValue = (value, keyName = '') => {
  // Null / undefined
  if (value === null || value === undefined) return 'Not Available';

  // Skip objects/arrays — handled by JSONViewer recursion
  if (typeof value === 'object') return value;

  // Boolean
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';

  // Currency
  if (typeof value === 'number' && isCurrencyKey(keyName)) {
    return formatCurrency(value);
  }

  // Date strings
  if (isDateString(value)) {
    return formatDate(value);
  }

  // Numeric currency (string like "25000" under a currency key)
  if (isCurrencyKey(keyName) && !isNaN(parseFloat(value)) && String(value).trim() !== '') {
    return formatCurrency(parseFloat(value));
  }

  return value;
};
