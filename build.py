#!/usr/bin/python

import argparse
import subprocess
import time
import boto3
from botocore.exceptions import ClientError
import sys
import os
import jawa
import jkl
import re



def gatherStackInfo(DEBUG,cf,stackname):
    vpc=False
    sg=False
    subnets=False

    try:
        response = cf.describe_stacks(StackName=str(stackname))
    except:
        print("Error retrieving stack information", sys.exc_info()[0], sys.exc_info()[1])
        return (vpc, sg, subnets)

    if DEBUG:
        print("Output from desribe_stacks",response,"\n\n")

    for i in response['Stacks'][0]['Outputs']:
        if DEBUG:
            print(i)
        if i['OutputKey'] == "VpcId":
            vpc=i['OutputValue']
        elif i['OutputKey'] == "SecurityGroups":
            sg=i['OutputValue']
        elif i['OutputKey'] == "SubnetIds":
            subnetlist=i['OutputValue']
            subnets=subnetlist.split(",")
            if DEBUG:
                print("subnets:",subnets)

    return(vpc,sg,subnets)



def gatherEKSInfo(DEBUG,eks,eksclustername):
    eksendpoint=False
    eksca=False

    try:
        response = eks.describe_cluster(name=str(eksclustername))
    except:
        print("Error retrieving EKS cluster information", sys.exc_info()[0], sys.exc_info()[1])
        return (eksendpoint, eksca)

    if DEBUG:
        print("output",response)
    eksendpoint=response['cluster']['endpoint']
    eksca = response['cluster']['certificateAuthority']['data']

    return(eksendpoint,eksca)


def listEC2InstanceIPaddresses(DEBUG,ec2,eksclustername,wngname):
    ipaddrs=[]
    if DEBUG:
        print("\n\nLooking for EC2 instances with name",str(eksclustername)+"-"+str(wngname)+"-Node")
    instance = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [str(eksclustername)+"-"+str(wngname)+"-Node"]}])
    if DEBUG:
        print("\n\n\n***Instances Found:",instance,"\n\n\n")
    for r in instance['Reservations']:
        for i in r['Instances']:
            try:
                pubip=i['NetworkInterfaces'][0]['Association']['PublicIp']
                if DEBUG:
                    print(pubip)
                ipaddrs.append(str(pubip))
            except:
                if DEBUG:
                    print("No public network interface for this instance")
    return(ipaddrs)




def installNessusAgent(DEBUG,sshprivatekey,agentkey,agentgroup,ipaddrs):
    print("IP addresses on which to install Nessus Agents:",ipaddrs)
    for ipaddress in ipaddrs:
        print("Installing Nessus Agent on",ipaddress)

        retval=existingNessusAgent(DEBUG,sshprivatekey,ipaddress)
        if retval == 0:
            #Copy over agent
            command="scp -o StrictHostKeyChecking=no -i "+str(sshprivatekey)+" NessusAgent-7.4.1.rpm ec2-user@"+str(ipaddress)+":"
            print("Command:"+command)
            try:
                output=subprocess.check_output(command,shell=True)
            except:
                print("Error copying Nessus Agent to worker node")
                return(False)
            print("Output: "+str(output))

            #Install RPM
            command="ssh -o StrictHostKeyChecking=no -i "+str(sshprivatekey)+" ec2-user@"+str(ipaddress)+" sudo rpm -ivh NessusAgent-7.4.1.rpm"
            print("Command:"+command)
            try:
                output=subprocess.check_output(command,shell=True)
            except:
                print("Error installing Nessus Agent on worker node")
            print("Output: "+str(output))

            #Start the agent
            command="ssh -o StrictHostKeyChecking=no -i "+str(sshprivatekey)+" ec2-user@"+str(ipaddress)+" sudo /sbin/service nessusagent start"
            print("Command:"+command)
            try:
                output=subprocess.check_output(command,shell=True)
            except:
                print("Error starting Nessus Agent on worker node")
            print("Output: "+str(output))

            time.sleep(5)

        if retval <= 1:
            #Link the agent
            command="ssh -o StrictHostKeyChecking=no -i "+str(sshprivatekey)+" ec2-user@"+str(ipaddress)+ \
                    " sudo /opt/nessus_agent/sbin/nessuscli agent link --key="+str(agentkey)+" --cloud --groups=\\'"+str(agentgroup)+"\\'"
            print("Command:"+command)
            try:
                output=subprocess.check_output(command,shell=True)
            except:
                print("Error linking Nessus Agent to worker node")
                return(False)
            print("Output: "+str(output))

