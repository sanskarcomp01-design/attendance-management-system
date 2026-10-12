import fs from "node:fs";
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const certificatePath = path.resolve("certs/attendance-local.pfx");
const certificatePasswordPath = path.resolve("certs/attendance-local-password.txt");

export default defineConfig({
  plugins: [react()],
  server: {
    https: process.env.AMS_LOCAL_HTTPS === "1"
      ? {
          pfx: fs.readFileSync(certificatePath),
          passphrase: fs.readFileSync(certificatePasswordPath, "utf8").trim(),
        }
      : undefined,
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
    },
  },
});
