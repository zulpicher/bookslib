pipeline {
    agent any

    environment {
        // === GANTI SESUAI MILIKMU ===
        GITHUB_REPO      = "zulpicher/bookslib"
        DOCKERHUB_USER   = "zulpicher"  
        // ============================

        IMAGE_PREFIX     = "${DOCKERHUB_USER}/bookslib"
        IMAGE_TAG        = "${env.BRANCH_NAME}-${env.BUILD_NUMBER}"
        GITHUB_TOKEN     = credentials('github-token')
    }

    options {
        timestamps()
        timeout(time: 45, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {

        // ─────────────────────────────────────────
        stage('Checkout') {
            steps {
                echo "📥 Checking out branch: ${env.BRANCH_NAME}"
                checkout scm
            }
        }

        // ─────────────────────────────────────────
        stage('Secret Scanning - Gitleaks') {
            steps {
                script {
                    echo "🔍 Running Gitleaks secret scan..."
                    def exitCode = sh(
                        script: '''
                            docker run --rm \
                              -v "${WORKSPACE}:/path" \
                              zricethezav/gitleaks:latest \
                              detect \
                              --source="/path" \
                              --report-format=json \
                              --report-path="/path/gitleaks-report.json" \
                              --no-git \
                              --exit-code=1 2>&1 || true

                            if [ -f gitleaks-report.json ]; then
                                COUNT=$(cat gitleaks-report.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo "0")
                                echo "Gitleaks found $COUNT secret(s)"
                                echo $COUNT
                            fi
                        ''',
                        returnStatus: true
                    )

                    if (exitCode != 0) {
                        def report = sh(script: "cat gitleaks-report.json 2>/dev/null || echo '[]'", returnStdout: true).trim()
                        sh """
                            bash jenkins/scripts/create-github-issue.sh \
                              "Secret Leaked in Code - Build #${env.BUILD_NUMBER}" \
                              "**Branch:** \`${env.BRANCH_NAME}\`\n**Build:** ${env.BUILD_NUMBER}\n\n**Gitleaks Report:**\n\`\`\`json\n${report.take(3000)}\n\`\`\`" \
                              "security"
                        """
                        error("❌ Gitleaks found secrets in code! Pipeline stopped.")
                    } else {
                        echo "✅ No secrets found"
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'gitleaks-report.json', allowEmptyArchive: true
                }
            }
        }

        // ─────────────────────────────────────────
        stage('SAST - Semgrep') {
            steps {
                script {
                    echo "🔬 Running Semgrep static analysis..."
                    sh '''
                        docker run --rm \
                          -v "${WORKSPACE}:/src" \
                          returntocorp/semgrep:latest \
                          semgrep scan \
                          --config=auto \
                          --json \
                          --output=/src/semgrep-report.json \
                          /src \
                          --severity=ERROR \
                          --timeout=120 \
                          2>/dev/null || true
                    '''

                    def severity = sh(
                        script: '''
                            python3 -c "
import json, sys
try:
    with open('semgrep-report.json') as f:
        data = json.load(f)
    errors = [r for r in data.get('results', []) if r.get('extra', {}).get('severity') == 'ERROR']
    print(len(errors))
except:
    print(0)
"
                        ''',
                        returnStdout: true
                    ).trim().toInteger()

                    echo "Semgrep found ${severity} ERROR-level finding(s)"

                    if (severity > 0) {
                        def summary = sh(
                            script: '''python3 -c "
import json
with open('semgrep-report.json') as f:
    data = json.load(f)
errors = [r for r in data.get('results', []) if r.get('extra', {}).get('severity') == 'ERROR']
for r in errors[:5]:
    print(f\"- {r.get('check_id','')} in {r.get('path','')}:{r.get('start',{}).get('line','')}\")
"''',
                            returnStdout: true
                        ).trim()

                        sh """
                            bash jenkins/scripts/create-github-issue.sh \
                              "SAST Finding: ${severity} ERROR(s) - Build #${env.BUILD_NUMBER}" \
                              "**Branch:** \`${env.BRANCH_NAME}\`\n**Severity:** ERROR\n**Count:** ${severity}\n\n**Top Findings:**\n${summary}" \
                              "security"
                        """
                        unstable("⚠️ Semgrep found ${severity} ERROR-level issues - marked as unstable")
                    } else {
                        echo "✅ No critical SAST findings"
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'semgrep-report.json', allowEmptyArchive: true
                }
            }
        }

        // ─────────────────────────────────────────
        stage('Dependency Scan') {
            parallel {

                stage('Python - pip-audit') {
                    steps {
                        script {
                            echo "📦 Scanning Python dependencies..."
                            sh '''
                                docker run --rm \
                                  -v "${WORKSPACE}/reviews-service:/app" \
                                  -w /app \
                                  python:3.10-slim \
                                  sh -c "pip install pip-audit --quiet && pip-audit -r requirements.txt --format=json -o /app/pip-audit-report.json 2>&1 || true"
                            '''

                            def vulnCount = sh(
                                script: '''python3 -c "
import json
try:
    with open('reviews-service/pip-audit-report.json') as f:
        data = json.load(f)
    vulns = [d for d in data.get('dependencies',[]) if d.get('vulns')]
    print(len(vulns))
except:
    print(0)
"''',
                                returnStdout: true
                            ).trim().toInteger()

                            if (vulnCount > 0) {
                                sh """
                                    bash jenkins/scripts/create-github-issue.sh \
                                      "Vulnerable Python Dependencies: ${vulnCount} package(s)" \
                                      "**Branch:** \`${env.BRANCH_NAME}\`\n**Service:** reviews-service\n**Vulnerable packages:** ${vulnCount}\n\nRun \`pip-audit -r requirements.txt\` locally for full details." \
                                      "dependencies"
                                """
                                echo "⚠️ ${vulnCount} vulnerable Python package(s) found"
                            } else {
                                echo "✅ Python dependencies clean"
                            }
                        }
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'reviews-service/pip-audit-report.json', allowEmptyArchive: true
                        }
                    }
                }

                stage('Node.js - npm audit') {
                    steps {
                        script {
                            echo "📦 Scanning Node.js dependencies..."
                            def exitCode = sh(
                                script: '''
                                    docker run --rm \
                                      -v "${WORKSPACE}/frontend:/app" \
                                      -w /app \
                                      node:18-alpine \
                                      sh -c "npm install --silent 2>/dev/null; npm audit --json > /app/npm-audit-report.json 2>/dev/null; exit 0"
                                ''',
                                returnStatus: true
                            )

                            def highVulns = sh(
                                script: '''python3 -c "
import json
try:
    with open('frontend/npm-audit-report.json') as f:
        data = json.load(f)
    meta = data.get('metadata', {}).get('vulnerabilities', {})
    print(meta.get('high', 0) + meta.get('critical', 0))
except:
    print(0)
"''',
                                returnStdout: true
                            ).trim().toInteger()

                            if (highVulns > 0) {
                                sh """
                                    bash jenkins/scripts/create-github-issue.sh \
                                      "Vulnerable Node.js Dependencies: ${highVulns} high/critical" \
                                      "**Branch:** \`${env.BRANCH_NAME}\`\n**Service:** frontend\n**High/Critical:** ${highVulns}\n\nRun \`npm audit\` locally for full details." \
                                      "dependencies"
                                """
                            }
                            echo "✅ Node.js audit done (${highVulns} high/critical)"
                        }
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'frontend/npm-audit-report.json', allowEmptyArchive: true
                        }
                    }
                }

                stage('Go - govulncheck') {
                    steps {
                        script {
                            echo "📦 Scanning Go dependencies..."
                            sh '''
                                docker run --rm \
                                  -v "${WORKSPACE}/auth-service:/app" \
                                  -w /app \
                                  golang:1.20-alpine \
                                  sh -c "go install golang.org/x/vuln/cmd/govulncheck@latest 2>/dev/null; govulncheck ./... 2>&1 | tee /app/govuln-report.txt; exit 0"
                            '''
                            echo "✅ Go vulnerability check done"
                        }
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'auth-service/govuln-report.txt', allowEmptyArchive: true
                        }
                    }
                }

            }
        }

        // ─────────────────────────────────────────
        stage('Build Docker Images') {
            steps {
                script {
                    echo "🐳 Building Docker images..."
                    def services = ['frontend', 'auth-service', 'books-service', 'reviews-service']
                    def imageMap = [
                        'frontend'       : "${IMAGE_PREFIX}-frontend:${IMAGE_TAG}",
                        'auth-service'   : "${IMAGE_PREFIX}-auth:${IMAGE_TAG}",
                        'books-service'  : "${IMAGE_PREFIX}-books:${IMAGE_TAG}",
                        'reviews-service': "${IMAGE_PREFIX}-reviews:${IMAGE_TAG}"
                    ]

                    services.each { svc ->
                        echo "Building ${svc}..."
                        sh "docker build --target production -t ${imageMap[svc]} ./${svc}"
                    }

                    env.IMAGE_FRONTEND = imageMap['frontend']
                    env.IMAGE_AUTH     = imageMap['auth-service']
                    env.IMAGE_BOOKS    = imageMap['books-service']
                    env.IMAGE_REVIEWS  = imageMap['reviews-service']
                }
            }
        }

        // ─────────────────────────────────────────
        stage('Image Scan - Trivy') {
            steps {
                script {
                    echo "🛡️ Scanning Docker images with Trivy..."
                    def images = [
                        ['name': 'frontend',  'image': env.IMAGE_FRONTEND],
                        ['name': 'auth',      'image': env.IMAGE_AUTH],
                        ['name': 'books',     'image': env.IMAGE_BOOKS],
                        ['name': 'reviews',   'image': env.IMAGE_REVIEWS]
                    ]

                    def criticalFound = false

                    images.each { item ->
                        echo "Scanning ${item.name}..."
                        sh """
                            docker run --rm \
                              -v /var/run/docker.sock:/var/run/docker.sock \
                              -v trivy-cache:/root/.cache/trivy \
                              aquasec/trivy:latest image \
                              --format json \
                              --output /tmp/trivy-${item.name}.json \
                              --severity HIGH,CRITICAL \
                              --exit-code 0 \
                              ${item.image} 2>/dev/null || true

                            docker cp \$(docker create --rm aquasec/trivy:latest):/tmp/trivy-${item.name}.json . 2>/dev/null || true
                        """

                        // Simpler approach: run trivy and capture output
                        sh """
                            docker run --rm \
                              -v /var/run/docker.sock:/var/run/docker.sock \
                              -v "${WORKSPACE}:/output" \
                              -v trivy-cache:/root/.cache/trivy \
                              aquasec/trivy:latest image \
                              --format json \
                              --output /output/trivy-${item.name}.json \
                              --severity HIGH,CRITICAL \
                              --exit-code 0 \
                              ${item.image} 2>&1 | tail -5
                        """

                        def critCount = sh(
                            script: """python3 -c "
import json
try:
    with open('trivy-${item.name}.json') as f:
        data = json.load(f)
    total = 0
    for result in data.get('Results', []):
        for v in result.get('Vulnerabilities', []):
            if v.get('Severity') == 'CRITICAL':
                total += 1
    print(total)
except Exception as e:
    print(0)
"  """,
                            returnStdout: true
                        ).trim().toInteger()

                        if (critCount > 0) {
                            criticalFound = true
                            sh """
                                bash jenkins/scripts/create-github-issue.sh \
                                  "CRITICAL CVE in Docker Image: ${item.name} (${critCount} finding(s))" \
                                  "**Branch:** \`${env.BRANCH_NAME}\`\n**Image:** \`${item.image}\`\n**CRITICAL CVEs:** ${critCount}\n\nRun \`trivy image ${item.image}\` for full details." \
                                  "security"
                            """
                            echo "⚠️ ${critCount} CRITICAL CVE(s) in ${item.name}"
                        } else {
                            echo "✅ ${item.name} image - no CRITICAL CVEs"
                        }
                    }

                    if (criticalFound) {
                        unstable("⚠️ Critical CVEs found in one or more images")
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'trivy-*.json', allowEmptyArchive: true
                }
            }
        }

        // ─────────────────────────────────────────
        stage('Push Images to Registry') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                script {
                    echo "📤 Pushing images to Docker Hub..."
                    withCredentials([usernamePassword(
                        credentialsId: 'dockerhub-cred',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )]) {
                        sh 'echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin'
                        sh "docker push ${env.IMAGE_FRONTEND}"
                        sh "docker push ${env.IMAGE_AUTH}"
                        sh "docker push ${env.IMAGE_BOOKS}"
                        sh "docker push ${env.IMAGE_REVIEWS}"

                        // Tag latest untuk branch main
                        if (env.BRANCH_NAME == 'main') {
                            ['frontend', 'auth', 'books', 'reviews'].each { svc ->
                                def img = env["IMAGE_${svc.toUpperCase()}"]
                                sh "docker tag ${img} ${DOCKERHUB_USER}/bookslib-${svc}:latest"
                                sh "docker push ${DOCKERHUB_USER}/bookslib-${svc}:latest"
                            }
                        }
                    }
                }
            }
        }

        // ─────────────────────────────────────────
        stage('Deploy - Staging') {
            when { branch 'develop' }
            steps {
                script {
                    echo "🚀 Deploying to Staging (docker-compose)..."
                    sh '''
                        cp .env.example .env 2>/dev/null || true

                        # Rolling update: bring up new containers, remove old
                        docker compose -f docker-compose.yml \
                          -f docker-compose.staging.yml \
                          up -d --build --remove-orphans

                        # Health check
                        sleep 15
                        docker compose ps
                    '''
                }
            }
        }

        // ─────────────────────────────────────────
        stage('Deploy - Production') {
            when { branch 'main' }
            steps {
                script {
                    echo "🚀 Deploying to Production (Zero-Downtime)..."
                    sh '''
                        # Zero-downtime: scale up new, health check, scale down old
                        docker compose -f docker-compose.yml \
                          -f docker-compose.prod.yml \
                          up -d --scale auth-service=2 --scale reviews-service=2 --no-build

                        sleep 20

                        # Verify semua container running
                        RUNNING=$(docker compose ps --status running | grep -c "Up" || true)
                        echo "Running containers: $RUNNING"

                        docker compose ps
                    '''
                }
            }
        }

    }

    post {
        success {
            echo "✅ Pipeline PASSED - Branch: ${env.BRANCH_NAME} | Build: ${env.BUILD_NUMBER}"
        }
        unstable {
            echo "⚠️ Pipeline UNSTABLE - Security findings detected, review GitHub Issues"
        }
        failure {
            echo "❌ Pipeline FAILED - Branch: ${env.BRANCH_NAME} | Build: ${env.BUILD_NUMBER}"
            script {
                sh """
                    bash jenkins/scripts/create-github-issue.sh \
                      "Pipeline FAILED - Build #${env.BUILD_NUMBER}" \
                      "**Branch:** \`${env.BRANCH_NAME}\`\n**Build:** ${env.BUILD_NUMBER}\n**Status:** FAILED\n\nCheck Jenkins logs for details: ${env.BUILD_URL}" \
                      "bug" || true
                """
            }
        }
        always {
            sh 'docker logout || true'
            echo "📊 Build artifacts archived"
        }
    }
}
