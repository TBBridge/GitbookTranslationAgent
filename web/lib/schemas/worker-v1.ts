import { z } from "zod";

import { jobV1Schema, languageTagSchema, safeNameSchema } from "@/lib/schemas/job-v1";

export const providerRoleSchema = z.enum(["translate", "review"]);

export const workerCapabilitiesV1Schema = z
  .object({
    schemaVersion: z.literal(1).default(1),
    workerName: z.string().min(1),
    dictionarySets: z.record(
      safeNameSchema,
      z
        .object({
          languages: z.array(languageTagSchema).default([])
        })
        .strict()
    ),
    outputRoots: z.array(safeNameSchema).default([]),
    providers: z
      .array(
        z
          .object({
            name: safeNameSchema,
            provider: z.string().min(1),
            model: z.string().min(1),
            roles: z.array(providerRoleSchema).min(1)
          })
          .strict()
      )
      .default([])
  })
  .strict()
  .superRefine((capabilities, context) => {
    const serialized = JSON.stringify(capabilities);
    if (/\/Users\/|[A-Za-z]:\\|(?:^|")\//.test(serialized)) {
      context.addIssue({
        code: "custom",
        message: "capabilities must not expose local paths"
      });
    }
  });

export type WorkerCapabilitiesV1 = z.infer<typeof workerCapabilitiesV1Schema>;

export const workerRegisterRequestSchema = z
  .object({
    schemaVersion: z.literal(1),
    capabilities: workerCapabilitiesV1Schema
  })
  .strict();

export const workerClaimResponseSchema = z
  .object({
    job: z
      .object({
        jobId: z.string().min(1),
        leaseId: z.string().min(1),
        leaseExpiresAt: z.string().min(1),
        config: jobV1Schema
      })
      .nullable()
      .optional()
  })
  .strict();

export const progressEventSchema = z
  .object({
    kind: z.string().min(1),
    stage: z.string().min(1),
    message: z.string().nullable().optional(),
    current: z.number().int().nonnegative().nullable().optional(),
    total: z.number().int().nonnegative().nullable().optional(),
    filePath: z.string().nullable().optional(),
    language: z.string().nullable().optional()
  })
  .strict();

export const workerUpdatesRequestSchema = z
  .object({
    schemaVersion: z.literal(1),
    leaseId: z.string().min(1),
    firstSequence: z.number().int().positive(),
    updates: z.array(progressEventSchema).min(1)
  })
  .strict();

export const pipelineResultSchema = z
  .object({
    status: z.enum(["succeeded", "partial", "failed", "cancelled"]),
    results: z.array(z.unknown()).default([]),
    issues: z.array(z.unknown()).default([])
  })
  .passthrough();

export const workerCompleteRequestSchema = z
  .object({
    schemaVersion: z.literal(1),
    leaseId: z.string().min(1),
    lastSequence: z.number().int().nonnegative().nullable().optional(),
    result: pipelineResultSchema
  })
  .strict();

export function workerCapabilitiesFixture(
  overrides: Partial<WorkerCapabilitiesV1> = {}
) {
  return workerCapabilitiesV1Schema.parse({
    schemaVersion: 1,
    workerName: "office-mac",
    dictionarySets: {
      default: {
        languages: ["en"]
      }
    },
    outputRoots: ["default"],
    providers: [
      {
        name: "ollama-local",
        provider: "ollama",
        model: "qwen3",
        roles: ["translate", "review"]
      }
    ],
    ...overrides
  });
}
