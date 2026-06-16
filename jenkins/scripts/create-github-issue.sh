#!/bin/bash
# Usage: ./create-github-issue.sh "title" "body" "label"

TITLE="$1"
BODY="$2"
LABEL="${3:-security}"

REPO="${GITHUB_REPO}"   # format: username/repo
TOKEN="${GITHUB_TOKEN}"

echo "Creating GitHub Issue: $TITLE"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO/issues" \
  -d "{
    \"title\": \"[DevSecOps] $TITLE\",
    \"body\": \"## Automated Security Finding\n\n$BODY\n\n---\n_This issue was automatically created by Jenkins DevSecOps Pipeline_\",
    \"labels\": [\"$LABEL\", \"automated\"]
  }")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY_RESP=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "201" ]; then
  ISSUE_URL=$(echo "$BODY_RESP" | grep -o '"html_url": "[^"]*' | head -1 | cut -d'"' -f4)
  echo "✅ Issue created: $ISSUE_URL"
else
  echo "⚠️  Failed to create issue (HTTP $HTTP_CODE)"
  echo "$BODY_RESP"
fi
