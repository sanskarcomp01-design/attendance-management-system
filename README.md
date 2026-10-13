# AI-Powered Attendance Management System

Community Engagement Project (CEP) for Second Year Information Technology, academic year **2026–2027**.

- **College:** S. B. Patil College of Engineering, Vangali, Indapur, Pune, Maharashtra
- **University:** Savitribai Phule Pune University (SPPU)
- **Goal:** Record attendance with a **time-limited QR code** plus **AI face verification** so another student cannot easily mark a proxy.

This project is written for beginners and continues the existing React + Flask application in this folder.

## What you get

- A **React** website (login and dashboards for admin, teacher, and student)
- A **Flask** REST API (Python)
- A **SQLite** database file created automatically
- Rotating QR codes for live class sessions
- Face enrollment and matching with OpenCV **YuNet** (detect) and **SFace** (recognize)
- Backend tests with **pytest**
- Browser tests with **Playwright**

## Roles

**Administrator**

- Log in
- Create, view, edit, and deactivate student and teacher accounts
- Manage classes, subjects, and enrollments
- View attendance reports (including CSV download) and audit logs

**Teacher**

- Log in
- See assigned subjects
- Start a live QR attendance session
- Watch the roster fill in as students verify
- Manually mark present/absent with a written reason (camera or QR failure)
- Close the session and open reports
- Download a CSV report with SPPU-style 75% eligibility
- Review present counts by QR + face or manual method, and open session rosters

**Student**

- Log in
- Enroll a face photo once
- Scan the teacher QR and follow a one-time randomized head-turn prompt using the live camera
- See personal subject-wise and overall attendance percentages
- Review their profile and change their password

## Tools you need on Windows

1. **Python 3.13**
2. **Node.js LTS** (needed for the React website)
3. Internet access for installing dependencies and downloading the two face models
4. A camera for face enrollment and QR scanning (needed only for the live camera workflow)

If `node` is not recognized in a new terminal, close and reopen the terminal after installing Node.js.

## Folder map (simple)

```
attendance management system/
  .env.example          # template of settings (no real secrets)
  .env                  # your local settings (do not share)
  README.md
  backend/              # Python API
    app/                # Flask application code
    tests/              # pytest tests
    scripts/            # download face models
    run.py              # start the API
    seed.py             # create demo users and SE-IT subjects
    requirements.txt
  frontend/             # React + Vite website
    src/pages/          # screens
    src/components/     # layout
    e2e/                # Playwright tests
```

## Installation (first time)

Open **PowerShell** in this project folder. These steps keep the existing SQLite database and its records.

### 1. Create settings and unique local credentials

```powershell
copy .env.example .env
python backend\scripts\initialize_secrets.py
```

The script writes distinct random API signing keys and seven unique seed passwords directly into `.env`. It prints only the names of the values it generated, never the values themselves. If Windows reports that script execution is disabled, this initializer can still be run with the `python ...` command above. Keep `.env` private and do not commit it. The Flask app refuses to start if its signing keys are missing, too short, or reused.

### 2. Python virtual environment and packages

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts\download_models.py
python seed.py
```

`download_models.py` saves two `.onnx` files in `backend/models/`. They are required for face matching. Internet is needed once. Seed account passwords are distinct and stored only in the root `.env`; do not copy them into reports or screenshots. To intentionally reset the existing seeded accounts from the current `.env` values, run `python seed.py --reset-seed-passwords`.

### 3. Node packages

Open a **second** PowerShell window:

```powershell
cd frontend
npm install
npx playwright install chromium
```

## Everyday commands

**Start the API** (keep this window open):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python run.py
```

The API is at `http://127.0.0.1:5000`. Check `http://127.0.0.1:5000/api/health`.
The health response includes `face_models_ready`; QR generation/scanning can work without face models, but attendance verification and enrollment require them.
Attendance requires two fresh camera frames that pass both face matching and the server-checked head-turn prompt. This basic liveness check makes static-photo replay harder; it is not a substitute for a dedicated anti-spoofing system in high-assurance deployments.

