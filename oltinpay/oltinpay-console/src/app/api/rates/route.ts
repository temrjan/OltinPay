import { getRates } from "@/lib/api";
import { proxyJson } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export const GET = (): Promise<Response> => proxyJson(getRates);
