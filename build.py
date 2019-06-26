#!/usr/bin/python

import argparse
import subprocess
import re
import time
import boto3

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


def gatherStackInfo(stackname):
    vpc=False
    sg=False
    subnets=False
    command="aws cloudformation describe-stacks --stack-name "+str(stackname)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error retrieving stack information")
        return (vpc, sg, subnets)

    match = re.search('"OutputValue": "(vpc-.*)".*', str(output))
    if match == None:
        print("Error retrieving stack information")
        return (vpc, sg, subnets)
    try:
        vpc=match.group(1)
    except:
        return (vpc, sg, subnets)

    match = re.search('"OutputValue": "(sg-.*)".*', str(output))
    if match == None:
        print("Error retrieving stack information")
        return (vpc, sg, subnets)
    try:
        sg=match.group(1)
    except:
        return (vpc, sg, subnets)

    match = re.search('"OutputValue": "(subnet-.*)".*', str(output))
    if match == None:
        print("Error retrieving stack information")
        return (vpc, sg, subnets)
    try:
        subnets=match.group(1)
    except:
        return (vpc, sg, subnets)


    return(vpc,sg,subnets)


def createEKS(clustername,sg,subnets,rolearn):
    command = "aws eks create-cluster --name "+str(clustername)+" --resources-vpc-config subnetIds="+str(subnets)+",securityGroupIds="+str(sg)+" --role-arn "+str(rolearn)
    print("Command:"+command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error creating EKS cluster")
        return(False)
    print("Output: "+str(output))

    command="aws eks wait cluster-active --name "+str(clustername)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error creating EKS cluster")
        return(False)
    print("Output: "+str(output))

    return(True)



def gatherEKSInfo(eksclustername):
    eksendpoint=False
    eksca=False
    command="aws eks describe-cluster --name "+str(eksclustername)
    print(command)
    try:
        output=subprocess.check_output(command,shell=True)
    except:
        print("Error retrieving stack information")
        return (eksendpoint, eksca)

    print(output)
    match = re.search('"endpoint": "(https://.*)".*', str(output))
    if match == None:
        print("Error retrieving stack information")
        return (eksendpoint, eksca)
    try:
        eksendpoint=match.group(1)
    except:
        return (eksendpoint, eksca)

    match = re.search('"data": "([^"]*)".*', str(output))
    if match == None:
        print("Error retrieving stack information")
        return (eksendpoint, eksca)
    try:
        eksca=match.group(1)
    except:
        print("Error retrieving stack information")
        return (eksendpoint, eksca)



    return(eksendpoint,eksca)


def createWorkNodeStack(stackname,nodegroupname,templatefile,vpc,sg,subnets,keypair):
    print("Starting creation of worker node group "+str(stackname))
    print("Using YAML file "+str(templatefile))

    command = "aws cloudformation create-stack --stack-name "+str(stackname)+" --template-body file://"+str(templatefile)+" --parameters '["+ \
                '{"ParameterKey": "NodeGroupName","ParameterValue": "'+str(nodegroupname)+'"},' + \
                '{"ParameterKey": "ClusterControlPlaneSecurityGroup","ParameterValue": "'+str(sg)+'"},' + \
                '{"ParameterKey": "KeyName","ParameterValue": "'+str(keypair)+'"},' + \
                '{"ParameterKey": "VpcId","ParameterValue": "'+str(vpc)+'"},' + \
                '{"ParameterKey": "Subnets","ParameterValue": "'+str(subnets)+'"}' + \
                "]' --capabilities CAPABILITY_IAM"
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


def listEC2InstanceIPaddresses(ec2,eksclustername,wngname):
    ipaddrs=[]
    instance = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [str(eksclustername)+"-"+str(wngname)+"-Node"]}])
    for i in instance['Reservations']:
        print(i['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp'])
        ipaddrs.append(i['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp'])

    return(ipaddrs)




def installNessusAgent(sshprivatekey,agentkey,agentgroup,ipaddrs):
    for ipaddress in ipaddrs:
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



################################################################
# Start of program
################################################################
parser = argparse.ArgumentParser(description="Creates EKS environment to demonstration Tenable Container Security")
parser.add_argument('--rolearn', help="The ARN of the role to use in the EKS environment",nargs=1,action="store",required=True)
parser.add_argument('--stackname', help="The name of the stack ",nargs=1,action="store",default=["tenable-eks-cs-demo-stack"])
parser.add_argument('--stackyamlfile', help="The YAML file defining the stack ",nargs=1,action="store",required=True)
parser.add_argument('--eksclustername', help="The name of the EKS cluster",nargs=1,action="store",default=["tenable-eks-cs-demo-eks-cluster"])
parser.add_argument('--wngstackname', help="The name of the worker node group stack",nargs=1,action="store",default=["tenable-eks-cs-demo-worker-nodes"])
parser.add_argument('--wngname', help="The name of the worker node group",nargs=1,action="store",default=["tenable-eks-cs-demo-worker-nodegroup"])
parser.add_argument('--wngyamlfile', help="The YAML file defining the workernodegroup ",nargs=1,action="store",required=True)
parser.add_argument('--sshkeypair', help="The name of the SSH keypair to use for worker node communication ",nargs=1,action="store",required=True)
parser.add_argument('--sshprivatekey', help="The file name of the SSH private key on your system",nargs=1,action="store",required=True)
parser.add_argument('--agentkey', help="The Tenable.io agent linking key ",nargs=1,action="store",required=True)
parser.add_argument('--agentgroup', help="The Tenable.io agent group for the agents ",nargs=1,action="store",required=True)
args = parser.parse_args()


ec2 = boto3.client('ec2')


if createStack(args.stackname[0],args.stackyamlfile[0]) == False:
    exit(-1)


(vpc,sg,subnets)=gatherStackInfo(args.stackname[0])
if vpc != False:
    print("VPC is ",vpc)
    print("SG is ",sg)
    print("Subnets are ",subnets)

if createEKS(args.eksclustername[0],sg,subnets,args.rolearn[0]) == False:
    exit(-1)

(eksendpoint,eksca)=gatherEKSInfo(args.eksclustername[0])
print("EKS Endpoint:",eksendpoint)
print("EKS CA:",eksca)

(vpc,sg,subnets)=gatherStackInfo(args.stackname[0])
createWorkNodeStack(args.wngstackname[0],args.wngname[0],args.wngyamlfile[0],vpc,sg,subnets,args.sshkeypair[0])

ipaddrs=listEC2InstanceIPaddresses(ec2,"Tenable-EKS-CS-demo-cluster",args.wngname[0])

installNessusAgent(args.sshprivatekey[0],args.agentkey[0],args.agentgroup[0],ipaddrs)
exit(0)
