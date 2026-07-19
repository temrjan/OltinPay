"use client";

import {
  ExternalLink,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { addressUrl, txUrl } from "@/lib/config";
import type {
  FeedReading,
  PorHistoryItem,
  PorResponse,
  RatesResponse,
} from "@/lib/types";

interface Data {
  por: PorResponse;
  rates: RatesResponse;
  history: PorHistoryItem[];
}

const POLL_MS = 7000;

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) {
    const body: unknown = await res.json().catch(() => ({}));
    const detail =
      body && typeof body === "object" && "error" in body
        ? String((body as { error: unknown }).error)
        : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

async function fetchAll(): Promise<Data> {
  const [por, rates, history] = await Promise.all([
    fetchJson<PorResponse>("/api/por"),
    fetchJson<RatesResponse>("/api/rates"),
    fetchJson<PorHistoryItem[]>("/api/history"),
  ]);
  return { por, rates, history };
}

const fmt = (n: number, digits = 2): string =>
  n.toLocaleString("en-US", { maximumFractionDigits: digits });

function ago(ms: number): string {
  const s = Math.max(0, Math.floor((Date.now() - ms) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

const shortHash = (h: string): string =>
  h.length > 12 ? `${h.slice(0, 6)}…${h.slice(-4)}` : h;

// Feed answer (integer string, scaled by `decimals`) -> human float.
const feedValue = (f: FeedReading): number =>
  Number(f.answer) / 10 ** f.decimals;

const answerToGrams = (answer: string, decimals: number): number =>
  Number(answer) / 10 ** decimals;

export function Dashboard() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // setState lives in the promise callbacks below (the blessed "async callback"
  // pattern) — never synchronously in the effect body.
  const apply = useCallback((d: Data) => {
    setData(d);
    setError(null);
    setUpdatedAt(Date.now());
  }, []);

  const fail = useCallback((e: unknown) => {
    setError(e instanceof Error ? e.message : "Failed to load");
  }, []);

  useEffect(() => {
    let cancelled = false;
    const tick = (): void => {
      fetchAll()
        .then((d) => {
          if (!cancelled) apply(d);
        })
        .catch((e: unknown) => {
          if (!cancelled) fail(e);
        });
    };
    tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [apply, fail]);

  // Manual refresh (user-initiated — spinner state is fine outside the effect).
  const refresh = (): void => {
    setRefreshing(true);
    fetchAll()
      .then(apply)
      .catch(fail)
      .finally(() => setRefreshing(false));
  };

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            OltinChain — Proof of Reserve
          </h1>
          <p className="text-text-muted text-sm">
            OLTIN is tokenized gold minted only against attested reserves. This
            page reads the live on-chain state.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {updatedAt !== null && (
            <span className="text-text-muted text-xs">
              updated {ago(updatedAt)}
            </span>
          )}
          <button
            onClick={refresh}
            className="border-border hover:border-gold flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors"
            aria-label="Refresh now"
          >
            <RefreshCw
              size={14}
              className={refreshing ? "animate-spin" : undefined}
            />
            Refresh
          </button>
        </div>
      </header>

      {error !== null && (
        <div className="border-red/40 bg-red/10 text-red mb-6 rounded-lg border px-4 py-3 text-sm">
          Live data unavailable: {error}
        </div>
      )}

      {data === null ? (
        <p className="text-text-muted">Loading live reserve data…</p>
      ) : (
        <Content data={data} />
      )}
    </main>
  );
}

function Content({ data }: { data: Data }) {
  const { por, rates, history } = data;
  const cov = por.coverage_ratio;
  const fullyBacked = cov !== null && cov >= 1;
  const noSupply = cov === null; // supply == 0 -> coverage undefined

  return (
    <>
      {/* Coverage hero */}
      <section
        className={`mb-6 rounded-2xl border p-6 ${
          noSupply
            ? "border-border"
            : fullyBacked
              ? "border-green/40 bg-green/5"
              : "border-red/40 bg-red/5"
        }`}
      >
        <div className="flex items-center gap-3">
          {noSupply ? (
            <ShieldCheck className="text-text-muted" size={28} />
          ) : fullyBacked ? (
            <ShieldCheck className="text-green" size={28} />
          ) : (
            <ShieldAlert className="text-red" size={28} />
          )}
          <div>
            <div className="text-3xl font-bold">
              {noSupply ? "—" : `${fmt(cov * 100, 1)}%`}
            </div>
            <div className="text-text-muted text-sm">
              {noSupply
                ? "No OLTIN in circulation yet — full reserve is spare mint capacity"
                : fullyBacked
                  ? "Fully backed — reserve covers all OLTIN in circulation"
                  : "Under-backed — reserve is below circulating OLTIN"}
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat
          label="Attested reserve (mint cap)"
          value={`${fmt(por.reserve_grams)} g`}
        />
        <Stat label="OLTIN in circulation" value={`${fmt(por.oltin_supply)}`} />
        <Stat
          label="OLTIN price"
          value={`${fmt(rates.oltin_price_uzd)} UZS`}
        />
        <Stat
          label="Reserve updated"
          value={
            por.reserve_updated_at === 0
              ? "never"
              : ago(por.reserve_updated_at * 1000)
          }
        />
      </section>

      {/* Rates */}
      <section className="mb-6 grid grid-cols-2 gap-4">
        <Stat
          label="XAU / USD"
          value={`$${fmt(feedValue(rates.xau_usd))}`}
        />
        <Stat
          label="UZS / USD (×1e8)"
          value={fmt(feedValue(rates.uzs_usd), 8)}
        />
      </section>

      {/* Attestation feed */}
      <section className="border-border mb-6 rounded-2xl border p-5">
        <h2 className="mb-4 font-semibold">Reserve attestations</h2>
        {history.length === 0 ? (
          <p className="text-text-muted text-sm">No attestations indexed yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-text-muted text-left">
                <tr>
                  <th className="pb-2 font-normal">Grams</th>
                  <th className="pb-2 font-normal">Block</th>
                  <th className="pb-2 font-normal">Tx</th>
                  <th className="pb-2 font-normal">Indexed</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.tx_hash} className="border-border border-t">
                    <td className="py-2">
                      {fmt(answerToGrams(h.answer, por.reserve_decimals))}
                    </td>
                    <td className="py-2">{h.block_number}</td>
                    <td className="py-2">
                      <a
                        href={txUrl(h.tx_hash)}
                        target="_blank"
                        rel="noreferrer"
                        className="text-gold inline-flex items-center gap-1"
                      >
                        {shortHash(h.tx_hash)}
                        <ExternalLink size={12} />
                      </a>
                    </td>
                    <td className="text-text-muted py-2">
                      {ago(new Date(h.indexed_at).getTime())}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Contracts */}
      <section className="border-border rounded-2xl border p-5">
        <h2 className="mb-4 font-semibold">On-chain contracts (zkSync Sepolia)</h2>
        <div className="grid gap-2 text-sm">
          <Contract label="OltinToken (OLTIN)" address={por.contracts.oltin} />
          <Contract label="UZD stablecoin" address={por.contracts.uzd} />
          <Contract
            label="Reserve attestor"
            address={por.contracts.reserve_attestor}
          />
          <Contract label="Exchange" address={por.contracts.exchange} />
        </div>
      </section>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-border bg-card rounded-xl border p-4">
      <div className="text-text-muted mb-1 text-xs">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}

function Contract({ label, address }: { label: string; address: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-text-muted">{label}</span>
      <a
        href={addressUrl(address)}
        target="_blank"
        rel="noreferrer"
        className="text-gold inline-flex items-center gap-1 font-mono text-xs"
      >
        {shortHash(address)}
        <ExternalLink size={12} />
      </a>
    </div>
  );
}
