#!/usr/bin/python
#[J]ames [K]ubernetes [L]ibrary

from kubernetes import client, config
from kubernetes.client.rest import ApiException
import sys
from pprint import pprint

def checkRunningPods(DEBUG):
    # Configs can be set in Configuration class directly or using helper utility
    config.load_kube_config()

    kube = client.CoreV1Api()
    print("Listing pods with their IPs:")
    try:
        ret = kube.list_pod_for_all_namespaces(watch=False)
    except:
        print("Error getting pod information:", sys.exc_info()[0], sys.exc_info()[1])
        return (False)

    countpods=0
    for i in ret.items:
        if i.metadata.namespace != "kube-system":
            countpods+=1
            print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))

    return(countpods)

def createNamespace(DEBUG,namespace):
    # Configs can be set in Configuration class directly or using helper utility
    config.load_kube_config()

    kube = client.CoreV1Api()
    body=client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))


    try:
        api_response = kube.create_namespace(body)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling CoreV1Api->create_namespace: %s\n" % e)


def deleteNamespace(DEBUG,namespace):
    # Configs can be set in Configuration class directly or using helper utility
    config.load_kube_config()

    kube = client.CoreV1Api()

    try:
        api_response = kube.delete_namespace(namespace)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling CoreV1Api->delete_namespace: %s\n" % e)