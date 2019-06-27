#!/usr/bin/python

import argparse
import subprocess
import re
import time
import boto3
import sys
import os

def createStack(stackname,templatefile):
    print("Starting creation of stack "+str(stackname))
    print("Using YAML file "+str(templatefile))

    command = "aws cloudformation create-stack --stack-name "+str(stackname)+" --template-body file://"+str(templatefile)+""
    print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error creating stack file")
        return(False)
    print("Output: "+str(output))

    command="aws cloudformation wait stack-create-complete --stack-name "+str(stackname)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error creating stack file")
        return(False)
    print("Output: "+str(output))

    return(True)


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


def createEKS(eks,clustername,sg,subnets,rolearn):
    print("Creating EKS cluster with name",clustername,"and roleARN",rolearn," using subnets",subnets,"and security group",sg)

    try:
        response = eks.create_cluster(name=str(clustername), roleArn=str(rolearn), resourcesVpcConfig={'subnetIds': subnets, 'securityGroupIds': [str(sg)], })
    except:
        print("Error creating EKS cluster",sys.exc_info()[0], sys.exc_info()[1])
        return(False)
    print("Output from EKS create cluster command: ",response)

    print("Waiting for EKS cluster to finish building...")
    waiter=eks.get_waiter('cluster_active')
    try:
        waiter.wait(name=str(clustername))
    except:
        print("Error creating EKS cluster")
        return(False)
    print("Done!")

    return(True)



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



def createWorkNodeStack(cf,stackname,nodegroupname,templatefile,vpc,sg,subnets,keypair):
    print("Starting creation of worker node group ",str(stackname), "with subnets",str(subnets))
    print("Using YAML file "+str(templatefile))

    with open(templatefile,"r") as yamlfile:
        yamlfilestr=yamlfile.read()

    subnetstr=""
    for i in subnets:
        if subnetstr != "":
            subnetstr+=","+str(i)
        else:
            subnetstr=str(i)

    try:
        response = cf.create_stack(StackName=str(stackname),TemplateBody=yamlfilestr,Capabilities=['CAPABILITY_IAM'],
                Parameters=[
                {"ParameterKey": "NodeGroupName","ParameterValue": str(nodegroupname) },
                {"ParameterKey": "ClusterControlPlaneSecurityGroup","ParameterValue": str(sg) },
                {"ParameterKey": "KeyName","ParameterValue": str(keypair) },
                {"ParameterKey": "VpcId","ParameterValue": str(vpc) },
                {"ParameterKey": "Subnets","ParameterValue": subnetstr } ])
    except:
        print("Error creating worker node group", sys.exc_info()[0], sys.exc_info()[1])
        return (False)


    print("Output: ",response)

    print("Waiting for cloud formation to finish for worker node group")
    waiter=cf.get_waiter('stack_create_complete')
    try:
        waiter.wait(StackName=str(stackname))
    except:
        print("Error creating stack file")
        return(False)

    print("Done!")

    return(True)


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




