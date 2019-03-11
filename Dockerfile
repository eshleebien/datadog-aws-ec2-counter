FROM datadog/agent:latest

RUN /opt/datadog-agent/embedded/bin/pip install boto3
COPY ./checks.d/aws_ec2_count.py /etc/datadog-agent/checks.d/
COPY ./conf.d/aws_ec2_count.yaml.example /etc/datadog-agent/conf.d/aws_ec2_count.yaml
