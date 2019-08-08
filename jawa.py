#!/usr/bin/python
#[J]ames [A][W]s [A]utomation library

import boto3
from botocore.exceptions import ClientError
import os
import sys
import stat


# Check if an AWS CloudFormation stack already exists with the same name
#
# If DEBUG is True then print debugging information to STDOUT
#
# Returns True if the stack exists, or None if the stack does not exist.
# Returns False if there were errors checking for the stack
#
def existingCFStack(DEBUG,cf,stackname):
    if DEBUG:
        print("Checking if stack name",stackname,"already exists.")

    try:
        response = cf.describe_stacks(StackName=str(stackname))
    except ClientError as e:
        if e.response['Error']['Code'] == 'ValidationError':
            if DEBUG:
                print("Stack does not exist")
            return(None)
        else:
            print("Unknown error code when checking for stack:",e.response['Error']['Code'])
            print("Error retrieving stack information", sys.exc_info()[0], sys.exc_info()[1])
            return(False)
    except:
        print("Error retrieving stack information",sys.exc_info()[0],sys.exc_info()[1])
        return(False)

    if DEBUG:
        print("Response:",response)
    return(True)

# Create an AWS CloudFormation stack
#
# If DEBUG is True then print debugging information to STDOUT
#
# Returns True if successful
# Returns False if there were errors
#
def createCFStack(DEBUG,cf,stackname,templatefile,capabilities=[],parameters=[]):
    if DEBUG:
        print("Starting creation of CloudFormation stack ",str(stackname))
        print("Using YAML file "+str(templatefile))
        print("Capabilities:",capabilities)
        print("Parameters:",parameters)

    with open(templatefile,"r") as yamlfile:
        yamlfilestr=yamlfile.read()

    try:
        response = cf.create_stack(StackName=str(stackname),TemplateBody=yamlfilestr,Capabilities=capabilities, Parameters=parameters)
    except ClientError as e:
        if e.response['Error']['Code'] == 'AlreadyExistsException':
            if DEBUG:
                print("Stack already exists")
            return(True)
        else:
            print("Unknown error code when checking for stack:",e.response['Error']['Code'])
            print("Error creating CloudFormation stack", sys.exc_info()[0], sys.exc_info()[1])
            return(False)
    except:
        print("Error creating CloudFormation stack", sys.exc_info()[0], sys.exc_info()[1])
        return (False)

    print("Output: ",response)

    print("Waiting for CloudFormation to finish for",stackname)
    waiter=cf.get_waiter('stack_create_complete')
    try:
        waiter.wait(StackName=str(stackname))
    except:
        print("Error creating stack file")
        return(False)

    print("CloudFormation complete for",stackname)

    return(True)

def deleteCFStack(DEBUG,cf,stackname):
    print("Starting deletion of stack "+str(stackname))

    try:
        response = cf.delete_stack(StackName=str(stackname))
    except ClientError as e:
        print("Unknown error code when checking for stack:",e.response['Error']['Code'])
        print("Error deleting CloudFormation stack", sys.exc_info()[0], sys.exc_info()[1])
        return(False)
    except:
        print("Error deleting CloudFormation stack", sys.exc_info()[0], sys.exc_info()[1])
        return (False)

    print("Output: ",response)

    print("Waiting for CloudFormation to finish deleting for",stackname)
    waiter=cf.get_waiter('stack_delete_complete')
    try:
        waiter.wait(StackName=str(stackname))
    except:
        print("Error deleting stack file")
        return(False)

    print("CloudFormation deleted for",stackname)

    return(True)



###
### EC2 keypair operations
###


# Checks if the key pair already exists
#
# If DEBUG is True then print debugging information to STDOUT
#
# Returns True if the keypair exists, or None if the keypair does not exist.
# Returns False if there were errors checking for the keypair
#
def existingEC2KeyPair(DEBUG,ec2,keypairname):
    try:
        response = ec2.describe_key_pairs(KeyNames=[ str(keypairname)])
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidKeyPair.NotFound':
            if DEBUG:
                print("Keypair does not exist")
            return(None)
        else:
            print("Error retrieving keypair information", sys.exc_info()[0], sys.exc_info()[1])
            return(False)
    except:
        print("Error retrieving keypair information",sys.exc_info()[0],sys.exc_info()[1])
        return(False)

    if DEBUG:
        print("Response:",response)
    return(True)


