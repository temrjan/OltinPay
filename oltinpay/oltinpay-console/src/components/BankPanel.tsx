"use client";

import { useCallback, useState } from "react";

const OP_HEADER = "x-operator-password";

interface BankWithdrawal {
  id: string;
  oltinId: string;
  walletAddress: string | null;
  amountUzd: number;
  status: string;
}

interface CallResult {
  status: number;
  data: unknown;
}

function message(r: CallResult): string {
  if (r.status >= 200 && r.status < 300) {
    const tx = (r.data as { txHash?: string }).txHash;
    return tx ? `OK — tx ${tx.slice(0, 12)}…` : "OK";
  }
  const d = r.data as { detail?: string; error?: string };
  return `Error ${r.status}: ${d.detail ?? d.error ?? "request failed"}`;
}

export function BankPanel() {
  const [password, setPassword] = useState("");
  const [authed, setAuthed] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [withdrawals, setWithdrawals] = useState<BankWithdrawal[]>([]);

  const [att, setAtt] = useState({ grams: "", auditRef: "" });
  const [fx, setFx] = useState({ uzsPerUsd: "", source: "CBU" });
  const [dep, setDep] = useState({ oltinId: "", amountUzs: "", bankTxId: "" });

  const call = useCallback(
    async (
      path: string,
      method: "GET" | "POST",
      body?: unknown,
    ): Promise<CallResult> => {
      const res = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json", [OP_HEADER]: password },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const data: unknown = await res.json().catch(() => ({}));
      return { status: res.status, data };
    },
    [password],
  );

  const loadWithdrawals = useCallback(async () => {
    const r = await call("/api/bank/withdrawals", "GET");
    if (r.status >= 200 && r.status < 300 && Array.isArray(r.data)) {
      setWithdrawals(r.data as BankWithdrawal[]);
    }
  }, [call]);

  const login = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);
    const res = await fetch("/api/bank/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (res.ok) {
      setAuthed(true);
      void loadWithdrawals();
    } else {
      setLoginError("Invalid operator password");
    }
  };

  const run = async (path: string, body: unknown) => {
    setBusy(true);
    setMsg(null);
    try {
      setMsg(message(await call(path, "POST", body)));
      void loadWithdrawals();
    } finally {
      setBusy(false);
    }
  };

  if (!authed) {
    return (
      <main className="mx-auto max-w-sm px-4 py-16">
        <h1 className="mb-2 text-xl font-semibold">Bank operator panel</h1>
        <p className="text-text-muted mb-6 text-sm">
          Drives real testnet mint/burn. Operator access only.
        </p>
        <form onSubmit={login} className="space-y-3">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Operator password"
            className="border-border bg-card w-full rounded-lg border px-3 py-2 text-sm"
            autoFocus
          />
          <button
            type="submit"
            className="bg-gold w-full rounded-lg px-3 py-2 text-sm font-medium text-black"
          >
            Enter
          </button>
          {loginError !== null && (
            <p className="text-red text-sm">{loginError}</p>
          )}
        </form>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="mb-6 text-xl font-semibold">Bank operator panel</h1>

      {msg !== null && (
        <div className="border-border bg-card mb-6 rounded-lg border px-4 py-3 text-sm">
          {msg}
        </div>
      )}

      <Card title="Post reserve attestation">
        <Field
          label="Grams of gold"
          type="number"
          value={att.grams}
          onChange={(e) => setAtt({ ...att, grams: e.target.value })}
        />
        <Field
          label="Audit reference"
          value={att.auditRef}
          onChange={(e) => setAtt({ ...att, auditRef: e.target.value })}
        />
        <Action
          busy={busy}
          onClick={() =>
            run("/api/bank/attestation", {
              grams: Number(att.grams),
              auditRef: att.auditRef,
            })
          }
        />
      </Card>

      <Card title="Post UZS/USD rate">
        <Field
          label="UZS per USD"
          type="number"
          value={fx.uzsPerUsd}
          onChange={(e) => setFx({ ...fx, uzsPerUsd: e.target.value })}
        />
        <Field
          label="Source"
          value={fx.source}
          onChange={(e) => setFx({ ...fx, source: e.target.value })}
        />
        <Action
          busy={busy}
          onClick={() =>
            run("/api/bank/fx", {
              uzsPerUsd: Number(fx.uzsPerUsd),
              source: fx.source,
            })
          }
        />
      </Card>

      <Card title="Confirm fiat deposit (mint UZD)">
        <Field
          label="Oltin ID"
          value={dep.oltinId}
          onChange={(e) => setDep({ ...dep, oltinId: e.target.value })}
        />
        <Field
          label="Amount UZS"
          type="number"
          value={dep.amountUzs}
          onChange={(e) => setDep({ ...dep, amountUzs: e.target.value })}
        />
        <Field
          label="Bank tx id"
          value={dep.bankTxId}
          onChange={(e) => setDep({ ...dep, bankTxId: e.target.value })}
        />
        <Action
          busy={busy}
          onClick={() =>
            run("/api/bank/deposit", {
              oltinId: dep.oltinId,
              amountUzs: Number(dep.amountUzs),
              bankTxId: dep.bankTxId,
            })
          }
        />
      </Card>

      <Card title={`Pending withdrawals (${withdrawals.length})`}>
        {withdrawals.length === 0 ? (
          <p className="text-text-muted text-sm">No pending withdrawals.</p>
        ) : (
          <div className="space-y-2">
            {withdrawals.map((w) => (
              <div
                key={w.id}
                className="border-border flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-sm"
              >
                <div>
                  <div className="font-medium">{w.amountUzd} UZD</div>
                  <div className="text-text-muted text-xs">
                    {w.oltinId} · {w.walletAddress ?? "no wallet"}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    disabled={busy}
                    onClick={() =>
                      run(`/api/bank/withdrawals/${w.id}`, { action: "confirm" })
                    }
                    className="bg-green rounded-lg px-3 py-1.5 text-xs font-medium text-black disabled:opacity-50"
                  >
                    Confirm (burn)
                  </button>
                  <button
                    disabled={busy}
                    onClick={() =>
                      run(`/api/bank/withdrawals/${w.id}`, { action: "reject" })
                    }
                    className="border-border rounded-lg border px-3 py-1.5 text-xs"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </main>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-border mb-4 rounded-2xl border p-5">
      <h2 className="mb-4 font-semibold">{title}</h2>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function Field({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="text-text-muted mb-1 block text-xs">{label}</span>
      <input
        {...props}
        className="border-border bg-card w-full rounded-lg border px-3 py-2 text-sm"
      />
    </label>
  );
}

function Action({ busy, onClick }: { busy: boolean; onClick: () => void }) {
  return (
    <button
      disabled={busy}
      onClick={onClick}
      className="bg-gold rounded-lg px-4 py-2 text-sm font-medium text-black disabled:opacity-50"
    >
      Submit (signs &amp; broadcasts)
    </button>
  );
}
