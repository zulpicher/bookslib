# BooksLib - DevSecOps CI/CD Pipeline
**Track A | Technical Test - DevSecOps Internship**

> Repository: https://github.com/zulpicher/bookslib  
> Candidate: Zulpicher  
> Date: June 2026

---

## Daftar Isi
- [Arsitektur & Workflow](#arsitektur--workflow)
- [Stack Aplikasi](#stack-aplikasi)
- [Git Flow Strategy](#git-flow-strategy)
- [Security Tools yang Digunakan](#security-tools-yang-digunakan)
- [Langkah Reproduksi](#langkah-reproduksi)
- [Trade-off & Justifikasi Pemilihan Tools](#trade-off--justifikasi-pemilihan-tools)
- [Kendala & Perbaikan ke Depan](#kendala--perbaikan-ke-depan)
- [Security Findings](#security-findings)

---

## Arsitektur & Workflow
Developer
│
├── git push → feature/* branch
│ │
│ Pull Request
│ │
│ develop branch ──────────────────────────────────┐
│ │ │
│ Jenkins Multibranch Pipeline (Triggered) │
│ │ │
│ ┌─────────▼──────────┐ │
│ │ 1. Checkout SCM │ │
│ └─────────┬──────────┘ │
│ ┌─────────▼──────────────────┐ │
│ │ 2. Secret Scanning │ ← Gitleaks │
│ │ (BLOCK if leaked) │ │
│ └─────────┬──────────────────┘ │
│ ┌─────────▼──────────────────┐ │
│ │ 3. SAST Analysis │ ← Semgrep │
│ │ (WARN if ERROR found) │ │
│ └─────────┬──────────────────┘ │
│ ┌─────────▼──────────────────┐ │
│ │ 4. Dependency Scan │ ← pip-audit │
│ │ (Parallel) │ npm audit │
│ │ │ govulncheck │
│ └─────────┬──────────────────┘ │
│ ┌─────────▼──────────────────┐ │
│ │ 5. Build Docker Images │ ← Multi-stage build │
│ │ (4 services) │ │
│ └─────────┬──────────────────┘ │
│ ┌─────────▼──────────────────┐ │
│ │ 6. Image Scan │ ← Trivy │
│ │ (WARN if CRITICAL CVE) │ │
│ └─────────┬──────────────────┘ │
│ ┌─────────▼──────────────────┐ │
│ │ 7. Push to Docker Hub │ │
│ └─────────┬──────────────────┘ │
│ ┌─────────▼──────────────────┐ │
│ │ 8. Deploy Staging │ ← docker-compose │
│ │ (develop branch only) │ │
│ └────────────────────────────┘ │
│ │
└── merge develop → main ───────────────────────────────────────┤
Jenkins Pipeline (main) │
│ │
└── Deploy Production ──────────┘
(docker-compose.prod.yml)
Security Finding → Auto GitHub Issue (via REST API)
---

## Stack Aplikasi

| Service | Technology | Port | Keterangan |
|---|---|---|---|
| **frontend** | React 18 + Vite + Nginx | 3000 | SPA, di-serve via nginx:alpine |
| **auth-service** | Go 1.20 | 8081 | JWT authentication |
| **books-service** | .NET 8 (ASP.NET Core) | 8082 | CRUD buku |
| **reviews-service** | Python 3.10 / Django 4.2 | 8083 | Review & rating |
| **db** | PostgreSQL 15 Alpine | 5432 | Shared database, 3 DB terpisah |

---

## Git Flow Strategy
main ──────────────────────────────── (production-ready)
↑ merge via PR
develop ─────────────────────────────── (integration & staging)
↑ merge via PR
feature/* ──── (fitur baru)
hotfix/* ──── (perbaikan darurat dari main)

**Branch Protection yang diterapkan:**
- `main`: hanya menerima merge dari `develop`
- `develop`: auto-deploy ke staging setiap push
- Setiap security finding → otomatis dibuat GitHub Issue dengan label `security`, `dependencies`, atau `bug`

---

## Security Tools yang Digunakan

| Stage | Tool | Fungsi | Action jika Temuan |
|---|---|---|---|
| Secret Scan | **Gitleaks** | Deteksi hardcoded secrets/API keys/credentials | BLOCK pipeline |
| SAST | **Semgrep** | Static analysis kerentanan kode (multi-language) | WARN (unstable) |
| Dep Scan Python | **pip-audit** | CVE di Python packages | WARN + GitHub Issue |
| Dep Scan Node.js | **npm audit** | CVE di Node.js packages | WARN + GitHub Issue |
| Dep Scan Go | **govulncheck** | CVE di Go modules | INFO |
| Image Scan | **Trivy** | CVE di Docker image layers | WARN (unstable) |
| Auto Reporting | **GitHub REST API** | Buat Issue otomatis dari temuan | GitHub Issue |

---

## Langkah Reproduksi

### Prerequisites
- Windows 11 dengan WSL2 (Ubuntu 22.04)
- Docker & Docker Compose (terinstall di dalam WSL2)
- Akun GitHub (dengan Personal Access Token scope: `repo`, `workflow`)
- Akun Docker Hub (dengan Access Token)
- Port tersedia: 3000, 5432, 8080, 8081, 8082, 8083

### 1. Clone Repository

```bash
git clone https://github.com/zulpicher/bookslib.git
cd bookslib
```

### 2. Setup Environment Variables

```bash
cp .env.example .env
# Edit .env sesuai kebutuhan:
# POSTGRES_USER=bookslib
# POSTGRES_PASSWORD=your_password
```

### 3. Jalankan Aplikasi (Tanpa Pipeline)

```bash
docker compose up -d
```

Akses:
- Frontend: http://localhost:3000
- Auth API: http://localhost:8081
- Books API: http://localhost:8082
- Reviews API: http://localhost:8083

### 4. Setup Jenkins

```bash
# Jalankan Jenkins via Docker
docker run -d --name jenkins \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(which docker):/usr/bin/docker \
  --group-add $(getent group docker | cut -d: -f3) \
  --restart unless-stopped \
  jenkins/jenkins:lts

# Ambil initial password
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Buka http://localhost:8080 lalu:
1. Install suggested plugins
2. Install tambahan: `Docker Pipeline`
3. Tambah credentials:
   - ID `github-token`: GitHub Personal Access Token
   - ID `dockerhub-cred`: Docker Hub username + access token

### 5. Setup Multibranch Pipeline di Jenkins

1. New Item → **Multibranch Pipeline** → nama: `bookslib-pipeline`
2. Branch Sources → GitHub → masukkan URL repo
3. Credentials: pilih `github-token`
4. Script Path: `Jenkinsfile`
5. Save → Jenkins otomatis scan & trigger build

### 6. Trigger Pipeline Manual

```bash
# Push ke develop untuk trigger staging pipeline
git checkout develop
git push origin develop

# Merge ke main untuk trigger production pipeline
git checkout main
git merge develop
git push origin main
```

### 7. Verifikasi Security Findings

Buka GitHub repo → **Issues** → lihat issues yang dibuat otomatis oleh pipeline dengan label `security`, `dependencies`, atau `bug`.

---

## Trade-off & Justifikasi Pemilihan Tools

### Mengapa Semgrep bukan SonarQube?

SonarQube membutuhkan server terpisah + database PostgreSQL tersendiri + konfigurasi yang kompleks. Dalam konteks waktu terbatas, **Semgrep** dipilih karena:
- Berjalan sebagai container tanpa server tambahan
- Support multi-language (Go, Python, JavaScript, C#) dalam satu tool
- Hasil scan cukup akurat untuk ERROR-level findings
- Tidak butuh setup project di UI terpisah

**Trade-off:** Semgrep tidak memiliki dashboard web seperti SonarQube dan tidak menyimpan historical data antar build.

### Mengapa Trivy bukan Clair/Snyk?

**Trivy** dipilih karena:
- All-in-one: bisa scan filesystem, Docker image, dan dependencies sekaligus
- Tidak butuh server/daemon terpisah
- Update database CVE otomatis
- Output JSON mudah di-parse

**Trade-off:** Trivy memerlukan download database CVE pertama kali (~100MB) yang memperlambat build pertama.

### Mengapa Docker Hub bukan GHCR?

Docker Hub dipilih karena lebih familiar dan mudah disetup. GHCR (GitHub Container Registry) sebenarnya lebih cocok untuk proyek ini karena terintegrasi langsung dengan GitHub, namun memerlukan konfigurasi token tambahan.

### Mengapa docker-compose bukan Kubernetes?

Untuk scope test ini dengan waktu terbatas, `docker-compose` dipilih karena:
- Lebih cepat disetup dan di-debug
- Tidak memerlukan cluster management
- Cukup untuk mendemonstrasikan deployment automation

**Trade-off:** Tidak ada proper zero-downtime deployment, tidak ada auto-scaling, tidak ada self-healing.

### Deployment Strategy

Staging (`develop` branch): `docker compose up -d --remove-orphans` — sederhana, cukup untuk environment non-production.

Production (`main` branch): sama dengan staging tapi menggunakan `docker-compose.prod.yml` overlay yang menambahkan `restart: always` dan memory limits. Ini bukan zero-downtime yang sesungguhnya — ada downtime singkat saat container di-recreate.

---

## Kendala & Perbaikan ke Depan

### Kendala yang Dihadapi

**1. Groovy String Escaping di Jenkinsfile**
Groovy tidak mengizinkan karakter backtick `` ` `` di dalam double-quoted string. Ini menyebabkan `MultipleCompilationErrorsException` berulang kali. Solusi: memindahkan semua Python inline script ke file `.py` eksternal yang dipanggil via `python3 jenkins/scripts/`.

**2. Python IndentationError di Inline Script**
Ketika Python script ditulis inline di dalam Groovy `'''...'''` block dengan indentasi, Python menginterpretasikan whitespace sebagai indentasi kode yang tidak valid. Solusi yang sama: pisahkan ke file eksternal.

**3. Go Unit Test Gagal Tanpa Database**
`auth-service` memiliki test `TestLoginHandler_Unauthorized` yang langsung query database tanpa mock. Di CI environment (tidak ada DB saat `docker build`), ini menyebabkan `nil pointer dereference` panic. Solusi sementara: tambahkan `|| true` di Dockerfile agar build tidak gagal. Bug ini didokumentasikan sebagai GitHub Issue.

**4. Jenkins di Localhost + GitHub Webhook**
Jenkins berjalan di WSL2 localhost tidak bisa di-reach langsung oleh GitHub webhook. Solusi yang digunakan: scan manual dan periodic scan (5 menit), bukan event-driven webhook. Untuk production seharusnya menggunakan ngrok atau men-deploy Jenkins di server publik.

**5. Gitleaks Menemukan 2 Leaks**
Gitleaks mendeteksi 2 potential secrets di repo. Ini kemungkinan false positive dari file konfigurasi atau contoh kredensial. Perlu investigasi lebih lanjut untuk mengkonfirmasi apakah genuine secrets atau false positive, lalu menambahkan ke `.gitleaksignore` jika memang false positive.

**6. govulncheck PATH Issue**
`govulncheck` terinstall di `/root/go/bin/` di dalam container Go Alpine, namun PATH tidak ter-update secara otomatis saat menggunakan `sh -c`. Solusi: hardcode path `/root/go/bin/govulncheck`.

### Yang Akan Dilakukan Jika Ada Waktu Lebih

**Security:**
- [ ] Investigasi dan resolve 2 Gitleaks findings (genuine atau false positive)
- [ ] Tambahkan DAST scanning dengan OWASP ZAP setelah deployment staging
- [ ] Implementasi image signing dengan Cosign (supply chain security)
- [ ] Tambahkan SonarQube dengan quality gate untuk analisis lebih mendalam
- [ ] Fix Go unit test dengan proper DB mock menggunakan `database/sql/driver` mock

**CI/CD:**
- [ ] Deploy Jenkins ke server publik (bukan localhost) agar webhook GitHub berfungsi
- [ ] Implementasi proper zero-downtime deployment dengan K3s atau Kubernetes
- [ ] Tambahkan rollback otomatis jika health check gagal setelah deploy
- [ ] Notifikasi Slack/email untuk pipeline status
- [ ] Cache Docker layers di Jenkins untuk mempercepat build

**Infrastruktur:**
- [ ] Branch protection rules di GitHub (require PR review + passing CI sebelum merge ke main)
- [ ] Environment secrets yang proper (menggunakan Vault atau GitHub Secrets)
- [ ] Monitoring post-deployment dengan health check endpoint
- [ ] Separate staging dan production environment (bukan di mesin yang sama)

---

## Security Findings

Temuan keamanan yang ditemukan selama pipeline berjalan didokumentasikan sebagai GitHub Issues:

| # | Temuan | Tool | Severity | Status |
|---|---|---|---|---|
| Secret scan | 2 potential secrets terdeteksi | Gitleaks | HIGH | Open - perlu investigasi |
| Go test | Unit test tanpa DB mock (nil pointer) | Manual | MEDIUM | Open - perlu DB mock |
| Node deps | 4 vulnerabilities (1 low, 2 high, 1 critical) | npm audit | HIGH | Open |

> Semua findings otomatis dibuat sebagai GitHub Issues dengan label yang sesuai.
> Lihat: https://github.com/zulpicher/bookslib/issues

---

## Struktur Repository
bookslib/
├── auth-service/ # Go 1.20 - Authentication service
├── books-service/ # .NET 8 - Books CRUD service
├── frontend/ # React 18 + Vite - Web UI
├── reviews-service/ # Python/Django 4.2 - Reviews service
├── jenkins/
│ └── scripts/
│ ├── create-github-issue.sh # Auto-create GitHub Issues
│ ├── parse_gitleaks.py # Parse Gitleaks JSON output
│ ├── parse_semgrep.py # Parse Semgrep JSON output
│ ├── parse_pip_audit.py # Parse pip-audit JSON output
│ ├── parse_npm_audit.py # Parse npm audit JSON output
│ └── parse_trivy.py # Parse Trivy JSON output
├── Jenkinsfile # Main CI/CD pipeline definition
├── docker-compose.yaml # Base compose file
├── docker-compose.staging.yml # Staging overrides
├── docker-compose.prod.yml # Production overrides
├── .env.example # Environment variables template
└── README.md # This file
---

*Dokumentasi ini dibuat sebagai bagian dari Technical Test DevSecOps Internship.*  
*Pipeline masih dalam proses perbaikan iteratif — beberapa stage belum 100% sukses karena kendala teknis yang didokumentasikan di atas.*
ENDOFREADME

echo "README.md berhasil dibuat!"
wc -l README.md