# Create an EC2 Key Pair
def createEC2KeyPair(DEBUG,ec2,keypairname,privatekey):
    retval=existingEC2KeyPair(DEBUG,ec2,keypairname)
    if retval == True:
        print("Keypair already exists.  Skipping creation.")
        return(True)
    elif retval == False:
        print("There was an error checking for an existing keypair")

    if DEBUG:
        print("Attempting to create keypair ",keypairname)

    try:
        response = ec2.create_key_pair(KeyName=str(keypairname))
    except:
        if DEBUG:
            print("Problem creating keypair.")
        return(False)

    if DEBUG:
        print("Response:",response)

    with open(privatekey,"w+") as privatekeyfp:
        privatekeyfp.write(response['KeyMaterial'])
        os.fchmod(privatekeyfp.fileno(),stat.S_IRUSR | stat.S_IWUSR)

    return(True)

# Deletes an EC2 key pair
#
# If DEBUG is True then print debugging information to STDOUT
#
# Returns True if EC2 key pair was successfully deleted
# Returns None if the key pair did not exist
# Returns False if there were errors deleting the key pair
#
def deleteEC2KeyPair(DEBUG,ec2,keypairname):
    if DEBUG:
        print("Attempting to delete keypair ",keypairname)
    try:
        response = ec2.delete_key_pair(KeyName=str(keypairname))
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidKeyPair.NotFound':
            if DEBUG:
                print("Keypair does not exist")
            return (None)
        else:
            print("Error deleting keypair information", sys.exc_info()[0], sys.exc_info()[1])
            return (False)
    except:
        print("Error deleting keypair information", sys.exc_info()[0], sys.exc_info()[1])
        return (False)

    if DEBUG:
        print("Response:",response)
    return(True)


###
### AWS EKS operations
###

# Create an EKS cluster
def createEKS(DEBUG,eks,clustername,sg,subnets,rolearn):
    print("Creating EKS cluster with name",clustername,"and roleARN",rolearn," using subnets",subnets,"and security group",sg)
    retval=existingEKS(DEBUG, eks, clustername)
    if retval == True:
        print("EKS cluster already exists. Skipping creation")
        return(True)
    elif retval == False:
        print("There was an error checking for an existing EKS cluster")

    try:
        response = eks.create_cluster(name=str(clustername), version="1.12", roleArn=str(rolearn),
                                      resourcesVpcConfig={'subnetIds': subnets, 'securityGroupIds': [str(sg)], })
    except ClientError as e:
        if e.response['Error']['Code'] == 'AlreadyExistsException':
            if DEBUG:
                print("EKS cluster already exists")
            return(True)
        else:
            print("Unknown error code when checking for stack:",e.response['Error']['Code'])
            print("Error creating EKS cluster", sys.exc_info()[0], sys.exc_info()[1])
            return(False)
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


# See if an EKS cluster already exists, by name
def existingEKS(DEBUG,eks,clustername):
    try:
        response = eks.describe_cluster(name=str(clustername))
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            if DEBUG:
                print("EKS cluster does not exist")
            return(None)
        else:
            print("Error retrieving EKS cluster information", sys.exc_info()[0], sys.exc_info()[1])
            return(False)
    except:
        print("Error retrieving EKS cluster information",sys.exc_info()[0],sys.exc_info()[1])
        return(False)

    if DEBUG:
        print("Response:",response)

    return(True)

def deleteEKS(DEBUG,eks,clustername):
    print("Dekete EKS cluster with name",clustername)
    retval=existingEKS(DEBUG, eks, clustername)
    if retval == None:
        print("EKS cluster does not exist. Skipping deletion")
        return(True)
    elif retval == False:
        print("There was an error checking for an existing EKS cluster")

    try:
        response = eks.delete_cluster(name=str(clustername))
    except ClientError as e:
        print("Unknown error code when checking for stack:",e.response['Error']['Code'])
        print("Error creating EKS cluster", sys.exc_info()[0], sys.exc_info()[1])
        return(False)
    except:
        print("Error creating EKS cluster",sys.exc_info()[0], sys.exc_info()[1])
        return(False)

    print("Output from EKS delete cluster command: ",response)

    print("Waiting for EKS delete cluster to finish building...")
    waiter=eks.get_waiter('cluster_deleted')
    try:
        waiter.wait(name=str(clustername))
    except:
        print("Error deleting EKS cluster")
        return(False)
    print("Done!")

    return(True)





###
### IAM Role operations
###
def getRoleARN(DEBUG, iam, rolename):
    if DEBUG:
        print('Retrieving Role ARN for role name', rolename)

    try:
        response = iam.get_role(RoleName=rolename)
    except:
        if DEBUG:
            print("Problem getting ARN for role", sys.exc_info()[0], sys.exc_info()[1])
        return (False)
    if DEBUG:
        print("Response", response)
    return (response['Role']['Arn'])