**Start the website on this computer** (second window):

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`.

Vite forwards `/api` calls to Flask, so you normally use only the website URL.
Teacher sign-in link on this computer: [http://localhost:5173/login](http://localhost:5173/login). After signing in, the teacher portal opens; use **Open session** to display its roster and QR page.

**Reopen the presentation after closing it:** double-click `start-presentation.bat` in the project folder. It opens separate backend and HTTPS website windows. Keep both windows open while presenting. Use the HTTPS link printed in the website window on your phone; if your laptop's network address changed, use the new printed link. If you close either server window, run `start-presentation.bat` again.

**Present from multiple devices on the same Wi-Fi with mobile camera support:** start the API as above, then double-click `start-frontend.bat`. It creates a local HTTPS certificate, trusts its root certificate for this Windows user, and prints the current presentation link, certificate-file path, and SHA-256 fingerprint. Copy `frontend/certs/attendance-local-root.cer` to each phone over USB or another trusted channel; install it as a CA certificate/profile and enable full trust if the phone asks. Verify its fingerprint against the value printed in the startup window. Then open `https://<laptop-ip>:5173/login`. Keep the phone and laptop on the same hotspot/Wi-Fi, and keep both server windows running. The laptop IP or its certificate may change after reconnecting to a different network; rerun the launcher and install the new root certificate if it generated a replacement. Only trust this private project certificate. If Windows Firewall blocks the connection, allow Node.js only on a trusted **Private** network; do not expose ports on public Wi-Fi or forward them from your router to the internet.

On Android, install the downloaded certificate from **Settings → Security/Privacy → Encryption & credentials → Install a certificate → CA certificate** (menu wording varies); Android may display a warning because this is a locally generated CA. On iPhone, open the downloaded profile, install it in **Settings → Profile Downloaded**, then enable it under **Settings → General → About → Certificate Trust Settings**. If a device cannot trust a locally installed CA, do not bypass certificate warnings or use that device for camera verification; use a publicly trusted HTTPS deployment instead.

## Deploy to Render

The repository includes a Render Blueprint (`render.yaml`) for a public HTTPS website and its Flask API. To launch it:

