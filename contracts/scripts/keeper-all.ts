/**
 * Shared keeper runner. Runs all three keepers SEQUENTIALLY in one process —
 * one wallet, one nonce stream, so the nonce race between keepers sharing the
 * poster key (К-7) is structurally impossible. Each feed runs in its own
 * try/catch: one feed's failure does not cancel the others.
 *
 * This is the ONLY entry cron/P4-A schedules:
 *   npm run keeper:all
 *
 * Exit codes (per-feed results are logged; the process code is the worst):
 *   1 if any feed refused/errored, else 0 if any feed posted, else 2.
 */

import { run as runXau } from "./keeper-xau";
import { run as runReserve } from "./keeper-reserve";
import { run as runUzs } from "./keeper-uzs";
import { EXIT_POSTED, EXIT_SKIPPED, EXIT_FAILED } from "./keeper-lib";

async function main(): Promise<number> {
  const feeds: ReadonlyArray<readonly [string, () => Promise<number>]> = [
    ["xau", runXau],
    ["reserve", runReserve],
    ["uzs", runUzs],
  ];

  let worst = EXIT_SKIPPED;
  for (const [name, runFeed] of feeds) {
    let code: number;
    try {
      code = await runFeed();
    } catch (e: unknown) {
      console.error(`[${name}] FATAL: ${e instanceof Error ? e.message : e}`);
      code = EXIT_FAILED;
    }
    console.log(`[${name}] exit=${code}`);
    if (code === EXIT_FAILED) {
      worst = EXIT_FAILED;
    } else if (code === EXIT_POSTED && worst !== EXIT_FAILED) {
      worst = EXIT_POSTED;
    }
  }
  return worst;
}

if (require.main === module) {
  main()
    .then((code) => process.exit(code))
    .catch((e: unknown) => {
      console.error(e instanceof Error ? e.message : e);
      process.exit(EXIT_FAILED);
    });
}
