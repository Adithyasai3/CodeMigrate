import { defineConfig } from '@playwright/test'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..')
// cmd.exe can't run "../x" paths, so the interpreter is given as a quoted absolute path
const python = JSON.stringify(
  process.env.PYTHON ??
    path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python'),
)

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  use: { baseURL: 'http://localhost:5173', trace: 'retain-on-failure' },
  webServer: [
    {
      command: `${python} -m uvicorn codemigrate.api.main:app --port 8000`,
      cwd: root,
      url: 'http://localhost:8000/api/health',
      reuseExistingServer: true,
      timeout: 120_000,
      env: { DATABASE_URL: 'sqlite:///./e2e.db', JWT_SECRET: 'e2e-secret-0123456789abcdef0123456789' },
    },
    { command: 'npm run dev', url: 'http://localhost:5173', reuseExistingServer: true, timeout: 120_000 },
  ],
})
