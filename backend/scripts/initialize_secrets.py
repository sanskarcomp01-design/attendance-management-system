"""Fill missing or known-demo secrets in the root .env without displaying them."""

import secrets
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"
SECRET_KEYS = ("SECRET_KEY", "JWT_SECRET_KEY")
PASSWORD_KEYS = (
    "SEED_ADMIN_PASSWORD",
    "SEED_TEACHER_PASSWORD",
    "SEED_TEACHER2_PASSWORD",
    "SEED_STUDENT_PASSWORD",
    "SEED_STUDENT2_PASSWORD",
    "SEED_STUDENT3_PASSWORD",
    "SEED_STUDENT4_PASSWORD",
)
KNOWN_WEAK_VALUES = {
    "change-this-to-a-long-random-string",
    "change-this-to-another-long-random-string",
    "Admin@12345",
    "Teacher@12345",
    "Student@12345",
}


def main():
    if not ENV_FILE.exists():
        raise SystemExit("Missing root .env. Copy .env.example to .env first.")

    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    keys = SECRET_KEYS + PASSWORD_KEYS
    values = {}
    for line in lines:
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key in keys:
            values[key] = value.strip().strip("\"").strip("'")

    replacements = {}
    password_values = [values.get(key, "") for key in PASSWORD_KEYS]
    secret_values = [values.get(key, "") for key in SECRET_KEYS]
    for key in keys:
        current = values.get(key, "")
        too_short = len(current) < (32 if key in SECRET_KEYS else 16)
        duplicated_password = key in PASSWORD_KEYS and password_values.count(current) > 1
        duplicated_secret = key in SECRET_KEYS and secret_values.count(current) > 1
        if too_short or current in KNOWN_WEAK_VALUES or duplicated_password or duplicated_secret:
            replacements[key] = secrets.token_urlsafe(36)

    if not replacements:
        print("Existing non-placeholder secrets were preserved.")
        return

    updated = []
    written = set()
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key, _value = line.split("=", 1)
            if key in replacements:
                updated.append(f"{key}={replacements[key]}")
                written.add(key)
                continue
        updated.append(line)
    for key in keys:
        if key in replacements and key not in written:
            updated.append(f"{key}={replacements[key]}")

    ENV_FILE.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print("Generated/replaced: " + ", ".join(replacements))


if __name__ == "__main__":
    main()
