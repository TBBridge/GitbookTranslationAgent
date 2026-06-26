import { z } from "zod";

export const safeNameSchema = z
  .string()
  .min(1)
  .regex(/^[A-Za-z0-9][A-Za-z0-9_-]*$/, "must be a capability name");

export const languageTagSchema = z
  .string()
  .min(1)
  .regex(/^[a-z]{2,3}(?:-[A-Z]{2})?$/, "must be a BCP-47-like language tag");

export const branchSchema = z
  .string()
  .min(1)
  .refine((branch) => !branch.startsWith("/") && !branch.endsWith("/"), {
    message: "branch must not start or end with slash"
  })
  .refine((branch) => !branch.includes("..") && !branch.includes("//"), {
    message: "branch contains an unsafe path segment"
  })
  .refine((branch) => !branch.includes("@{"), {
    message: "branch contains an unsafe ref sequence"
  });

export const targetPathSchema = z
  .string()
  .min(1)
  .refine((path) => !path.startsWith("/") && !path.includes(".."), {
    message: "target paths must be repository-relative patterns"
  });

export const jobV1Schema = z
  .object({
    schemaVersion: z.literal(1).default(1),
    repoUrl: z
      .string()
      .url()
      .refine((url) => new URL(url).protocol === "https:", {
        message: "repoUrl must be HTTPS"
      }),
    branch: branchSchema.default("main"),
    targetPaths: z.array(targetPathSchema).min(1),
    languages: z.array(languageTagSchema).min(1),
    dictionarySet: safeNameSchema,
    outputRoot: safeNameSchema,
    cacheRoot: safeNameSchema.optional(),
    translationProvider: safeNameSchema,
    reviewProvider: safeNameSchema.nullable().optional(),
    pushStrategy: z
      .enum(["none", "push_same_repo_direct", "push_same_repo_new_branch"])
      .default("none"),
    confirmDirectPush: z.boolean().default(false),
    limits: z
      .object({
        maxFiles: z.number().int().positive().max(1000).optional(),
        maxBytesPerFile: z.number().int().positive().max(1_000_000).optional()
      })
      .strict()
      .optional()
  })
  .strict()
  .superRefine((value, context) => {
    if (
      value.pushStrategy === "push_same_repo_direct" &&
      !value.confirmDirectPush
    ) {
      context.addIssue({
        code: "custom",
        path: ["confirmDirectPush"],
        message: "direct push requires typed confirmation"
      });
    }
  });

export type JobV1 = z.infer<typeof jobV1Schema>;

export function validJobFixture(overrides: Partial<JobV1> = {}) {
  return jobV1Schema.parse({
    schemaVersion: 1,
    repoUrl: "https://github.com/acme/docs",
    branch: "main",
    targetPaths: ["docs/**/*.md"],
    languages: ["en"],
    dictionarySet: "default",
    outputRoot: "default",
    translationProvider: "ollama-local",
    reviewProvider: null,
    pushStrategy: "none",
    confirmDirectPush: false,
    ...overrides
  });
}
