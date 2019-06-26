#!/bin/sh

#Set variables
STACKNAME="tenable-eks-cs-demo-stack"
EKSCLUSTER='tenable-eks-cs-demo-eks-cluster'

#Delete EKS cluster
echo "Deleting EKS cluster '$EKSCLUSTER'"
date
aws eks delete-cluster --name $EKSCLUSTER

date
if [ $? -ne 0 ] ; then
  echo 'Error deleting EKS cluster "$EKSCLUSTER"'
  exit -1
fi

date
echo "Waiting for '$EKSCLUSTER' to finish deleting..."
RETVAL=-1
while [ $RETVAL -ne 0 ] ; do
  aws eks wait cluster-deleted --name "$EKSCLUSTER"
  RETVAL=$?
  date
done
echo "Done!"


#Delete VPC, SG, and subnets
aws cloudformation delete-stack --stack-name "tenable-eks-cs-demo-stack"
if [ $? -ne 0 ] ; then
  echo 'Error deleting cloud formation stack "tenable-eks-cs-demo-stack"'
  exit -1
fi

echo "Waiting for 'tenable-eks-cs-demo-stack' to finish deleting..."
aws cloudformation wait stack-delete-complete --stack-name "tenable-eks-cs-demo-stack"
echo "Done!"