def installNessusAgent(sshprivatekey,agentkey,agentgroup,ipaddrs):
    print("IP addresses on which to install Nessus Agents:",ipaddrs)
    for ipaddress in ipaddrs:
        print("Installing Nessus Agent on",ipaddress)

        #Copy over agent
        command="scp -o StrictHostKeyChecking=no -i "+str(sshprivatekey)+" NessusAgent-7.4.1.rpm ec2-user@"+str(ipaddress)+":"
        print("Command:"+command)
        try:
            output=subprocess.check_output(command,shell=True)
        except:
            print("Error creating stack file")
            return(False)
        print("Output: "+str(output))

        #Install RPM
        command="ssh -o StrictHostKeyChecking=no -i "+str(sshprivatekey)+" ec2-user@"+str(ipaddress)+" sudo rpm -ivh NessusAgent-7.4.1.rpm"
        print("Command:"+command)
        try:
            output=subprocess.check_output(command,shell=True)
        except:
            print("Error creating stack file")
            return(False)
        print("Output: "+str(output))

        #Start the agent
        command="ssh -o StrictHostKeyChecking=no -i "+str(sshprivatekey)+" ec2-user@"+str(ipaddress)+" sudo /sbin/service nessusagent start"
        print("Command:"+command)
        try:
            output=subprocess.check_output(command,shell=True)
        except:
            print("Error creating stack file")
            return(False)
        print("Output: "+str(output))

        time.sleep(5)

        #Link the agent
        command="ssh -o StrictHostKeyChecking=no -i "+str(sshprivatekey)+" ec2-user@"+str(ipaddress)+ \
                " sudo /opt/nessus_agent/sbin/nessuscli agent link --key="+str(agentkey)+" --cloud --groups=\\'"+str(agentgroup)+"\\'"
        print("Command:"+command)
        try:
            output=subprocess.check_output(command,shell=True)
        except:
            print("Error creating stack file")
            return(False)
        print("Output: "+str(output))


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
    command="aws-iam-authenticator token -i tenable-eks-cs-demo-eks-cluster"
    if DEBUG:
        print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error testing AWS connectivity to EKS cluster")
        return(False)
    if DEBUG:
        print("Output: "+str(output))

def deployGuestbook():
    print("Deploying redis master")
    command="kubectl apply -f redis-master.yaml"
    print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error creating stack file")
        return(False)
    print("Output: "+str(output))

    print("Deploying redis slaves")
    command="kubectl apply -f redis-slaves.yaml"
    print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error creating stack file")
        return(False)
    print("Output: "+str(output))

    print("Deploying guestbook frontend")
    command="kubectl apply -f guestbook-frontend.yaml"
    print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error creating stack file")
        return(False)
    print("Output: "+str(output))


def displayPublicURLs(DEBUG,ec2):
    if DEBUG:
        print("Gathering public IP addresses from EC2 network interfaces")
    interfaces = ec2.describe_network_interfaces(Filters=[{"Name": "group-name", "Values": ["k8s-elb-*"]}])
    if DEBUG:
        print("\n\n\n***interfaces Found:",interfaces,"\n\n\n")
    print("Public URLs for this cluster:")
    for i in interfaces['NetworkInterfaces']:
        try:
            print("http://"+str(i['PrivateIpAddresses'][0]['Association']['PublicIp']))
        except:
            x=0

    return()


################################################################
# Start of program
################################################################
parser = argparse.ArgumentParser(description="Creates EKS environment to demonstration Tenable Container Security")
parser.add_argument('--debug',help="Display a **LOT** of information",action="store_true")
parser.add_argument('--rolearn', help="The ARN of the role to use in the EKS cluster",nargs=1,action="store",default=[None])
parser.add_argument('--stackname', help="The name of the stack ",nargs=1,action="store",default=["tenable-eks-cs-demo-stack"])
parser.add_argument('--stackyamlfile', help="The YAML file defining the stack ",nargs=1,action="store",default=[None])
parser.add_argument('--eksclustername', help="The name of the EKS cluster",nargs=1,action="store",default=["tenable-eks-cs-demo-eks-cluster"])
parser.add_argument('--wngstackname', help="The name of the worker node group stack",nargs=1,action="store",default=["tenable-eks-cs-demo-worker-nodes"])
parser.add_argument('--wngname', help="The name of the worker node group",nargs=1,action="store",default=["tenable-eks-cs-demo-worker-nodegroup"])
parser.add_argument('--wngyamlfile', help="The YAML file defining the workernodegroup ",nargs=1,action="store",default=[None])
parser.add_argument('--sshkeypair', help="The name of the SSH keypair to use for worker node communication ",nargs=1,action="store",default=[None])
parser.add_argument('--sshprivatekey', help="The file name of the SSH private key on your system",nargs=1,action="store",default=[None])
parser.add_argument('--agentkey', help="The Tenable.io agent linking key ",nargs=1,action="store",default=[None])
parser.add_argument('--agentgroup', help="The Tenable.io agent group for the agents ",nargs=1,action="store",default=[None])
parser.add_argument('--only', help="Only run one part of install: vpc, eks, nodegroup, agents, apps, display",nargs=1,action="store",default=[None])
args = parser.parse_args()

