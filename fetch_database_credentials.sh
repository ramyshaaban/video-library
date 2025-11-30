#!/bin/bash
# Fetch database credentials from AWS Secrets Manager

echo "============================================================"
echo "Fetching Database Credentials from AWS"
echo "============================================================"
echo ""

# Get production RDS credentials
echo "📋 Production RDS Credentials:"
PROD_RDS=$(aws secretsmanager get-secret-value --secret-id "production/rds" --query SecretString --output text 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$PROD_RDS" ]; then
    echo "$PROD_RDS" | python3 -m json.tool
    echo ""
    echo "💾 Saving to: production_rds_credentials.json"
    echo "$PROD_RDS" | python3 -m json.tool > production_rds_credentials.json
else
    echo "❌ Failed to get production RDS credentials"
fi

echo ""
echo "📋 Production Config:"
PROD_CONFIG=$(aws secretsmanager get-secret-value --secret-id "production/config" --query SecretString --output text 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$PROD_CONFIG" ]; then
    echo "$PROD_CONFIG" | python3 -m json.tool | head -30
    echo ""
    echo "💾 Saving to: production_config.json"
    echo "$PROD_CONFIG" | python3 -m json.tool > production_config.json
else
    echo "❌ Failed to get production config"
fi

echo ""
echo "============================================================"
echo "Database Endpoints:"
echo "============================================================"
echo ""
echo "Production: staycurrentmd-prod.cwbfxes47odm.us-east-1.rds.amazonaws.com:5432"
echo "Dev: staycurrent-dev-db.cwbfxes47odm.us-east-1.rds.amazonaws.com:5432"
echo ""

