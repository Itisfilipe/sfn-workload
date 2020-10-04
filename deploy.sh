#!/bin/bash

set -e
PACKAGES_BUCKET="my-artifact-12345"
STACK_NAME="my-scrapper-12345"
PROFILE="filipeamaral"
REGION="us-east-1"

if pip show aws-sam-cli 2>&1 | grep -q 'not found'
then
echo "Installing SAM cli"
  pip install aws-sam-cli
fi

if aws s3 ls --profile $PROFILE --region $REGION "s3://$PACKAGES_BUCKET"  2>&1 | grep -q 'NoSuchBucket'
then
  echo "Creating artifact bucket"
  aws s3 mb --profile $PROFILE --region $REGION s3://$PACKAGES_BUCKET
fi

if aws cloudformation describe-stacks --stack-name $STACK_NAME --profile $PROFILE --region $REGION  2>&1 | grep -q '"StackStatus": "ROLLBACK_COMPLETE"'
then
  echo "Removing stack with ROLLBACK_COMPLETE status so we can create a new one"
  aws cloudformation delete-stack --stack-name $STACK_NAME --profile $PROFILE --region $REGION
fi

# just in case they exist
rm -f template.yaml
rm -f packaged.yaml

# run deploy tasks
python inject_steps.py -s ./src/stepFunctions.json -c template.raw.yaml -o template.yaml

sam validate --profile $PROFILE --region $REGION
sam build --profile $PROFILE --region $REGION
sam package --profile $PROFILE --region $REGION --s3-bucket $PACKAGES_BUCKET --output-template-file packaged.yaml
# You may want to append  --parameter-overrides ParameterKey=ShouldCreateTable,ParameterValue=true ParameterKey=ShouldCreateBucket,ParameterValue=true
sam deploy --profile $PROFILE --region $REGION --template-file packaged.yaml --stack-name $STACK_NAME --capabilities CAPABILITY_IAM

# # remove generated files
rm -f template.yaml
rm -f packaged.yaml
