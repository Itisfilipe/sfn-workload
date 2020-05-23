#!/bin/bash

set -e
PACKAGES_BUCKET="my-artifact"
STACK_NAME="my-scrapper"

if aws s3 ls "s3://$PACKAGES_BUCKET" 2>&1 | grep -q 'NoSuchBucket'
then
  echo "Creating artifact bucket"
  aws s3 mb s3://$PACKAGES_BUCKET
fi

# just in case they exist
rm -f template.yaml
rm -f packaged.yaml

# run deploy tasks
python inject_steps.py -s ./src/stepFunctions.json -c template.raw.yaml -o template.yaml

sam validate
sam build
sam package --s3-bucket $PACKAGES_BUCKET --output-template-file packaged.yaml
sam deploy --template-file packaged.yaml --stack-name $STACK_NAME --capabilities CAPABILITY_IAM

# remove generated files
rm -f template.yaml
rm -f packaged.yaml
