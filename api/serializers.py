from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Profile, Post, Comment, Like

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        # modelsのUserを取得
        model = get_user_model()
        fields = ('id', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    # emailとpasswordが問題なければ、validate後のデータがvalidated_dataに格納される
    def create(self, validated_data):

        user = get_user_model().objects.create_user(**validated_data)
        return user

class ProfileSerializer(serializers.ModelSerializer):

    # 元々auto_now_addの内容は読みにくいので下記で加工する
    created_on = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)

    class Meta:
        # 元はmodelsのProfileモデル
        model = Profile
        fields = ('id', 'nickName', 'userProfile', 'created_on', 'img')
        # viewsでログインユーザーを自動で識別してuserProfileに格納するロジックを書く
        extra_kwargs = {'userProfile': {'read_only': True}}


class PostSerializer(serializers.ModelSerializer):
    liked_by = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Profile.objects.all()
    )
    created_on = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)

    class Meta:
        model = Post
        fields = ('id', 'title', 'userPost', 'created_on', 'img', 'liked_by')
        # viewsでログインユーザーを自動で識別してuserPostに格納するロジックを書く
        extra_kwargs = {'userPost': {'read_only': True}}

    def update(self, instance, validated_data):
        liked_by = validated_data.pop('liked_by')
        for i in liked_by:
            instance.liked_by.add(i)
        instance.save()
        return instance

class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ("liked_by", "like_post")
        

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('id', 'text', 'userComment', 'post')
        # viewsでログインユーザーを自動で識別してuserCommentに格納するロジックを書く
        # フロント側で識別処理を書かなくてよくなる
        extra_kwargs = {'userComment': {'read_only': True}}