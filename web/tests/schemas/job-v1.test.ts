import { describe, expect, it } from "vitest";

import { jobV1Schema, validJobFixture } from "@/lib/schemas/job-v1";

describe("job v1 schema", () => {
  it("accepts zh-CN as a language tag", () => {
    const config = jobV1Schema.parse(validJobFixture({ languages: ["zh-CN"] }));

    expect(config.languages).toEqual(["zh-CN"]);
  });

  it("rejects arbitrary local output paths", () => {
    expect(() =>
      jobV1Schema.parse(validJobFixture({ outputRoot: "/tmp/output" }))
    ).toThrow();
  });

  it("requires typed confirmation for direct push", () => {
    expect(() =>
      jobV1Schema.parse(
        validJobFixture({
          pushStrategy: "push_same_repo_direct",
          confirmDirectPush: false
        })
      )
    ).toThrow();
  });
});
