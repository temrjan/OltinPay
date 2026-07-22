import { Dashboard } from "@/components/Dashboard";

// Public Proof-of-Reserve dashboard (no auth). Thin server shell; the live
// polling happens in the client Dashboard against the same-origin /api/* proxy.
export default function Page() {
  return <Dashboard />;
}
