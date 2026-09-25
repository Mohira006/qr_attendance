#Requires -Version 5.1
<#
.SYNOPSIS
    One-command setup and launch for the Face ID Attendance System.

.DESCRIPTION
    Designed around the specific problems that came up getting this project running
    manually: it never depends on any externally-activated virtual environment (it
    creates and always calls its own, by full path, so a PyCharm terminal tab
    auto-activating the wrong project's venv can't affect it); it never depends on
    the shell's current directory (it locates itself via $PSScriptRoot, so it works
    the same whether you're sitting in the project root or somewhere else entirely);
    and it changes into backend/ specifically before running Alembic or the seed
    script, since the app's .env resolution is relative to the working directory.

.PARAMETER Reset
    Wipe and reseed the database even if one already exists.

.PARAMETER SetupOnly
    Install/configure everything but don't launch the servers.

.EXAMPLE
    .\setup.ps1
    Full setup (idempotent - safe to re-run) and launches both servers in new windows.

.EXAMPLE
    .\setup.ps1 -Reset
    Same, but wipes and reseeds the database first.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup.ps1
    Use this exact form if PowerShell refuses to run the script at all with a
    message about execution policies - this is a Windows default for scripts
    that arrived via a downloaded zip, not a problem with the script itself.
#>

param(
    [switch]$Reset,
    [switch]$SetupOnly
)

$ErrorActionPreference = "Stop"

function Write-Step($message) { Write-Host ""; Write-Host "==> $message" -ForegroundColor Cyan }
function Write-Info($message) { Write-Host "    $message" -ForegroundColor Gray }
function Write-Ok($message) { Write-Host "    $message" -ForegroundColor Green }
function Write-Failure($message) { Write-Host ""; Write-Host "ERROR: $message" -ForegroundColor Red }

# Always operate relative to this script's own location, never the shell's current
# directory - this is what makes it safe to run regardless of which folder you
# happened to `cd` into first.
$ProjectRoot = $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"
$FrontendPath = Join-Path $ProjectRoot "frontend"
$VenvPath = Join-Path $BackendPath ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$EnvPath = Join-Path $ProjectRoot ".env"
$DbPath = Join-Path $BackendPath "dev.db"

Write-Host "Face ID Attendance - Setup" -ForegroundColor White
Write-Info "Project root: $ProjectRoot"

# --- Sanity check: are we actually pointed at a real checkout of this project? ---
if (-not (Test-Path (Join-Path $BackendPath "app\main.py")) -or -not (Test-Path (Join-Path $FrontendPath "package.json"))) {
    Write-Failure "This doesn't look like the project root (missing backend\app\main.py or frontend\package.json)."
    Write-Info "Make sure setup.ps1 sits directly inside the folder that contains backend\ and frontend\."
    exit 1
}

# --- Step 1: Python virtual environment (always fresh-created here, never reused from elsewhere) ---
Write-Step "Checking Python virtual environment"
if (-not (Test-Path $VenvPython)) {
    Write-Info "Creating a new virtual environment at backend\.venv ..."
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        & py -3 -m venv $VenvPath
    } else {
        $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if (-not $PythonCmd) {
            Write-Failure "No Python installation found on PATH (neither 'py' nor 'python'). Install Python 3.10+ from python.org and re-run this script."
            exit 1
        }
        & python -m venv $VenvPath
    }
    if (-not (Test-Path $VenvPython)) {
        Write-Failure "Virtual environment creation appears to have failed - $VenvPython was not created."
        exit 1
    }
    Write-Ok "Created."
} else {
    Write-Ok "Already exists at backend\.venv - reusing it."
}

# --- Step 2: Backend dependencies ---
Write-Step "Installing backend dependencies"
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r (Join-Path $BackendPath "requirements-dev.txt") --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Failure "pip install failed - see output above."
    exit 1
}
Write-Ok "Backend dependencies installed."

# --- Step 3: .env (only created if missing - never overwrites an existing one) ---
Write-Step "Checking .env"
if (-not (Test-Path $EnvPath)) {
    Write-Info "Not found - creating one with SQLite defaults (no PostgreSQL server needed)."
    $AlphabetForSecrets = (48..57) + (97..122)
    $JwtSecret = -join ((1..40) | ForEach-Object { [char](Get-Random -InputObject $AlphabetForSecrets) })
    $DeviceKey = -join ((1..40) | ForEach-Object { [char](Get-Random -InputObject $AlphabetForSecrets) })
    @"
ENVIRONMENT=development
DATABASE_URL=sqlite+aiosqlite:///./dev.db
JWT_SECRET=$JwtSecret
FACE_DEVICE_API_KEY=$DeviceKey
COMPANY_NAME=Demo Company
COMPANY_TIMEZONE=Asia/Tashkent
STORAGE_PATH=./storage
FACE_RECOGNITION_PROVIDER=simulator
SIMULATOR_ENABLED=true
SEED_PASSWORD=Password123!
"@ | Set-Content -Path $EnvPath -Encoding utf8
    Write-Ok "Created $EnvPath"
} else {
    Write-Ok "Already exists - left untouched."
}

