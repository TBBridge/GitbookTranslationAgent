import { z } from "zod";

import { languageTagSchema, safeNameSchema } from "@/lib/schemas/job-v1";

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
