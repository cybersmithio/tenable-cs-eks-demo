#!/usr/bin/python

import argparse
import subprocess
import time
import boto3




def deleteEKS(clustername):
    command = "aws eks delete-cluster --name "+str(clustername)
    print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error deleting EKS cluster")
        return(False)
    print("Output: "+str(output))

    print("Waiting for EKS to delete")
    command = "aws eks wait cluster-deleted --name " + str(clustername)
    while True:
        try:
            output=subprocess.check_output(command,shell=True)
            break
        except:
            print("Error waiting for EKS cluster to finish deleting")

    print("EKS cluster successfully deleted")


def deleteStack(stackname):
    print("Starting deletion of stack "+str(stackname))
    command="aws cloudformation delete-stack --stack-name "+str(stackname)
    print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error creating stack file")
        return(False)
    print("Output: ",output)

    command="aws cloudformation wait stack-delete-complete --stack-name "+str(stackname)
    print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error creating stack file")
        return(False)
    print("Output: ",output)

    return(True)


def listEC2InstanceIPaddresses(ec2,eksclustername,wngname):
    ipaddrs=[]
    instance = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [str(eksclustername)+"-"+str(wngname)+"-Node"]}])
    for i in instance['Reservations']:
        print(i['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp'])
        ipaddrs.append(i['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp'])

    return(ipaddrs)



def removeNessusAgent(sshprivatekey,ipaddrs):
    for ipaddress in ipaddrs:

        #Link the agent
        command="ssh -o StrictHostKeyChecking=no -i "+str(sshprivatekey)+" ec2-user@"+str(ipaddress)+ \
                " sudo /opt/nessus_agent/sbin/nessuscli agent unlink"
        print("Command:"+command)
        try:
            output=subprocess.check_output(command,shell=True)
        except:
            print("Error creating stack file")
            return(False)
        print("Output: "+str(output))



################################################################
# Start of program
################################################################
parser = argparse.ArgumentParser(description="Creates EKS environment to demonstration Tenable Container Security")
parser.add_argument('--stackname', help="The name of the stack ",nargs=1,action="store",default="tenable-eks-cs-demo-stack")
parser.add_argument('--eksclustername', help="The name of the EKS cluster",nargs=1,action="store",default=["tenable-eks-cs-demo-eks-cluster"])
parser.add_argument('--wngstackname', help="The name of the worker node group stack",nargs=1,action="store",default=["tenable-eks-cs-demo-worker-nodes"])
parser.add_argument('--wngname', help="The name of the worker node group",nargs=1,action="store",default=["tenable-eks-cs-demo-worker-nodegroup"])
parser.add_argument('--sshprivatekey', help="The file name of the SSH private key on your system",nargs=1,action="store",required=True)

args = parser.parse_args()

ec2 = boto3.client('ec2')


if deleteEKS(args.eksclustername[0]) == False:
    exit(-1)

if deleteStack(args.stackname[0]) == False:
    exit(-1)
exit(0)

ipaddrs=listEC2InstanceIPaddresses(ec2,"Tenable-EKS-CS-demo-cluster",args.wngname[0])

removeNessusAgent(args.sshprivatekey[0],ipaddrs)

if deleteStack(args.wngstackname[0]) == False:
    exit(-1)

if deleteEKS(args.eksclustername[0]) == False:
    exit(-1)

if deleteStack(args.stackname[0]) == False:
    exit(-1)


