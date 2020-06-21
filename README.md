# Step Functions Workload 
A small aws workload that will grab data from an API, parse it to excel spreadsheets  and deliver to emails.
It was made for personal usage so it lacks testing and needs some refactoring, ⚠️ USE AT YOUR OWN RISK⚠️

Also, some configuration is required, check the parameters on cloudformation template and the lambda code
to figure out that 

- deploy.sh: execute everything needed for deployment
- template.ram.yaml: cloudformation description of the infrastructure, needs to be parsed with SAM
- inject_steps.py: small script to inject the json step functions template into our cloudformation template
- src/lambda/*: contains all lambdas the stepfunctions will be executing


![image](https://user-images.githubusercontent.com/4977614/85228514-2ab4c380-b3ba-11ea-927a-2afd8ffa98a8.png)
