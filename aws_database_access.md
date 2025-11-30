# AWS Database Access Guide

## ✅ AWS Access Confirmed

- **AWS CLI**: Installed and configured
- **AWS Account**: 842991041407
- **User**: ramy
- **SSM Parameters**: Found for staycurrent-services

## 🔍 Finding Database Credentials

### Option 1: Check RDS Databases

```bash
# List all RDS instances
aws rds describe-db-instances --query 'DBInstances[*].{ID:DBInstanceIdentifier, Engine:Engine, Endpoint:Endpoint.Address, Port:Endpoint.Port}' --output table

# Get connection details for a specific database
aws rds describe-db-instances --db-instance-identifier <DB_NAME> --query 'DBInstances[0].{Endpoint:Endpoint.Address, Port:Endpoint.Port, MasterUsername:MasterUsername}'
```

### Option 2: Check AWS Secrets Manager

```bash
# List all secrets
aws secretsmanager list-secrets --query 'SecretList[*].{Name:Name, Description:Description}' --output table

# Get a specific secret (database credentials)
aws secretsmanager get-secret-value --secret-id <SECRET_NAME> --query SecretString --output text
```

### Option 3: Check SSM Parameter Store

```bash
# List all parameters for staycurrent-services
aws ssm get-parameters-by-path --path "/copilot/staycurrent-services" --recursive

# Get specific parameter
aws ssm get-parameter --name "/copilot/staycurrent-services/production/secrets/DATABASE_URL" --with-decryption --query Parameter.Value --output text
```

### Option 4: Check ECS Task Definitions

```bash
# List ECS clusters
aws ecs list-clusters

# List services in a cluster
aws ecs list-services --cluster <CLUSTER_NAME>

# Get task definition (contains environment variables)
aws ecs describe-task-definition --task-definition <TASK_DEFINITION> --query 'taskDefinition.containerDefinitions[0].environment' --output json
```

## 🎯 Recommended Approach

1. **Check RDS** for database instances
2. **Check Secrets Manager** for database credentials
3. **Check SSM Parameters** for database URLs
4. **Check ECS** task definitions for environment variables

## 📋 Next Steps

Run the commands above to find:
- Database endpoint
- Database credentials
- Connection string

Once found, we can:
1. Update `fetch_videos_from_database.py` with the correct database URL
2. Query the database directly
3. Fetch all video metadata

