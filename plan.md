# AWS IRA Operator Plan

## Overview
The AWS IRA (IAM Roles for Service Accounts) Operator is a Python-based Kubernetes operator designed to automatically inject a `credhelper` sidecar container into pods based on specific annotations.

## Technical Stack
- **Language:** Python
- **Framework:** Kopf (Kubernetes Operator Framework)
- **Client:** `kubernetes` Python client
- **Deployment:** Dockerized deployment on Kubernetes

## Logic
1. **Monitoring:** Watches `apps/v1/Deployment` and `apps/v1/StatefulSet` resources.
2. **Filtering:** Only processes resources in namespaces specified via the `WATCH_NAMESPACES` environment variable.
3. **Trigger:** Looks for the following annotations on the pod template:
    - `ira.aws/trust-anchor-id`
    - `ira.aws/profile-arn`
    - `ira.aws/role-arn`
4. **Action:** Patches the pod spec to inject a sidecar container:
    - **Container Name:** `aws-ira-credhelper`
    - **Environment Variables:**
        - `TRUST_ANCHOR_ID`: from `ira.aws/trust-anchor-id`
        - `PROFILE_ARN`: from `ira.aws/profile-arn`
        - `ROLE_ARN`: from `ira.aws/role-arn`
5. **Idempotency:** Checks if the sidecar already exists before patching to prevent infinite loops.

## Project Structure
- `main.py`: The operator logic.
- `requirements.txt`: Dependencies.
- `Dockerfile`: Build configuration.
- `k8s/`: Kubernetes manifests (RBAC, Deployment, Test resources).
