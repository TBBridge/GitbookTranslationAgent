import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  workerClaimResponseSchema,
  workerCompleteRequestSchema,
  workerRegisterRequestSchema,
  workerUpdatesRequestSchema
} from "@/lib/schemas/worker-v1";

const CONTRACT_SCHEMAS = {
  register: workerRegisterRequestSchema,
  claim: workerClaimResponseSchema,
  updates: workerUpdatesRequestSchema,
  complete: workerCompleteRequestSchema
};

describe("worker api v1 contract", () => {
  it.each(["register", "claim", "updates", "complete"] as const)(
    "%s fixture parses with the web schema",
    async (name) => {
      const payload = JSON.parse(
        await readFile(
          join(process.cwd(), "..", "contracts", "worker-api-v1", `${name}.json`),
          "utf8"
        )
      );

      expect(CONTRACT_SCHEMAS[name].safeParse(payload).success).toBe(true);
    }
  );
});
