import { BankPanel } from "@/components/BankPanel";

// Operator-gated bank panel. The gate and HMAC signing are enforced server-side
// (E2/E3) in the /api/bank/* route handlers; this page only renders the UI.
export default function Page() {
  return <BankPanel />;
}
