from rest_framework import serializers

from processes.models import AwsEcsServiceLoadBalancerDetails


class AwsEcsServiceLoadBalancerDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AwsEcsServiceLoadBalancerDetails
        fields = ['target_group_arn', 'container_name', 'container_port']
