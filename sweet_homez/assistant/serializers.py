from rest_framework import serializers

from houses.serializers import HouseSerializer
from users.models import User

from .models import Inquiry, SearchConversation, SearchMessage, SearchRequirements, ViewingRequest
from .schemas import REQUIREMENT_FIELDS


class ChatRequestSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    message = serializers.CharField(max_length=2000, trim_whitespace=True)


class SearchRequirementsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchRequirements
        fields = REQUIREMENT_FIELDS


class SearchMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchMessage
        fields = ["id", "role", "content", "created_at"]


class SearchConversationSerializer(serializers.ModelSerializer):
    requirements = SearchRequirementsSerializer(read_only=True)
    messages = SearchMessageSerializer(many=True, read_only=True)

    class Meta:
        model = SearchConversation
        fields = ["id", "language", "requirements", "messages", "created_at", "updated_at"]


class ChatResponseSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    message = serializers.CharField()
    requirements = SearchRequirementsSerializer()
    matches = HouseSerializer(many=True)
    recommended_agents = serializers.ListField()
    missing_requirements = serializers.ListField(child=serializers.CharField())


class RecommendedAgentSerializer(serializers.ModelSerializer):
    agency_name = serializers.CharField(source="agent_profile.agency_name", read_only=True)
    phone_number = serializers.CharField(source="agent_profile.phone_number", read_only=True)
    whatsapp_number = serializers.CharField(source="agent_profile.whatsapp_number", read_only=True)
    is_verified = serializers.BooleanField(source="agent_profile.is_verified", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "agency_name",
            "phone_number", "whatsapp_number", "is_verified",
        ]


class InquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = [
            "id", "house", "conversation", "customer_name", "phone_number", "message", "status", "created_at"
        ]
        read_only_fields = ["id", "status", "created_at"]


class ViewingRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewingRequest
        fields = [
            "id", "house", "conversation", "customer_name", "phone_number", "preferred_at", "notes", "status", "created_at"
        ]
        read_only_fields = ["id", "status", "created_at"]
