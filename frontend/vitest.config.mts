// Tests unitarios del frontend (Fase 5I): lógica pura de `lib/`, sin navegador.
// Lo que exige un navegador real lo cubren las e2e de `frontend/e2e/`.
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: { alias: { "@": fileURLToPath(new URL("./", import.meta.url)) } },
  test: { include: ["tests/**/*.test.ts"], environment: "node" },
});
