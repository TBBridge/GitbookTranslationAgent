import { describe, expect, it } from "vitest";

import { validJobFixture } from "@/lib/schemas/job-v1";
import {
  findCompatibleWorkers,
  workerCapabilityFixture,
  type WorkerCandidate
} from "@/lib/services/capabilities";

describe("capability matching", () => {
  it("requires one online worker to advertise every selected capability", () => {
    const workers: WorkerCandidate[] = [
      {
        id: "w1",
        name: "office-mac",
        online: true,
        capabilities: workerCapabilityFixture({
          dictionarySets: { default: { languages: ["en", "zh-CN"] } }
        })
      },
      {
        id: "w2",
        name: "offline",
        online: false,
        capabilities: workerCapabilityFixture()
      }
    ];

    const compatible = findCompatibleWorkers(
      validJobFixture({ languages: ["en", "zh-CN"] }),
      workers
    );

    expect(compatible.map((worker) => worker.name)).toEqual(["office-mac"]);
  });

  it("rejects workers missing a requested language", () => {
    const compatible = findCompatibleWorkers(validJobFixture({ languages: ["zh-CN"] }), [
      {
        id: "w1",
        name: "english-only",
        online: true,
        capabilities: workerCapabilityFixture({
          dictionarySets: { default: { languages: ["en"] } }
        })
      }
    ]);

    expect(compatible).toEqual([]);
  });
});
