import { afterEach, describe, expect, it } from "vitest";

import { checkOperator } from "./operator";

const ORIG = process.env.CONSOLE_OPERATOR_PASSWORD;

afterEach(() => {
  if (ORIG === undefined) {
    delete process.env.CONSOLE_OPERATOR_PASSWORD;
  } else {
    process.env.CONSOLE_OPERATOR_PASSWORD = ORIG;
  }
});

describe("checkOperator", () => {
  it("accepts the exact configured password", () => {
    process.env.CONSOLE_OPERATOR_PASSWORD = "s3cret-operator";
    expect(checkOperator("s3cret-operator")).toBe(true);
  });

  it("rejects a wrong password (incl. one-char / case difference)", () => {
    process.env.CONSOLE_OPERATOR_PASSWORD = "s3cret-operator";
    expect(checkOperator("wrong")).toBe(false);
    expect(checkOperator("s3cret-operatoR")).toBe(false);
  });

  it("rejects empty, null, and when the server has no password set", () => {
    process.env.CONSOLE_OPERATOR_PASSWORD = "s3cret-operator";
    expect(checkOperator("")).toBe(false);
    expect(checkOperator(null)).toBe(false);
    delete process.env.CONSOLE_OPERATOR_PASSWORD;
    expect(checkOperator("s3cret-operator")).toBe(false);
  });
});
