import { expect, test } from "vitest";
import { parseAmount } from "../src/parse";

test("parses currency to cents", () => {
  expect(parseAmount("$1,234.50")).toBe(123450);
});
