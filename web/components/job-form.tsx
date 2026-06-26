"use client";

import { useMemo, useState } from "react";

import type { WorkerCapabilitiesV1 } from "@/lib/schemas/worker-v1";

export interface JobFormWorker {
  id: string;
  name: string;
  capabilities: WorkerCapabilitiesV1;
}

export function JobForm({ workers }: { workers: JobFormWorker[] }) {
  const [workerName, setWorkerName] = useState(workers[0]?.name ?? "");
  const [publishStrategy, setPublishStrategy] = useState("none");
  const [confirmation, setConfirmation] = useState("");
  const selectedWorker = useMemo(
    () => workers.find((worker) => worker.name === workerName) ?? workers[0],
    [workerName, workers]
  );
  const providers = selectedWorker?.capabilities.providers ?? [];
  const dictionaries = Object.keys(selectedWorker?.capabilities.dictionarySets ?? {});
  const outputRoots = selectedWorker?.capabilities.outputRoots ?? [];
  const directPushNeedsConfirmation =
    publishStrategy === "push_same_repo_direct" && confirmation !== "DIRECT PUSH";

  return (
    <form className="panel form-grid">
      <label>
        Worker
        <select
          value={workerName}
          onChange={(event) => setWorkerName(event.target.value)}
        >
          {workers.map((worker) => (
            <option key={worker.id} value={worker.name}>
              {worker.name}
            </option>
          ))}
        </select>
      </label>

      <label>
        Repository URL
        <input name="repoUrl" type="url" placeholder="https://github.com/acme/docs" />
      </label>

      <label>
        Target paths
        <input name="targetPaths" placeholder="docs/**/*.md" />
      </label>

      <label>
        Languages
        <input name="languages" placeholder="en, zh-CN" />
      </label>

      <label>
        Dictionary
        <select name="dictionarySet">
          {dictionaries.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>

      <label>
        Output root
        <select name="outputRoot">
          {outputRoots.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>

      <label>
        Translation provider
        <select name="translationProvider">
          {providers
            .filter((provider) => provider.roles.includes("translate"))
            .map((provider) => (
              <option key={provider.name} value={provider.name}>
                {provider.model}
              </option>
            ))}
        </select>
      </label>

      <label>
        Publish strategy
        <select
          name="pushStrategy"
          value={publishStrategy}
          onChange={(event) => setPublishStrategy(event.target.value)}
        >
          <option value="none">Local output only</option>
          <option value="push_same_repo_new_branch">Push new branch</option>
          <option value="push_same_repo_direct">Direct push</option>
        </select>
      </label>

      {publishStrategy === "push_same_repo_direct" ? (
        <label>
          Type DIRECT PUSH to confirm
          <input
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
          />
        </label>
      ) : null}

      <button type="submit" disabled={directPushNeedsConfirmation || !selectedWorker}>
        Create job
      </button>
    </form>
  );
}
