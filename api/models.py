from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings

# instanceはProfileクラスを参照
# fileNameはフロントでユーザーが送信したファイル名
def upload_avatar_path(instance, filename):
    # 拡張子を取得してextに格納（.jpg .png など）
    ext = filename.split('.')[-1]
    # avatarsフォルダに格納
    return '/'.join(['avatars', str(instance.userProfile.id)+str(instance.nickName)+str(".")+str(ext)])

def upload_post_path(instance, filename):
    # 上に同じ
    ext = filename.split('.')[-1]
    return '/'.join(['posts', str(instance.userPost.id)+str(instance.title)+str(".")+str(ext)])

# デフォルトがusernameなので、emailを使ってログインする場合は改変が必要
class UserManager(BaseUserManager):
    # 今回はメールアドレスとパスワードのみ
    def create_user(self, email, password=None):

        if not email:
            raise ValueError('Email is must')

        user = self.model(
            # emailの正規化（大文字を小文字になど）
            email=self.normalize_email(email)
        )

        # パスワードをハッシュ化してから設定
        user.set_password(password)
        # 作ったuserをデータベースに保存
        user.save(using=self._db)

        return user


    def create_superuser(self, email, password):
        # is_activeでアカウントの有効、無効を操作可能
        user = self.create_user(email, password)
        # Dashboardにログインする権限
        user.is_staff = True
        # Dashboardにログインしデータベースの内容を変更できる権限
        user.is_superuser = True
        user.save(using=self._db)

        return user

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()
    # こうしておくと、Userモデルのインスタンスからobjects.create_userでユーザー作成ができるようになる

    # defaultはusernameなので変更
    USERNAME_FIELD = 'email'

    # emailの内容を文字列として返す
    def __str__(self):
        return self.email

class Profile(models.Model):
    nickName = models.CharField(max_length=20)
    userProfile = models.OneToOneField(
        # 認証ユーザーとOnetoOneで紐づける
        settings.AUTH_USER_MODEL, related_name='userProfile',
        # 認証ユーザーが削除されれば同時に削除（CASCADE）
        on_delete=models.CASCADE
    )
    liked_posts = models.ManyToManyField('Post', through='Like')
    created_on = models.DateTimeField(auto_now_add=True)
    img = models.ImageField(blank=True, null=True, upload_to=upload_avatar_path)

    # nickNameを文字列として返す
    def __str__(self):
        return self.nickName


class Post(models.Model):
    title = models.CharField(max_length=100)
    # OnetoManyを表現するためのForeignKey
    userPost = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='userPost',
        on_delete=models.CASCADE
    )
    liked_by = models.ManyToManyField('Profile', through='Like') 
    created_on = models.DateTimeField(auto_now_add=True)
    img = models.ImageField(blank=True, null=True, upload_to=upload_post_path)
    # liked = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked', blank=True)


    def __str__(self):
        return self.title


class Like(models.Model):
    like_post = models.ForeignKey(Post, related_name="liked_post", on_delete=models.CASCADE, blank=True, null=True)
    liked_by = models.ForeignKey(Profile, related_name="likd_by", on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return str(self.liked_by) + ' likes ' + str(self.like_post)


class Comment(models.Model):
    text = models.CharField(max_length=100)
    userComment = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='userComment',
        on_delete=models.CASCADE
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.text
