from rest_framework import generics
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from . import serializers
from .models import Profile, Post, Comment, Like

# 新規作成に特化したviewを選択
class CreateUserView(generics.CreateAPIView):
    serializer_class = serializers.UserSerializer
    permission_classes = {AllowAny,}

# 新規作成や更新の必要があるのでModelViewSetを継承
class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = serializers.ProfileSerializer

    # userProfileをread_onlyにして自動割当カスタムにしたため
    def perform_create(self, serializer):
        # self.request.userは現在ログインしているユーザー
        serializer.save(userProfile=self.request.user)

class MyProfileListView(generics.ListAPIView):
    queryset = Profile.objects.all()
    serializer_class = serializers.ProfileSerializer

    # ログインしているユーザーを自動で返してくれる
    def get_queryset(self):
        return self.queryset.filter(userProfile=self.request.user)


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = serializers.PostSerializer

    # その時ログインしているユーザーを割り当てて投稿を作成
    def perform_create(self, serializer):
        serializer.save(userPost=self.request.user)

class LikeViewSet(viewsets.ModelViewSet):
    queryset = Like.objects.all()
    serializer_class = serializers.LikeSerializer

    def perform_create(self, serializer):
        serializer.save(like_from=self.request.user)
    

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = serializers.CommentSerializer

    def perform_create(self, serializer):
        serializer.save(userComment=self.request.user)