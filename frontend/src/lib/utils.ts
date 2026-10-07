import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function round(n: number | null | undefined): string {
  return n === null || n === undefined ? "—" : String(Math.round(n));
}
