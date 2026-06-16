pipeline {
    agent any

    environment {
        GITHUB_REPO    = "zulpicher/bookslib"
        DOCKERHUB_USER = "zulpicher"
        IMAGE_PREFIX   = "${DOCKERHUB_USER}/bookslib"
        IMAGE_TAG      = "${env.BRANCH_NAME}-${env.BUILD_NUMBER}"
        GITHUB_TOKEN   = credentials('github-token')
    }

    options {
        timestamps()
        timeout(time: 45, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {

        stage('Checkout') {
            steps {
                echo "Checking out branch: ${env.BRANCH_NAME}"
                checkout scm
            }
        }

        stage('Secret Scanning - Gitleaks') {
            steps {
                script {
                    echo "Running Gitleaks secret scan..."
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
                        ''',
                        returnStatus: true
                    )
                    if (exitCode != 0) {
                        sh """
                            bash jenkins/scripts/create-github-issue.sh \
                              "Secret Leaked in Code - Build ${env.BUILD_NUMBER}" \
                              "Branch: ${env.BRANCH_NAME} | Gitleaks found secrets. Check build artifacts." \
                              "security"
                        """
                        error("Gitleaks found secrets! Pipeline stopped.")
                    } else {
                        echo "No secrets found by Gitleaks"
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'gitleaks-report.json', allowEmptyArchive: true
                }
            }
        }

        stage('SAST - Semgrep') {
            steps {
                script {
                    echo "Running Semgrep static analysis..."
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
                        script: 'python3 jenkins/scripts/parse_semgrep.py',
                        returnStdout: true
                    ).trim().toInteger()

                    echo "Semgrep found ${severity} ERROR-level finding(s)"

                    if (severity > 0) {
                        sh """
                            bash jenkins/scripts/create-github-issue.sh \
                              "SAST Finding: ${severity} ERROR(s) - Build ${env.BUILD_NUMBER}" \
                              "Branch: ${env.BRANCH_NAME} | Semgrep found ${severity} ERROR(s). Check semgrep-report.json artifact." \
                              "security"
                        """
                        unstable("Semgrep found ${severity} ERROR-level issues")
                    } else {
                        echo "No critical SAST findings"
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'semgrep-report.json', allowEmptyArchive: true
                }
            }
        }

        stage('Dependency Scan') {
            parallel {

                stage('Python - pip-audit') {
                    steps {
                        script {
                            echo "Scanning Python dependencies..."
                            sh '''
                                docker run --rm \
                                  -v "${WORKSPACE}/reviews-service:/app" \
                                  -w /app \
                                  python:3.10-slim \
                                  sh -c "pip install pip-audit --quiet 2>/dev/null && \
                                         pip-audit -r requirements.txt --format=json \
                                         -o /app/pip-audit-report.json 2>&1 || true"
                            '''
                            def vulnCount = sh(
                                script: 'python3 jenkins/scripts/parse_pip_audit.py',
                                returnStdout: true
                            ).trim().toInteger()

                            echo "pip-audit found ${vulnCount} vulnerable package(s)"

                            if (vulnCount > 0) {
                                sh """
                                    bash jenkins/scripts/create-github-issue.sh \
                                      "Vulnerable Python Deps: ${vulnCount} package(s) - Build ${env.BUILD_NUMBER}" \
                                      "Branch: ${env.BRANCH_NAME} | Service: reviews-service | Vulnerable: ${vulnCount}" \
                                      "dependencies"
                                """
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
                            echo "Scanning Node.js dependencies..."
                            sh '''
                                docker run --rm \
                                  -v "${WORKSPACE}/frontend:/app" \
                                  -w /app \
                                  node:18-alpine \
                                  sh -c "npm install --silent 2>/dev/null; \
                                         npm audit --json > /app/npm-audit-report.json 2>/dev/null; \
                                         exit 0"
                            '''
                            def highVulns = sh(
                                script: 'python3 jenkins/scripts/parse_npm_audit.py',
                                returnStdout: true
                            ).trim().toInteger()

                            echo "npm audit found ${highVulns} high/critical issue(s)"

                            if (highVulns > 0) {
                                sh """
                                    bash jenkins/scripts/create-github-issue.sh \
                                      "Vulnerable Node.js Deps: ${highVulns} - Build ${env.BUILD_NUMBER}" \
                                      "Branch: ${env.BRANCH_NAME} | Service: frontend | High/Critical: ${highVulns}" \
                                      "dependencies"
                                """
                            }
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
                            echo "Scanning Go dependencies..."
                            sh '''
                                docker run --rm \
                                  -v "${WORKSPACE}/auth-service:/app" \
                                  -w /app \
                                  golang:1.20-alpine \
                                  sh -c "go install golang.org/x/vuln/cmd/govulncheck@latest 2>/dev/null; \
                                         /root/go/bin/govulncheck ./... 2>&1 | tee /app/govuln-report.txt; \
                                         exit 0"
                            '''
                            echo "Go vulnerability check done"
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

        stage('Build Docker Images') {
            steps {
                script {
                    echo "Building all Docker images..."
                    def services = [
                        [dir: 'frontend',        tag: "${IMAGE_PREFIX}-frontend:${IMAGE_TAG}"],
                        [dir: 'auth-service',    tag: "${IMAGE_PREFIX}-auth:${IMAGE_TAG}"],
                        [dir: 'books-service',   tag: "${IMAGE_PREFIX}-books:${IMAGE_TAG}"],
                        [dir: 'reviews-service', tag: "${IMAGE_PREFIX}-reviews:${IMAGE_TAG}"]
                    ]
                    services.each { svc ->
                        echo "Building ${svc.dir}..."
                        sh "docker build --target production --no-cache -t ${svc.tag} ./${svc.dir} 2>&1"
                    }
                    env.IMAGE_FRONTEND = "${IMAGE_PREFIX}-frontend:${IMAGE_TAG}"
                    env.IMAGE_AUTH     = "${IMAGE_PREFIX}-auth:${IMAGE_TAG}"
                    env.IMAGE_BOOKS    = "${IMAGE_PREFIX}-books:${IMAGE_TAG}"
                    env.IMAGE_REVIEWS  = "${IMAGE_PREFIX}-reviews:${IMAGE_TAG}"
                }
            }
        }

        stage('Image Scan - Trivy') {
            steps {
                script {
                    echo "Scanning Docker images with Trivy..."
                    def images = [
                        [name: 'frontend', image: env.IMAGE_FRONTEND],
                        [name: 'auth',     image: env.IMAGE_AUTH],
                        [name: 'books',    image: env.IMAGE_BOOKS],
                        [name: 'reviews',  image: env.IMAGE_REVIEWS]
                    ]
                    def criticalFound = false
                    images.each { item ->
                        echo "Scanning: ${item.name}"
                        sh """
                            docker run --rm \
                              -v /var/run/docker.sock:/var/run/docker.sock \
                              -v trivy-cache:/root/.cache/trivy \
                              -v "${WORKSPACE}:/output" \
                              aquasec/trivy:latest image \
                              --format json \
                              --output /output/trivy-${item.name}.json \
                              --severity HIGH,CRITICAL \
                              --exit-code 0 \
                              ${item.image} 2>&1 | tail -3 || true
                        """
                        def critCount = sh(
                            script: "python3 jenkins/scripts/parse_trivy.py ${item.name}",
                            returnStdout: true
                        ).trim().toInteger()

                        echo "Trivy: ${item.name} -> ${critCount} CRITICAL CVE(s)"

                        if (critCount > 0) {
                            criticalFound = true
                            sh """
                                bash jenkins/scripts/create-github-issue.sh \
                                  "CRITICAL CVE in image: ${item.name} - Build ${env.BUILD_NUMBER}" \
                                  "Branch: ${env.BRANCH_NAME} | Image: ${item.image} | CRITICAL CVEs: ${critCount}" \
                                  "security"
                            """
                        }
                    }
                    if (criticalFound) {
                        unstable("Critical CVEs found in one or more images")
                    } else {
                        echo "No CRITICAL CVEs found"
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'trivy-*.json', allowEmptyArchive: true
                }
            }
        }

        stage('Push Images to Registry') {
            when {
                anyOf { branch 'main'; branch 'develop' }
            }
            steps {
                script {
                    echo "Pushing images to Docker Hub..."
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
                        if (env.BRANCH_NAME == 'main') {
                            def latest = [
                                [img: env.IMAGE_FRONTEND, name: 'frontend'],
                                [img: env.IMAGE_AUTH,     name: 'auth'],
                                [img: env.IMAGE_BOOKS,    name: 'books'],
                                [img: env.IMAGE_REVIEWS,  name: 'reviews']
                            ]
                            latest.each { s ->
                                sh "docker tag ${s.img} ${DOCKERHUB_USER}/bookslib-${s.name}:latest"
                                sh "docker push ${DOCKERHUB_USER}/bookslib-${s.name}:latest"
                            }
                        }
                    }
                }
            }
        }

        stage('Deploy - Staging') {
            when { branch 'develop' }
            steps {
                echo "Deploying to Staging..."
                sh '''
                    docker compose -f docker-compose.yaml \
                      -f docker-compose.staging.yml \
                      up -d --build --remove-orphans
                    sleep 15
                    docker compose ps
                '''
            }
        }

        stage('Deploy - Production') {
            when { branch 'main' }
            steps {
                echo "Deploying to Production..."
                sh '''
                    docker compose -f docker-compose.yaml \
                      -f docker-compose.prod.yml \
                      up -d --build --remove-orphans
                    sleep 20
                    docker compose ps
                '''
            }
        }

    }

    post {
        success {
            echo "PIPELINE PASSED - Branch: ${env.BRANCH_NAME} | Build: ${env.BUILD_NUMBER}"
        }
        unstable {
            echo "PIPELINE UNSTABLE - Security findings detected, check GitHub Issues"
        }
        failure {
            script {
                sh """
                    bash jenkins/scripts/create-github-issue.sh \
                      "Pipeline FAILED - Build ${env.BUILD_NUMBER}" \
                      "Branch: ${env.BRANCH_NAME} | Build: ${env.BUILD_NUMBER} | URL: ${env.BUILD_URL}" \
                      "bug" || true
                """
            }
        }
        always {
            sh 'docker logout || true'
        }
    }
}