#Returns:
#  0 if no existing Agent
#  1 if agent installed but not linked
#  2 if agent is linked
def existingNessusAgent(DEBUG,sshprivatekey,ipaddress):
    print("Installing Nessus Agent on",ipaddress)

    #Link the agent
    command="ssh -o StrictHostKeyChecking=no -i "+str(sshprivatekey)+" ec2-user@"+str(ipaddress)+ \
            " sudo /opt/nessus_agent/sbin/nessuscli agent status"
    print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True).decode('utf-8')
    except:
        print("Error getting agent status")
        return(0)

    if DEBUG:
        print("Output: "+str(output))

    status = re.match(".*(Link failed with error).*", output)
    if status != None:
        if DEBUG:
            print("Agent is not linked.")
        return(1)

    status = re.match(".*(Not linked to a manager).*", output)
    if status != None:
        if DEBUG:
            print("Agent is not linked.")
        return(1)

    status = re.match(".*(command not found).*", output)
    if status != None:
        if DEBUG:
            print("Agent is not linked.")
        return(1)

    status = re.match(".*(Linked to: cloud.tenable.com).*", output)
    if status != None:
        if DEBUG:
            print("Agent is linked to cloud.tenable.com")
        return(2)
    else:
        if DEBUG:
            print("Agent does not appear to be linked.")
        return(1)

    return(0)


def writeKubeConfigEKS(eksca,eksendpoint,eksclustername,homedir):

    fp=open(homedir+"/.kube/kube-config-eks","w")
    fp.write(
'''apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: '''+ str(eksca)+'''
    server: '''+ str(eksendpoint)+
'''
  name: kubernetes
contexts:
- context:
    cluster: kubernetes
    user: aws
  name: aws
current-context: aws
kind: Config
preferences: {}
users:
- name: aws
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1alpha1
      command: aws-iam-authenticator
      args:
        - "token"
        - "-i"
        - "'''+ str(eksclustername)+
'''"
''')
    fp.close()


def writeAWSAuthYAML(rolearn):
    fp=open("aws-auth.yaml","w")
    fp.write(
'''apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: ''' +str(rolearn)+
'''
      username: system:node:{{EC2PrivateDNSName}}
      groups:
        - system:bootstrappers
        - system:nodes

'''
    )
    fp.close

def getWorkerNodeStackInfo(cf,stackname):
    rolearn=False

    try:
        response = cf.describe_stacks(StackName=str(stackname))
    except:
        print("Error retrieving stack information", sys.exc_info()[0], sys.exc_info()[1])
        return (rolearn)

    for i in response['Stacks'][0]['Outputs']:
        if i['OutputKey'] == "NodeInstanceRole":
            rolearn=i['OutputValue']
            print("Role ARN:",rolearn)

    return(rolearn)


def applyAWSAuthYAML():
    command="kubectl apply -f aws-auth.yaml"
    print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error creating stack file")
        return(False)
    print("Output: "+str(output))

def testAWSConnectivity(DEBUG,eksclustername):
    command="aws-iam-authenticator token -i "+str(eksclustername)
    if DEBUG:
        print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error testing AWS connectivity to EKS cluster")
        return(False)
    if DEBUG:
        print("Output: "+str(output))

def deployGuestbook(DEBUG,namespace="default"):
    print("Deploying redis master")
    command="kubectl apply -f redis-master.yaml --namespace="+str(namespace)

    if DEBUG:
        print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error creating stack file")
        return(False)
    if DEBUG:
        print("Output: "+str(output))

    print("Deploying redis slaves")
    command="kubectl apply -f redis-slaves.yaml --namespace="+str(namespace)
    if DEBUG:
        print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error creating stack file")
        return(False)
    if DEBUG:
        print("Output: "+str(output))

    print("Deploying guestbook frontend")
    command="kubectl apply -f guestbook-frontend.yaml --namespace="+str(namespace)
    print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error creating stack file")
        return(False)
    if DEBUG:
        print("Output: "+str(output))


def displayPublicURLs(DEBUG,ec2):
    if DEBUG:
        print("Gathering public IP addresses from EC2 network interfaces")
    interfaces = ec2.describe_network_interfaces(Filters=[{"Name": "group-name", "Values": ["k8s-elb-*"]}])
    if DEBUG:
        print("\n\n\n***interfaces Found:",interfaces,"\n\n\n")
    print("Public URLs for this cluster:")

    c=0
    for i in interfaces['NetworkInterfaces']:
        try:
            print("http://"+str(i['PrivateIpAddresses'][0]['Association']['PublicIp']))
            c+=1
        except:
            x=0

    if c == 0 :
        return(False)

    return(True)