DEBUG=False
HOMEDIR=os.getenv("HOME")
ec2 = boto3.client('ec2')
cf= boto3.client('cloudformation')
eks = boto3.client('eks')

if args.debug:
    DEBUG=True


if args.only[0] == False:
    CREATEVPC=True
    CREATEEKS=True
    CREATEWORKERS=True
    INSTALLAGENTS=True
    DEPLOYAPPS=True
else:
    CREATEVPC=False
    CREATEEKS=False
    CREATEWORKERS=False
    INSTALLAGENTS=False
    DEPLOYAPPS=False
    if args.only[0]=="vpc":
        CREATEVPC=True
    elif args.only[0] == "eks":
        CREATEEKS = True
    elif args.only[0]=="nodegroup":
        CREATEWORKERS=True
    elif args.only[0]=="agents":
        INSTALLAGENTS=True
    elif args.only[0]=="apps":
        DEPLOYAPPS=True

#Check that all necessary parameters are given
if CREATEVPC:
    if args.stackyamlfile[0] == None:
        print("Need YAML file to create VPC stack")
        exit(-1)

if CREATEEKS:
    if args.rolearn[0] == None:
        print("Need role ARN for the creation of the EKS cluster")
        exit(-1)

if CREATEWORKERS:
    if args.wngyamlfile[0] == None:
        print("Need YAML file to create worker nodegroup stack")
        exit(-1)
    if args.sshkeypair[0] == None:
        print("Need SSH Keypair for worker nodegroup stack")
        exit(-1)

if INSTALLAGENTS:
    if args.sshprivatekey[0] == None:
        print("Need SSH private key location to install Nessus agents")
        exit(-1)
    if args.agentkey[0] == None:
        print("Need Tenable.io Agent linking key to install Nessus agents")
        exit(-1)
    if args.agentgroup[0] == None:
        print("Need Tenable.io Agent group key to install Nessus agents")
        exit(-1)


if CREATEVPC:
    if createStack(args.stackname[0],args.stackyamlfile[0]) == False:
        exit(-1)
    if onlyaction != False:
        exit(0)

(vpc,sg,subnets)=gatherStackInfo(DEBUG,cf,args.stackname[0])
if vpc != False:
    print("VPC is",vpc)
    print("SG is",sg)
    print("Subnets are",subnets)

if CREATEEKS:
    if createEKS(eks,args.eksclustername[0],sg,subnets,args.rolearn[0]) == False:
        exit(-1)
    if onlyaction != False:
        exit(0)

testAWSConnectivity(DEBUG,args.eksclustername[0])

(eksendpoint,eksca)=gatherEKSInfo(DEBUG,eks,args.eksclustername[0])
print("EKS Endpoint:",eksendpoint)
print("EKS CA:",eksca)

if CREATEEKS:
    writeKubeConfigEKS(eksca,eksendpoint,args.eksclustername[0],HOMEDIR)

if CREATEWORKERS:
    createWorkNodeStack(cf,args.wngstackname[0],args.wngname[0],args.wngyamlfile[0],vpc,sg,subnets,args.sshkeypair[0])
    (wngrolearn) = getWorkerNodeStackInfo(cf, args.wngstackname[0])
    writeAWSAuthYAML(wngrolearn)
    applyAWSAuthYAML()
    if onlyaction != False:
        exit(0)



ipaddrs=listEC2InstanceIPaddresses(DEBUG,ec2,args.eksclustername[0],args.wngname[0])

if INSTALLAGENTS:
    print("Installing Nessus Agents")
    installNessusAgent(args.sshprivatekey[0],args.agentkey[0],args.agentgroup[0],ipaddrs)
    if onlyaction != False:
        exit(0)

if DEPLOYAPPS:
    print("Deploying Guestbook app and Redis backend")
    deployGuestbook()

displayPublicURLs(DEBUG,ec2)

exit(0)
