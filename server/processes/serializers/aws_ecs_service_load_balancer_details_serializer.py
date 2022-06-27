from rest_framework import serializers

from processes.models import AwsEcsServiceLoadBalancerDetails


class AwsEcsServiceLoadBalancerDetailsSerializer(serializers.ModelSerializer):
    """
    Configuration for a service AWS ECS Task that is behind an application load
    balancer.
    """

    class Meta:
        model = AwsEcsServiceLoadBalancerDetails
        fields = ['target_group_arn', 'container_name', 'container_port']
