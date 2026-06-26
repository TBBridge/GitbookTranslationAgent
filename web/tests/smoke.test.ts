import { describe, expect, it } from "vitest";

import { APP_NAME } from "@/lib/constants";

describe("application", () => {
  it("has the configured product name", () => {
    expect(APP_NAME).toBe("GitBook Translation Control");
  });
});
