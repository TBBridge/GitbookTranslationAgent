import { verify } from "@node-rs/argon2";

export async function verifyAdminPassword(
  password: unknown,
  passwordHash = process.env.ADMIN_PASSWORD_HASH
) {
  if (typeof password !== "string" || password.length === 0) {
    return false;
  }
  if (!passwordHash) {
    throw new Error("ADMIN_PASSWORD_HASH is required");
  }

  try {
    return await verify(passwordHash, password);
  } catch {
    return false;
  }
}
