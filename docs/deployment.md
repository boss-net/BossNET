# Deployment Guide

This guide explains how to deploy the Bangladesh Student Data Analytics project in different environments.

## Deployment Options

1. [Docker Compose Deployment](#docker-compose-deployment) (Development/Staging)
2. [Kubernetes Deployment](#kubernetes-deployment) (Production)

## Prerequisites

- Docker and Docker Compose installed
- Kubernetes cluster (for production)
- Access to container registry
- Required environment variables configured

## Docker Compose Deployment

### Development Environment

1. Build and start services:
   \`\`\`bash
   docker-compose up --build -d
   \`\`\`

2. Run database migrations:
   \`\`\`bash
   docker-compose exec app python src/data_processing/run_migrations.py
   \`\`\`

3. Access the application:
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs

### Staging Environment

1. Create staging environment file:
   \`\`\`bash
   cp deploy/environments/development.env deploy/environments/staging.env
   # Edit staging.env with appropriate values
   \`\`\`

2. Deploy using staging configuration:
   \`\`\`bash
   ./deploy/deploy.sh staging v1.0.0
   \`\`\`

## Kubernetes Deployment

### Production Environment Setup

1. Create Kubernetes namespace:
   \`\`\`bash
   kubectl create namespace bdren
   \`\`\`

2. Create secrets:
   \`\`\`bash
   # Update deploy/kubernetes/secrets.yaml with your base64 encoded values
   kubectl apply -f deploy/kubernetes/secrets.yaml
   \`\`\`

3. Deploy infrastructure:
   \`\`\`bash
   kubectl apply -f deploy/kubernetes/db-deployment.yaml
   kubectl apply -f deploy/kubernetes/redis-deployment.yaml
   \`\`\`

4. Deploy application:
   \`\`\`bash
   kubectl apply -f deploy/kubernetes/app-deployment.yaml
   \`\`\`

5. Configure ingress:
   \`\`\`bash
   kubectl apply -f deploy/kubernetes/ingress.yaml
   \`\`\`

### Scaling

Scale the application horizontally:
\`\`\`bash
kubectl scale deployment student-analytics -n bdren --replicas=5
\`\`\`

### Monitoring

1. Check deployment status:
   \`\`\`bash
   kubectl get pods -n bdren
   kubectl get services -n bdren
   \`\`\`

2. View logs:
   \`\`\`bash
   kubectl logs -f deployment/student-analytics -n bdren
   \`\`\`

## Environment Variables

Key environment variables that need to be configured:

\`\`\`bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
DB_USER=prod_user
DB_PASSWORD=secure_password
DB_NAME=student_analytics_prod
DB_PORT=5432

# Redis
REDIS_PORT=6379

# API
PORT=8000
ALLOWED_ORIGINS=https://analytics.bdren.edu.bd
\`\`\`

## Backup and Restore

### Database Backup

1. Manual backup:
   \`\`\`bash
   ./deploy/backup.sh
   \`\`\`

2. Automated daily backups are configured in Kubernetes CronJob

### Restore from Backup

\`\`\`bash
./deploy/restore.sh <backup-file>
\`\`\`

## Troubleshooting

### Common Issues

1. Database Connection Issues
   - Check database credentials
   - Verify network connectivity
   - Ensure database service is running

2. Redis Connection Issues
   - Verify Redis service status
   - Check Redis credentials
   - Confirm network policies

3. Application Startup Issues
   - Check logs: `kubectl logs -f deployment/student-analytics -n bdren`
   - Verify environment variables
   - Check resource constraints

### Health Checks

1. Application Health:
   \`\`\`bash
   curl https://analytics.bdren.edu.bd/health
   \`\`\`

2. Database Health:
   \`\`\`bash
   kubectl exec -it $(kubectl get pod -l app=postgres -n bdren -o jsonpath='{.items[0].metadata.name}') -n bdren -- pg_isready
   \`\`\`

## Rollback Procedure

1. Identify the previous working version
2. Update the deployment:
   \`\`\`bash
   kubectl set image deployment/student-analytics student-analytics=your-registry.com/student-analytics:previous-version -n bdren
   \`\`\`

3. Monitor the rollback:
   \`\`\`bash
   kubectl rollout status deployment/student-analytics -n bdren
   \`\`\`

## Security Considerations

1. Secrets Management
   - Use Kubernetes secrets for sensitive data
   - Rotate credentials regularly
   - Monitor access logs

2. Network Security
   - Configure network policies
   - Use TLS for all external communication
   - Regular security audits

3. Access Control
   - Implement RBAC
   - Regular access review
   - Audit logging

## Performance Optimization

1. Resource Allocation
   - Monitor resource usage
   - Adjust limits based on usage patterns
   - Configure auto-scaling

2. Caching Strategy
   - Configure Redis caching
   - Implement API response caching
   - Monitor cache hit rates

## Maintenance

1. Regular Updates
   - Schedule maintenance windows
   - Update dependencies
   - Apply security patches

2. Monitoring
   - Set up metrics collection
   - Configure alerts
   - Regular performance review

## Support

For deployment support:
1. Check the troubleshooting guide
2. Review logs and metrics
3. Contact the DevOps team
4. Submit issues in the repository

Remember to always test deployments in lower environments before applying to production.
