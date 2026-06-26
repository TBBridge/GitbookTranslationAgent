import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { JobProgress } from "@/components/job-progress";

describe("JobProgress", () => {
  it("shows the current state and latest log entry", () => {
    render(
      <JobProgress
        job={{ state: "running", cancelRequested: false }}
        logs={[
          {
            id: 1,
            message: "Translating docs/index.md",
            stage: "translate"
          }
        ]}
      />
    );

    expect(screen.getByText("running")).toBeVisible();
    expect(screen.getByText("Translating docs/index.md")).toBeVisible();
  });
});