# --- Step 4: Database reset (only if -Reset was passed) ---
function Remove-ItemWithRetry($path, [switch]$recurse) {
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        try {
            if ($recurse) { Remove-Item $path -Recurse -Force -ErrorAction Stop }
            else { Remove-Item $path -Force -ErrorAction Stop }
            return $true
        } catch {
            if ($attempt -lt 5) { Start-Sleep -Seconds 1 }
        }
    }
    return $false
}

if ($Reset -and (Test-Path $DbPath)) {
    Write-Step "Resetting database (-Reset was specified)"

    # dev.db can be locked by a still-running backend server from an earlier
    # session (Windows refuses to delete an open file, unlike Linux) - stop any
    # python.exe process using THIS specific venv first, so -Reset doesn't
    # require manually closing windows every time.
    try {
        $LockingProcesses = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
            try { $_.Path -eq $VenvPython } catch { $false }
        }
        if ($LockingProcesses) {
            Write-Info "Stopping a running backend process that's using this environment..."
            $LockingProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
            # Windows doesn't always release the file handle the instant the
            # process dies - the retry loop below adds more time on top of this,
            # but this initial wait covers the common case without any retries needed.
            Start-Sleep -Seconds 2
        }
    } catch {
        # Best-effort only - fall through to the delete attempt below, which
        # gives a clear message if something is still holding the file.
    }

    if (-not (Remove-ItemWithRetry $DbPath)) {
        Write-Failure "Couldn't delete dev.db after several attempts - something other than a plain backend terminal has it open."
        Write-Info "Likely culprits: PyCharm's Database tool window (if dev.db was ever opened there), or a python.exe process this script couldn't identify."
        Write-Info "Close PyCharm entirely, end any python.exe processes in Task Manager, then try -Reset again."
        exit 1
    }

    $StoragePath = Join-Path $BackendPath "storage"
    if (Test-Path $StoragePath) {
        if (-not (Remove-ItemWithRetry $StoragePath -recurse)) {
            Write-Failure "Couldn't delete the storage folder after several attempts - the same file-lock issue as above."
            Write-Info "Close PyCharm entirely, end any python.exe processes in Task Manager, then try -Reset again."
            exit 1
        }
    }
    Write-Ok "Removed existing dev.db and storage\."
}

# --- Step 5: Migrations and seeding (both need CWD = backend\, since .env resolution is relative to it) ---
Write-Step "Running database migrations"
Push-Location $BackendPath
try {
    & $VenvPython -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Failure "Alembic migration failed - see output above."
        exit 1
    }
    Write-Ok "Migrations applied."

    if ($Reset -or -not (Test-Path $DbPath)) {
        Write-Step "Seeding demo data"
        & $VenvPython -m scripts.seed
        if ($LASTEXITCODE -ne 0) {
            Write-Failure "Seed script failed - see output above."
            exit 1
        }
        Write-Ok "Seed complete."
    } else {
        Write-Step "Database already has data"
        Write-Info "Skipping seed. Re-run with -Reset to wipe and reseed."
    }
} finally {
    Pop-Location
}

# --- Step 6: Frontend dependencies (re-installs if package.json changed since the last install, not just if node_modules is missing entirely) ---
Write-Step "Checking frontend dependencies"
$NodeModulesPath = Join-Path $FrontendPath "node_modules"
$PackageJsonPath = Join-Path $FrontendPath "package.json"
$NeedsNpmInstall = $true
if (Test-Path $NodeModulesPath) {
    $NeedsNpmInstall = (Get-Item $PackageJsonPath).LastWriteTime -gt (Get-Item $NodeModulesPath).LastWriteTime
}
if ($NeedsNpmInstall) {
    $NpmCmd = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $NpmCmd) {
        Write-Failure "npm was not found on PATH. Install Node.js from nodejs.org and re-run this script."
        exit 1
    }
    Write-Info "Installing (or updating) frontend packages - this can take a minute..."
    Push-Location $FrontendPath
    try {
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Failure "npm install failed - see output above."
            exit 1
        }
    } finally {
        Pop-Location
    }
    Write-Ok "Frontend dependencies installed."
} else {
    Write-Ok "Already up to date."
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green

if ($SetupOnly) {
    Write-Info "Run without -SetupOnly to also launch both servers, or start them yourself:"
    Write-Info "  Backend:  cd backend; & '$VenvPython' -m uvicorn app.main:app --reload"
    Write-Info "  Frontend: cd frontend; npm run dev"
    exit 0
}

# --- Step 7: Launch both servers, each in its own new window ---
Write-Step "Starting both servers"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$BackendPath'; & '$VenvPython' -m uvicorn app.main:app --reload"
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$FrontendPath'; npm run dev"

Write-Host ""
Write-Host "Both servers are starting in new windows." -ForegroundColor Green
Write-Host "  Backend docs: http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host "  Frontend app: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "HR login: hr@company.com / Password123!" -ForegroundColor Gray
