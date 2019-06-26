#!/bin/sh

#Set variables
STACKNAME="tenable-eks-cs-demo-stack"
EKSCLUSTER='tenable-eks-cs-demo-eks-cluster'
ROLEARN="$1"
if [ "x$ROLEARN" = "x" ] ; then
  echo "Need ROLEARN provided"
  exit -1
fi


#Create VPC, Subnets, and SG
aws cloudformation create-stack --stack-name "$STACKNAME" --template-body "`cat eks-course-vpc.yaml`"
if [ $? -ne 0 ] ; then
  echo 'Error creating cloud formation stack "$STACKNAME"'
  exit -1
fi

date
echo "Waiting for '$STACKNAME' to finish creating..."
aws cloudformation wait stack-create-complete --stack-name "$STACKNAME"
if [ $? -ne 0 ] ; then
  echo 'Error creating cloud formation stack "$STACKNAME"'
  exit -1
fi
echo "Done!"
date
SUBNETS=`aws cloudformation describe-stacks --stack-name "$STACKNAME" | sed -n "s/.*\"OutputValue\": \"\(subnet-.*\)\".*/\1/p"`
SECGROUP=`aws cloudformation describe-stacks --stack-name "$STACKNAME" | sed -n "s/.*\"OutputValue\": \"\(sg-.*\)\".*/\1/p"`
VPC=`aws cloudformation describe-stacks --stack-name "$STACKNAME" | sed -n "s/.*\"OutputValue\": \"\(vpc-.*\)\".*/\1/p"`

echo "VPC: $VPC"
echo "Subnets: $SUBNETS"
echo "SECGROUP: $SECGROUP"


#Create EKS cluster
aws eks create-cluster --name $EKSCLUSTER --resources-vpc-config subnetIds=$SUBNETS,securityGroupIds=$SECGROUP --role-arn $ROLEARN

date
if [ $? -ne 0 ] ; then
  echo 'Error creating EKS cluster "$EKSCLUSTER"'
  exit -1
fi

date
echo "Waiting for '$EKSCLUSTER' to finish creating..."
aws eks wait cluster-active --name "$EKSCLUSTER"
echo "Done!"
date
