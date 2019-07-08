#!/usr/bin/python
#[J]ames [K]ubernetes [L]ibrary

from kubernetes import client, config
import sys

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
