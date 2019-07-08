#!/usr/bin/python

import argparse
import subprocess
import time
import boto3
import os
import jawa
import jkl


def listEC2InstanceIPaddresses(ec2,eksclustername,wngname):
    ipaddrs=[]
    print("\n\nLooking for EC2 instances with name",str(eksclustername)+"-"+str(wngname)+"-Node")
    instance = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [str(eksclustername)+"-"+str(wngname)+"-Node"]}])
    print("\n\n\n***Instances Found:",instance,"\n\n\n")
    for r in instance['Reservations']:
        for i in r['Instances']:
            try:
                pubip=i['NetworkInterfaces'][0]['Association']['PublicIp']
                print(pubip)
                ipaddrs.append(str(pubip))
            except:
                print("No public network interface for this instance")
    return(ipaddrs)

def removeNessusAgent(sshprivatekey,ipaddrs):
    print("Removing Nessus Agents from worker nodes")
    for ipaddress in ipaddrs:
        print("Removing Nessus Agent from",ipaddress)

        #Link the agent
        command="ssh -o StrictHostKeyChecking=no -i "+str(sshprivatekey)+" ec2-user@"+str(ipaddress)+ \
                " sudo /opt/nessus_agent/sbin/nessuscli agent unlink"
        print("Command:"+command)
        try:
            output=subprocess.check_output(command,shell=True)
        except:
            print("Error removing Nessus Agents")
            return(False)
        print("Output: "+str(output))


def deletingGuestbook(DEBUG):
    c=0
    output=""

    while jkl.checkRunningPods(DEBUG) > 0:
        print("Deleting guestbook frontend")
        command="kubectl delete -f guestbook-frontend.yaml"
        print("Command:"+command)
        try:
            output=subprocess.check_output(command,shell=True)
        except:
            print("Error deleting stack file")
        print("Output: "+str(output))

        print("Deleting redis slaves")
        command="kubectl delete -f redis-slaves.yaml"
        print("Command:"+command)
        try:
            output=subprocess.check_output(command,shell=True)
        except:
            print("Error deleting stack file")
        print("Output: "+str(output))


        print("Deleting redis master")
        command="kubectl delete -f redis-master.yaml"
        print("Command:"+command)
        try:
            output=subprocess.check_output(command,shell=True)
        except:
            print("Error deleting stack file")
        print("Output: "+str(output))
        c+=1
        time.sleep(60)
        if c > 3:
            print("Error deleting Guestbook app")
            return(False)

    return(True)





################################################################
# Start of program
################################################################
parser = argparse.ArgumentParser(description="Creates EKS environment to demonstration Tenable Container Security")
parser.add_argument('--debug',help="Display a **LOT** of information",action="store_true")
parser.add_argument('--stackname', help="The name of the stack ",nargs=1,action="store",default=["tenable-eks-cs-demo-stack"])
parser.add_argument('--ec2keypairname', help="The name of the EC2 Key Pair ",nargs=1,action="store",default=["tenable-eks-demo-cs-keypair"])
parser.add_argument('--eksclustername', help="The name of the EKS cluster",nargs=1,action="store",default=["tenable-eks-cs-demo-eks-cluster"])
parser.add_argument('--wngstackname', help="The name of the worker node group stack",nargs=1,action="store",default=["tenable-eks-cs-demo-worker-nodes"])
parser.add_argument('--wngname', help="The name of the worker node group",nargs=1,action="store",default=["tenable-eks-cs-demo-worker-nodegroup"])
parser.add_argument('--sshprivatekey', help="The file name of the SSH private key on your system",nargs=1,action="store",default=[None])
parser.add_argument('--only', help="Only run one part of install: vpc, eks, nodegroup, agents, apps, keypair, display",nargs=1,action="store",default=[None])

args = parser.parse_args()
HOMEDIR=os.getenv("HOME")

ec2 = boto3.client('ec2')
cf= boto3.client('cloudformation')
eks = boto3.client('eks')

DEBUG=False
if args.debug:
    DEBUG=True


if args.only[0] == None:
    VPCSTACK=True
    EKSCLUSTER=True
    WORKERS=True
    AGENTS=True
    APPS=True
    KEYPAIR=True
else:
    VPCSTACK=False
    EKSCLUSTER=False
    WORKERS=False
    AGENTS=False
    APPS=False
    KEYPAIR=False
    if args.only[0]=="vpc":
        VPCSTACK=True
    elif args.only[0] == "eks":
        EKSCLUSTER = True
    elif args.only[0]=="nodegroup":
        WORKERS=True
    elif args.only[0]=="agents":
        AGENTS=True
    elif args.only[0] == "apps":
        APPS = True
    elif args.only[0]=="keypair":
        KEYPAIR = True

if args.sshprivatekey[0] == None:
    args.sshprivatekey[0]=HOMEDIR+"/.ssh/tenable-eks-cs-demo-keypair.pem"


if AGENTS:
    if args.sshprivatekey[0] == None:
        print("Need SSH private key location to unlink Nessus agents")
        exit(-1)


if APPS:
    if deletingGuestbook(DEBUG) == False:
        exit(-1)

ipaddrs=listEC2InstanceIPaddresses(ec2,args.eksclustername[0],args.wngname[0])

if AGENTS:
    if removeNessusAgent(args.sshprivatekey[0],ipaddrs):
        exit(-1)

if WORKERS:
    retval=jawa.deleteCFStack(DEBUG,cf,str(args.wngstackname[0]))
    if retval == True:
        print("Successfully deleted the CloudFoundation stack",str(args.wngstackname[0]))
    elif retval== None:
        print("Could not delete the CloudFoundation stack",str(args.wngstackname[0]),"since it does not exist")
    else:
        print("Error deleting the CloudFoundation stack",str(args.wngstackname[0]))
        exit(-1)

if EKSCLUSTER:
    retval=jawa.deleteEKS(DEBUG,eks,args.eksclustername[0])
    if retval == True:
        print("Successfully deleted the EKS cluster",str(args.eksclustername[0]))
    elif retval== None:
        print("Could not delete the EKS cluster",str(args.eksclustername[0]),"since it does not exist")
    else:
        print("Error deleting the EKS cluster",str(args.eksclustername[0]))
        exit(-1)


if VPCSTACK:
    retval=jawa.deleteCFStack(DEBUG,cf,args.stackname[0])
    if retval == True:
        print("Successfully deleted the CloudFoundation stack",str(args.stackname[0]))
    elif retval== None:
        print("Could not delete the CloudFoundation stack",str(args.stackname[0]),"since it does not exist")
    else:
        print("Error deleting the CloudFoundation stack",str(args.stackname[0]))
        exit(-1)


if KEYPAIR:
    retval=jawa.deleteEC2KeyPair(DEBUG,ec2,args.ec2keypairname[0])
    if retval == True:
        print("Successfully deleted the EC2 keypair",str(args.ec2keypairname[0]))
    elif retval== None:
        print("Could not delete the EC2 keypair",str(args.ec2keypairname[0]),"since it does not exist")
    else:
        print("Error deleting the EC2 keypair",str(args.ec2keypairname[0]))
        exit(-1)