1. Sign in to [Render](https://render.com), select **New → Blueprint**, and connect this GitHub repository.
2. Review the services and costs before confirming. The API uses a paid instance and a 1 GB persistent disk so attendance records survive restarts and deploys; Render's free instances do not provide persistent disks.
3. Wait for both services to finish deploying. Open the `attendance-web` URL to use the website, and check `https://<attendance-api-host>/api/health` for API status and `face_models_ready`.
4. The first API deployment creates separate sample accounts and class data in the hosted database. Find each initial password in the API service's environment variables (`SEED_ADMIN_PASSWORD`, `SEED_TEACHER_PASSWORD`, or `SEED_STUDENT_PASSWORD`) and change it after signing in. Do not share these credentials publicly.

This is a new hosted database: the local `backend/attendance.db`, `.env`, uploads, and other local files are not uploaded, modified, or deleted. Local records are not available on the hosted website unless you separately arrange a secure data migration. The hosted instance stores its database on the persistent disk; keep independent backups before using it for important records.

The deployment downloads the face-recognition model files during its build. This academic demo has not been hardened or privacy-reviewed for real student biometric data; obtain institutional approval and informed consent before collecting real students' data online.

## Seed account names

The seed command creates these accounts and several additional sample classroom users:

| Role | Email |
|------|-------|
| Admin | admin@sbpcoe.edu |
| Teacher | teacher@sbpcoe.edu |
| Student | student@sbpcoe.edu |

The corresponding passwords are generated into `.env` and are not printed by the seed command. Share credentials only through a private channel. The sample SE-IT-A class and subjects are created by `python seed.py`.

## Classroom demo flow

1. Sign in as **admin** and confirm users/subjects.
2. Sign in as **student** → **Enroll face** → capture one clear selfie.
3. Sign in as **teacher** → **Start QR session** on a projector.
4. On the student phone/laptop → **Scan QR** → live selfie → attendance becomes **present**.
5. Teacher sees the roster update. If a phone fails, the teacher can mark **Present** or **Absent** and type a reason (this is written to the audit log).
6. Admin/teacher can open **Reports**, print, or **Download CSV**. Students below 75% are highlighted as not eligible.

Use two browsers or one normal window plus one private window if you test teacher and student on the same PC.

## Tests

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

The automated backend suite uses mocked face-service results for face enrollment and match outcomes; it does not prove real camera/model accuracy. It covers QR time-window expiry, duplicate attendance, authorization, reporting, and class/subject edits.
The student's overall percentage is weighted by sessions held across all enrolled subjects (`total present / total sessions`); both QR + face and manual present records count as present.

Frontend end-to-end (website should be startable; Playwright can start Vite itself):

```powershell
cd frontend
npx playwright test
```

Install Playwright's Chromium browser once with `npx playwright install chromium`. The login error test expects the Flask API to be running. Start `python run.py` first for a full pass.

## Debugging (plain language)

| Problem | What to try |
|---------|-------------|
| Website says it cannot reach the server | Start `python run.py` in `backend`. Confirm `/api/health` opens. |
| `node` / `npm` not recognized | Install Node.js LTS, then open a **new** terminal. |
| Face enrollment: “models are missing” | Run `python scripts\download_models.py` from `backend`. |
| Flask reports missing signing keys | From the project root run `python backend\scripts\initialize_secrets.py`, then restart Flask. |
| Seed asks for passwords | Run the same secret initializer, then `python seed.py` from `backend`. |
| “No face found” | Better light, one person, look at the camera, remove mask. |
| QR expired | The code rotates. Scan the code currently on the teacher screen. |
| Proxy blocked / face did not match | The selfie does not match the enrolled student. Re-enroll if the first photo was poor. |
| Database is empty | Run `python seed.py` again. It will not duplicate emails. |
| Port 5000 or 5173 already used | Close the old window that is running the app. |
| PowerShell blocks venv activate | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

Logs: the API prints errors in the backend terminal. Audit events are on the admin **Audit log** page.

## Security notes (for the CEP report)

- Passwords are stored as hashes (Werkzeug), not plain text.
- Login is rate-limited.
- Roles are checked on every protected API route (JWT claims + active user).
- QR tokens are HMAC-signed and accepted in their current or immediately previous time bucket; future and older QR windows are rejected.
- Face matching uses a cosine threshold (see `FACE_MATCH_THRESHOLD` in `.env`); the backend tests simulate successful and failed match responses and do not measure the recognition model's false acceptance/rejection rate.
- Manual attendance changes require a written reason and appear in the admin audit log.
- Deactivated users cannot log in.
- `.env` must stay off Git (see `.gitignore`).
- This is a **college lab system**, not a production biometric product. For a real college deployment you would add HTTPS, a stronger database, hardware key storage, and a formal privacy notice for student photos. Photos are converted to numeric embeddings; raw images are not kept in the database.

## Compatibility chosen for this PC

- Python **3.13** with pinned packages in `backend/requirements.txt`
- Face stack: **OpenCV 4.12** YuNet + SFace ONNX (works on Windows; avoids `dlib`, which is painful on Python 3.13)
- Frontend: React 19, Vite 7, `html5-qrcode` 2.3.8
- Node.js LTS is required for Vite and Playwright

If a package fails to install, copy the full error text, then try `pip install -r requirements.txt` again after upgrading pip.

## What is not built yet

These items are still incomplete. Do not treat them as working features:

- No email/SMS reminders or forgot-password flow.
- Face matching verifies a captured image against a stored embedding; it does not perform anti-spoofing or liveness detection.
- Browser tests do not automate the full QR/camera classroom flow. Real camera, lighting, phone/browser permission, and model behavior still require an in-person classroom test.
- This is a local academic project, not a production service: there is no deployment hardening, account recovery, biometric consent workflow, or secure remote hosting configuration.
- Login rate-limit counters are kept in process memory; use a shared persistent limiter store before running multiple API instances.
- Password changes do not revoke other already-issued JWTs immediately; tokens expire after the configured eight-hour lifetime.
