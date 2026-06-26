import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { JobForm, type JobFormWorker } from "@/components/job-form";
import { workerCapabilitiesFixture } from "@/lib/schemas/worker-v1";

const workers: JobFormWorker[] = [
  {
    id: "w1",
    name: "office-mac",
    capabilities: workerCapabilitiesFixture()
  },
  {
    id: "w2",
    name: "gpu-box",
    capabilities: workerCapabilitiesFixture({
      workerName: "gpu-box",
      providers: [
        {
          name: "unavailable-model",
          provider: "ollama",
          model: "llama3",
          roles: ["translate"]
        }
      ]
    })
  }
];

describe("JobForm", () => {
  it("shows only capabilities from the selected worker", async () => {
    const user = userEvent.setup();
    render(<JobForm workers={workers} />);

    await user.selectOptions(screen.getByLabelText("Worker"), "office-mac");

    expect(screen.getByRole("option", { name: "qwen3" })).toBeVisible();
    expect(screen.queryByRole("option", { name: "unavailable-model" })).toBeNull();
  });

  it("requires typed confirmation for direct push", async () => {
    const user = userEvent.setup();
    render(<JobForm workers={workers} />);

    await user.selectOptions(screen.getByLabelText("Publish strategy"), "push_same_repo_direct");

    expect(screen.getByRole("button", { name: "Create job" })).toBeDisabled();

    await user.type(screen.getByLabelText("Type DIRECT PUSH to confirm"), "DIRECT PUSH");

    expect(screen.getByRole("button", { name: "Create job" })).toBeEnabled();
  });
});