def mkdirs(DEBUG,homedir):
    try:
        os.mkdir(homedir+"/.aws")
    except:
        print("Couldn't make ~/.aws/\nIt likely already exists")

    try:
        os.mkdir(homedir+"/.kube")
    except:
        print("Couldn't make ~/.kube/\nIt likely already exists")

    try:
        os.mkdir(homedir+"/.ssh")
    except:
        print("Couldn't make ~/.ssh/\nIt likely already exists")



################################################################
# Start of program
################################################################
parser = argparse.ArgumentParser(description="Creates EKS environment to demonstration Tenable Container Security")
parser.add_argument('--debug',help="Display a **LOT** of information",action="store_true")
parser.add_argument('--eksrole', help="The name of the EKS role used in the EKS cluster",nargs=1,action="store",default=["EKS-role"])
parser.add_argument('--stackname', help="The name of the stack ",nargs=1,action="store",default=["tenable-eks-cs-demo-stack"])
parser.add_argument('--stackyamlfile', help="The YAML file defining the stack ",nargs=1,action="store",default=[None])
parser.add_argument('--eksclustername', help="The name of the EKS cluster",nargs=1,action="store",default=["tenable-eks-cs-demo-eks-cluster"])
parser.add_argument('--namespace', help="The Kubernetes namespace into which all the objects will be deployed",nargs=1,action="store",default=["tenable-eks-cs-demo"])
parser.add_argument('--wngstackname', help="The name of the worker node group stack",nargs=1,action="store",default=["tenable-eks-cs-demo-worker-nodes"])
parser.add_argument('--wngname', help="The name of the worker node group",nargs=1,action="store",default=["tenable-eks-cs-demo-worker-nodegroup"])
parser.add_argument('--wngyamlfile', help="The YAML file defining the workernodegroup ",nargs=1,action="store",default=[None])
parser.add_argument('--ec2keypairname', help="The name of the EC2 keypair to use for SSH worker node communication ",nargs=1,action="store",default=["tenable-eks-demo-cs-keypair"])
parser.add_argument('--sshprivatekey', help="The file name of the SSH private key on your system",nargs=1,action="store",default=[None])
parser.add_argument('--agentkey', help="The Tenable.io agent linking key ",nargs=1,action="store",default=[None])
parser.add_argument('--agentgroup', help="The Tenable.io agent group for the agents ",nargs=1,action="store",default=[None])
parser.add_argument('--only', help="Only run one part of install: vpc, eks, nodegroup, agents, apps, keypair, display",nargs=1,action="store",default=[None])
parser.add_argument('--existingkeypair',help="Check if there is an existing keypair",action="store_true")
parser.add_argument('--existingvpc',help="Check if there is an existing VPC cloud formation stack",action="store_true")
parser.add_argument('--existingeks',help="Check if there is an existing EKS cluster",action="store_true")
parser.add_argument('--existingwng',help="Check if there is an existing Kubernetes worker node group stack",action="store_true")
parser.add_argument('--existingapps',help="Check if the apps have already been deployed",action="store_true")
args = parser.parse_args()

DEBUG=False
HOMEDIR=os.getenv("HOME")
ec2 = boto3.client('ec2')
cf= boto3.client('cloudformation')
eks = boto3.client('eks')
iam = boto3.client('iam')

namespace=args.namespace[0]
if args.debug:
    DEBUG=True

mkdirs(DEBUG,HOMEDIR)


if args.existingkeypair:
    if jawa.existingEC2KeyPair(DEBUG,ec2,args.ec2keypairname[0]):
        print("Key pair already exists")
    else:
        print("Key pair does not exist.")
    exit(0)

if args.existingvpc:
    if jawa.existingCFStack(DEBUG,cf,args.stackname[0]):
        print("VPC stack already exists.")
    else:
        print("VPC stack does not exist.")
    exit(0)

if args.existingwng:
    if jawa.existingCFStack(DEBUG,cf,args.wngname[0]):
        print("Worker node group stack already exists.")
    else:
        print("Worker node group stack does not exist.")
    exit(0)

if args.existingeks:
    if jawa.existingEKS(DEBUG,eks,args.eksclustername[0]):
        print("EKS cluster already exists.")
    else:
        print("EKS cluster does not exist.")
    exit(0)

if args.existingapps:
    retval=jkl.checkRunningPods(DEBUG)
    if retval >= 0 :
        print("Existing Kubernetes apps already deployed. # of Pods:",retval)
    else:
        print("No existing Kubernetes apps found.")
    exit(0)


if args.sshprivatekey[0] == None:
    args.sshprivatekey[0]=HOMEDIR+"/.ssh/tenable-eks-cs-demo-keypair.pem"


