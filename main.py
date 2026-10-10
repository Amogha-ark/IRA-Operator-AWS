import os
import kopf
from kubernetes import client, config

# Configuration from environment variables
WATCH_NAMESPACES = os.getenv("WATCH_NAMESPACES", "").split(",")
CREDHELPER_IMAGE = os.getenv("CREDHELPER_IMAGE", "aws-ira/credhelper:latest")

def get_k8s_client():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.AppsV1Api()

def inject_sidecar(resource):
    api = get_k8s_client()
    name = resource['metadata']['name']
    namespace = resource['metadata']['namespace']
    kind = resource['kind']
    
    # Get pod template annotations
    spec = resource['spec']['template']['spec']
    annotations = resource['spec']['template']['metadata'].get('annotations', {})
    
    # Required annotations
    required_annotations = {
        "trust_anchor_id": "ira.aws/trust-anchor-id",
        "profile_arn": "ira.aws/profile-arn",
        "role_arn": "ira.aws/role-arn"
    }
    
    # Check if all required annotations are present
    vals = {}
    for key, anno in required_annotations.items():
        if anno not in annotations:
            return {"status": "ignored", "message": f"Missing annotation {anno}"}
        vals[key] = annotations[anno]

    # Check if sidecar already exists to avoid infinite loop
    containers = spec.get('containers', [])
    if any(c['name'] == 'aws-ira-credhelper' for c in containers):
        return {"status": "skipped", "message": "Sidecar already present"}

    # Create the sidecar container
    sidecar = {
        "name": "aws-ira-credhelper",
        "image": CREDHELPER_IMAGE,
        "env": [
            {"name": "TRUST_ANCHOR_ID", "value": vals["trust_anchor_id"]},
            {"name": "PROFILE_ARN", "value": vals["profile_arn"]},
            {"name": "ROLE_ARN", "value": vals["role_arn"]},
        ]
    }
    
    # Add sidecar to containers
    containers.append(sidecar)
    
    # Prepare the patch
    patch_body = {
        "spec": {
            "template": {
                "spec": {
                    "containers": containers
                }
            }
        }
    }
    
    if kind == "Deployment":
        api.patch_namespaced_deployment(name, namespace, patch_body)
    elif kind == "StatefulSet":
        api.patch_namespaced_stateful_set(name, namespace, patch_body)
        
    return {"status": "patched", "message": "Sidecar injected successfully"}

@kopf.on.create('apps', 'v1', 'deployments')
@kopf.on.update('apps', 'v1', 'deployments')
def handle_deployment(spec, name, namespace, **kwargs):
    if WATCH_NAMESPACES and namespace not in WATCH_NAMESPACES:
        return {"status": "ignored", "message": f"Namespace {namespace} not in watch list"}
    
    # The 'spec' passed by Kopf is the spec of the deployment. 
    # We need the full resource for our helper, or we can just use the passed values.
    # For simplicity in this logic, we reconstruct a minimal resource object.
    resource = {
        'kind': 'Deployment',
        'metadata': {'name': name, 'namespace': namespace},
        'spec': spec
    }
    return inject_sidecar(resource)

@kopf.on.create('apps', 'v1', 'statefulsets')
@kopf.on.update('apps', 'v1', 'statefulsets')
def handle_statefulset(spec, name, namespace, **kwargs):
    if WATCH_NAMESPACES and namespace not in WATCH_NAMESPACES:
        return {"status": "ignored", "message": f"Namespace {namespace} not in watch list"}
    
    resource = {
        'kind': 'StatefulSet',
        'metadata': {'name': name, 'namespace': namespace},
        'spec': spec
    }
    return inject_sidecar(resource)
