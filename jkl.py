#!/usr/bin/python
#[J]ames [K]ubernetes [L]ibrary

from kubernetes import client, config
from kubernetes.client.rest import ApiException
import sys
from pprint import pprint
import base64

def checkRunningPods(DEBUG,namespace):
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
        if i.metadata.namespace == namespace:
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



def createSecretPassword(DEBUG,namespace,secretname,secretvalue):
    config.load_kube_config()

    kube = client.CoreV1Api()
    body=client.V1Secret("v1",{"password": base64.b64encode(str(secretvalue).encode('utf-8')).decode('utf-8') },'Secret',{"name":secretname})

    try:
        api_response = kube.create_namespaced_secret(namespace,body)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling CoreV1Api->create_namespaced_secret: %s\n" % e)


def deleteSecretPassword(DEBUG,namespace,secretname):
    config.load_kube_config()

    kube = client.CoreV1Api()
    try:
        api_response = kube.delete_namespaced_secret(secretname,namespace)
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling CoreV1Api->delete_namespaced_secret: %s\n" % e)