#Check that all necessary parameters are given
if args.only[0] == None or args.only[0]=="vpc":
    if args.stackyamlfile[0] == None:
        print("Need YAML file to create VPC stack")
        exit(-1)

if args.only[0] == None or args.only[0]=="eks":
    if args.eksrole[0] == None:
        print("Need role ARN for the creation of the EKS cluster")
        exit(-1)

if args.only[0] == None or args.only[0]=="nodegroup":
    if args.wngyamlfile[0] == None:
        print("Need YAML file to create worker nodegroup stack")
        exit(-1)
    if args.ec2keypairname[0] == None:
        print("Need SSH Keypair for worker nodegroup stack")
        exit(-1)

if args.only[0] == None or args.only[0]=="agents":
    if args.agentkey[0] == None:
        print("Need Tenable.io Agent linking key to install Nessus agents")
        exit(-1)
    if args.agentgroup[0] == None:
        print("Need Tenable.io Agent group key to install Nessus agents")
        exit(-1)


#Execute steps
if args.only[0] == None or args.only[0]=="keypair":
    if jawa.createEC2KeyPair(DEBUG,ec2,args.ec2keypairname[0],args.sshprivatekey[0]) == False:
        exit(-1)
    if args.only[0] == "keypair":
        exit(0)

if args.only[0] == None or args.only[0]=="vpc":
    if jawa.createCFStack(DEBUG,cf,args.stackname[0],args.stackyamlfile[0]) == False:
        exit(-1)
    if args.only[0] == "vpc":
        exit(0)

(vpc,sg,subnets)=gatherStackInfo(DEBUG,cf,args.stackname[0])
if vpc != False:
    print("VPC is",vpc)
    print("SG is",sg)
    print("Subnets are",subnets)

if args.only[0] == None or args.only[0]=="eks":
    rolearn=jawa.getRoleARN(DEBUG,iam,args.eksrole[0])
    if jawa.createEKS(DEBUG,eks,args.eksclustername[0],sg,subnets,rolearn) == False:
        exit(-1)


testAWSConnectivity(DEBUG,args.eksclustername[0])

(eksendpoint,eksca)=gatherEKSInfo(DEBUG,eks,args.eksclustername[0])
print("EKS Endpoint:",eksendpoint)
print("EKS CA:",eksca)

if args.only[0] == None or args.only[0]=="eks":
    writeKubeConfigEKS(eksca,eksendpoint,args.eksclustername[0],HOMEDIR)
    if args.only[0] == "eks":
        exit(0)



if args.only[0] == None or args.only[0]=="namespace":
    jkl.createNamespace(DEBUG,str(namespace))


if args.only[0] == None or args.only[0]=="nodegroup":
    #Create CloudFormation stack for worker node group
    subnetstr=""
    for i in subnets:
        if subnetstr != "":
            subnetstr+=","+str(i)
        else:
            subnetstr=str(i)
    jawa.createCFStack(DEBUG,cf,args.wngstackname[0],args.wngyamlfile[0],capabilities = ['CAPABILITY_IAM'],parameters=[
                                   {"ParameterKey": "NodeGroupName", "ParameterValue": str(args.wngname[0])},
                                   {"ParameterKey": "ClusterControlPlaneSecurityGroup", "ParameterValue": str(sg)},
                                   {"ParameterKey": "KeyName", "ParameterValue": str(args.ec2keypairname[0])},
                                   {"ParameterKey": "VpcId", "ParameterValue": str(vpc)},
                                   {"ParameterKey": "Subnets", "ParameterValue": subnetstr}])

    (wngrolearn) = getWorkerNodeStackInfo(cf, args.wngstackname[0])
    writeAWSAuthYAML(wngrolearn)
    applyAWSAuthYAML()
    if args.only[0] == "nodegroup":
        exit(0)


ipaddrs=listEC2InstanceIPaddresses(DEBUG,ec2,args.eksclustername[0],args.wngname[0])



if args.only[0] == None or args.only[0]=="agents":
    print("Installing Nessus Agents")
    installNessusAgent(DEBUG,args.sshprivatekey[0],args.agentkey[0],args.agentgroup[0],ipaddrs)
    if args.only[0] == "agents":
        exit(0)

if args.only[0] == None or args.only[0]=="apps":
    print("Deploying Guestbook app and Redis backend")
    deployGuestbook(DEBUG,namespace=namespace)
    while displayPublicURLs(DEBUG,ec2) == False:
        print("No public URLs available yet...waiting 30 seconds")
        time.sleep(30)
    if args.only[0] == "apps":
        exit(0)

if args.only[0] == None or args.only[0]=="display":
    displayPublicURLs(DEBUG,ec2)

exit(0)
