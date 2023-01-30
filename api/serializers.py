from .models import *
from rest_framework import serializers


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id",
            "username",
            "account_id",
            "email",
            "user_icon",
            "user_type",
            "profile",
            "website_link",
            "phone_number",
            "birth_date",
            "language",
            "instagram_link",
            "facebook_link",
            "twitter_link",
            "linkedin_link",
            "youtube_link",
            "email_verified",
        ]

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            if value or value == "":
                setattr(instance, key, value)
        instance.save()
        return instance


class AccountPublicSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id",
            "username",
            "account_id",
            "user_icon",
            "profile",
            "website_link",
            "instagram_link",
            "facebook_link",
            "twitter_link",
            "linkedin_link",
            "youtube_link",
        ]


class PostSerializer(serializers.HyperlinkedModelSerializer):
    account = AccountPublicSerializer(read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "account",
            "image1",
            "image2",
            "image3",
            "title",
            "content",
            "category",
            "tags",
            "status",
        ]


class VerificationSerializer(serializers.HyperlinkedModelSerializer):
    account_id = serializers.SerializerMethodField()

    class Meta:
        model = Verification
        fields = ["id", "account_id", "verification_type"]

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            if value or value == "":
                setattr(instance, key, value)
        instance.save()
        return instance

    def get_account_id(self, obj):
        try:
            return obj.account.id
        except:
            return ""


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    account = AccountPublicSerializer(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "account", "items", "description", "sort_order"]


class NotificationSerializer(serializers.HyperlinkedModelSerializer):
    account = AccountPublicSerializer(read_only=True)
    initiator = AccountPublicSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "account", "type", "initiator", "target_art", "target_studio", "is_read"]
