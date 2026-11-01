// Single source of truth for pricing and upload rules.
// The price shown in the UI and the amount charged by Stripe both come from here.

export const PRICE_CENTS = 5000;
export const PRICE_DISPLAY = "$50";
export const CURRENCY = "usd";

export const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;
export const ALLOWED_EXTENSIONS = ["csv", "xlsx", "xls", "pdf"] as const;
export type AllowedExtension = (typeof ALLOWED_EXTENSIONS)[number];

export const BRAND = "Verity Analytics";
