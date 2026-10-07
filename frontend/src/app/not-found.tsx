import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-md px-4 py-24">
      <h1>404</h1>
      <p className="mt-3 text-muted">This page doesn&apos;t exist. / Такой страницы нет.</p>
      <Link href="/" className="mt-6 inline-block underline underline-offset-2">OfferReady</Link>
    </main>
  );
}
