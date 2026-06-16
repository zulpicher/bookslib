# BooksLib - DevSecOps CI/CD Pipeline (Track A)

## Arsitektur
GitHub (develop/main branch)

│

▼ push/PR trigger (Webhook)

Jenkins Pipeline

│

├─ 1. Secret Scan    (Gitleaks)       → block pipeline jika ada secrets

├─ 2. SAST           (Semgrep)         → flag ERROR-level findings

├─ 3. Dependency Scan (parallel)

│      ├─ Python     (pip-audit)

│      ├─ Node.js    (npm audit)

│      └─ Go         (govulncheck)

├─ 4. Build Docker Images (multi-stage Dockerfile)

├─ 5. Image Scan     (Trivy)           → flag CRITICAL CVEs

├─ 6. Push to Docker Hub               (develop & main only)

└─ 7. Deploy

├─ develop → docker-compose (staging)

└─ main    → docker-compose (production, zero-downtime scale)
Security findings → GitHub Issues (otomatis via REST API)
## Stack Microservices

| Service | Tech | Port |
|---|---|---|
| frontend | React + Vite + Nginx | 3000 |
| auth-service | Go 1.20 | 8081 |
| books-service | .NET 8 | 8082 |
| reviews-service | Python/Django 4.2 | 8083 |
| Database | PostgreSQL 15 | 5432 |

## Git Flow Branching

- `main` → production only, dilindungi branch protection
- `develop` → integration branch, auto-deploy ke staging
- `feature/*` → fitur baru, PR ke develop
- `hotfix/*` → perbaikan darurat dari main

## Cara Menjalankan Lokal

### Prerequisites
- Docker & Docker Compose
- WSL2 (Windows) atau Linux

```bash
git clone https://github.com/<username>/bookslib.git
cd bookslib
cp .env.example .env   # edit sesuai kebutuhan
docker compose up -d
```

Akses: http://localhost:3000

## Cara Menjalankan Jenkins

```bash
docker run -d --name jenkins \
  -p 8080:8080 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(which docker):/usr/bin/docker \
  jenkins/jenkins:lts
```

Buka http://localhost:8080 → setup Multibranch Pipeline → arahkan ke repo ini.

## Security Tools & Justifikasi

| Tool | Fungsi | Alasan Dipilih |
|---|---|---|
| Gitleaks | Secret scanning | Ringan, CLI-based, zero config |
| Semgrep | SAST | Support multi-language, no server needed |
| pip-audit | Python deps | Native pip ecosystem |
| npm audit | Node.js deps | Built-in npm |
| govulncheck | Go deps | Official Google tool |
| Trivy | Image scanning | All-in-one, cepat, akurat |

**Trade-off:** Saya memilih Semgrep daripada SonarQube karena SonarQube butuh server + database terpisah yang kompleks untuk setup dalam waktu terbatas. Semgrep memberikan hasil yang cukup baik untuk SAST dengan setup minimal.

## Kendala & Improvement

### Kendala
- Jenkins di localhost membutuhkan ngrok untuk webhook GitHub (tidak ideal untuk production)
- Build .NET memakan waktu cukup lama di pipeline

### Yang Akan Dilakukan Jika Ada Waktu Lebih
- [ ] Tambah SonarQube dengan quality gate
- [ ] Implementasi K3s untuk zero-downtime deployment yang lebih proper
- [ ] DAST scanning dengan OWASP ZAP setelah deployment staging
- [ ] Signing image dengan Cosign (supply chain security)
- [ ] Notifikasi Slack/email untuk pipeline status
- [ ] Branch protection rules di GitHub (require PR review sebelum merge ke main)
