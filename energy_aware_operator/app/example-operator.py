import kopf
import pykube #library that simplifies interaction with k8s API

@kopf.on.create("example.com", "v1alpha1", "exampleresources") # Watch for ExampleResource creation events
def create_fn(spec, **kwargs): # Function to handle creation events
    kube_api = pykube.HTTPClient(pykube.KubeConfig.from_file()) # Kubernetes API client
    deployment = pykube.Deployment(kube_api, {
        # Define the deployment object based on the ExampleResource spec
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        # ... other deployment properties
    })
    kopf.adopt(deployment) # Mark deployment as managed by the Operator
    deployment.create() # Create the deployment
    return {'message': 'Deployment created'}