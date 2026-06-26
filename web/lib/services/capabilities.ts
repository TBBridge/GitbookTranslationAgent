import { jobV1Schema, type JobV1 } from "@/lib/schemas/job-v1";
import {
  workerCapabilitiesFixture,
  workerCapabilitiesV1Schema,
  type WorkerCapabilitiesV1
} from "@/lib/schemas/worker-v1";

export interface WorkerCandidate {
  id: string;
  name: string;
  online: boolean;
  capabilities: WorkerCapabilitiesV1;
}

export function findCompatibleWorkers(
  rawJob: unknown,
  workers: WorkerCandidate[]
) {
  const job = jobV1Schema.parse(rawJob);
  return workers.filter((worker) => isWorkerCompatible(job, worker));
}

export function isWorkerCompatible(job: JobV1, worker: WorkerCandidate) {
  if (!worker.online) {
    return false;
  }

  const capabilities = workerCapabilitiesV1Schema.parse(worker.capabilities);
  const dictionarySet = capabilities.dictionarySets[job.dictionarySet];
  if (!dictionarySet) {
    return false;
  }
  if (!job.languages.every((language) => dictionarySet.languages.includes(language))) {
    return false;
  }
  if (!capabilities.outputRoots.includes(job.outputRoot)) {
    return false;
  }
  if (!hasProviderRole(capabilities, job.translationProvider, "translate")) {
    return false;
  }
  if (
    job.reviewProvider &&
    !hasProviderRole(capabilities, job.reviewProvider, "review")
  ) {
    return false;
  }
  return true;
}

function hasProviderRole(
  capabilities: WorkerCapabilitiesV1,
  providerName: string,
  role: "translate" | "review"
) {
  return capabilities.providers.some(
    (provider) => provider.name === providerName && provider.roles.includes(role)
  );
}

export { workerCapabilitiesFixture as workerCapabilityFixture };
