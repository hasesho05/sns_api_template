import os
import uuid
from django.db import models
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.db.models import Count, OuterRef, Subquery
from ckeditor.fields import RichTextField

USER_TYPE = (
    ("general", "一般"),
    ("company", "法人"),
    ("group", "団体"),
    ("government", "行政"),
)

VERIFICATION_TYPES = [
    ("email", "メールアドレス"),
    ("reset-password", "パスワードリセット"),
]


NOTIFICATION_TYPE = (
    ("follow", "フォロー"),
    ("follow_request", "フォローリクエスト"),
    ("like", "いいね"),
)


class Account(models.Model):
    def __str__(self):
        return f"{self.id} | {self.account_id} | {self.username} | {self.email}"

    def user_directory_path(instance, filename):
        return "user_icon/user_{0}/{1}".format(instance.id, filename)

    username = models.CharField(verbose_name="ユーザー名", max_length=128)
    account_id = models.CharField(verbose_name="アカウントID", max_length=128, unique=True)
    email = models.CharField(verbose_name="メールアドレス", max_length=128, unique=True)
    user_icon = models.ImageField(verbose_name="アイコン", upload_to=user_directory_path, null=True, blank=True)
    user_type = models.CharField(verbose_name="ユーザータイプ", max_length=128, choices=USER_TYPE, default=USER_TYPE[0][0])
    profile = models.TextField(verbose_name="プロフィール", null=True, blank=True)
    website_link = models.CharField(verbose_name="ウェブサイト", max_length=256, null=True, blank=True)
    phone_number = models.CharField(verbose_name="電話番号", max_length=128, null=True, blank=True)
    birth_date = models.DateField(verbose_name="生年月日", null=True, blank=True)
    instagram_link = models.CharField(verbose_name="Instagram", max_length=128, null=True, blank=True)
    facebook_link = models.CharField(verbose_name="Facebook", max_length=128, null=True, blank=True)
    twitter_link = models.CharField(verbose_name="Twitter", max_length=128, null=True, blank=True)
    linkedin_link = models.CharField(verbose_name="LinkedIn", max_length=128, null=True, blank=True)
    youtube_link = models.CharField(verbose_name="Youtube", max_length=128, null=True, blank=True)
    encrypted_password = models.CharField(verbose_name="パスワード", max_length=128)
    email_verified = models.BooleanField(verbose_name="メールアドレス確認済み", default=False)
    created_at = models.DateTimeField(verbose_name="作成日時", default=timezone.now)
    updated_at = models.DateTimeField(verbose_name="更新日時", default=timezone.now)


class Verification(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    verification_type = models.CharField(
        verbose_name="タイプ", max_length=128, default="email", choices=VERIFICATION_TYPES
    )
    code = models.CharField(verbose_name="確認コード", max_length=128)
    verified = models.BooleanField(verbose_name="確認済み", default=False)
    created_at = models.DateTimeField(verbose_name="作成日時", default=timezone.now)
    updated_at = models.DateTimeField(verbose_name="更新日時", default=timezone.now)

    def __str__(self):
        return f"{self.id} | {self.account} | {self.code}"


class Category(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(verbose_name="カテゴリー名", max_length=128)
    description = models.TextField(verbose_name="説明", null=True, blank=True)
    sort_order = models.IntegerField(verbose_name="並び順", default=1)
    created_at = models.DateTimeField(verbose_name="作成日時", default=timezone.now)
    updated_at = models.DateTimeField(verbose_name="更新日時", default=timezone.now)

    def __str__(self):
        return f"{self.id} | @{self.account.account_id} | {self.name}"


STATUS = (
    ("public", "公開"),
    ("private", "非公開"),
    ("draft", "下書き"),
)


class Post(models.Model):
    def __str__(self):
        return f"{self.id} | {self.title_original} | {self.account.username}"

    class Meta:
        ordering = ["-created_at"]

    def user_directory_path(instance, filename):
        return "art_images/user_{0}/{1}".format(instance.account.id, filename)

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="arts")
    image1 = models.FileField(verbose_name="画像1", upload_to=user_directory_path, null=False, blank=False)
    image2 = models.FileField(verbose_name="画像2", upload_to=user_directory_path, null=True, blank=True)
    image3 = models.FileField(verbose_name="画像3", upload_to=user_directory_path, null=True, blank=True)
    title = models.CharField(verbose_name="タイトル", max_length=128, default="Original Title")
    content = models.TextField(verbose_name="内容", null=True, blank=True)
    tags = models.CharField(verbose_name="タグ", max_length=256, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="arts", null=True, blank=True)
    status = models.CharField(verbose_name="ステータス", max_length=128, default="", choices=STATUS, null=True, blank=True)
    created_at = models.DateTimeField(verbose_name="作成日時", default=timezone.now)
    updated_at = models.DateTimeField(verbose_name="更新日時", default=timezone.now)


class Notification(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(verbose_name="通知タイプ", max_length=128, choices=NOTIFICATION_TYPE)
    initiator = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="notification_initiators")
    target_post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="notification_target_arts", null=True, blank=True
    )
    is_read = models.BooleanField(verbose_name="既読", default=False)
    created_at = models.DateTimeField(verbose_name="作成日時", default=timezone.now)
    updated_at = models.DateTimeField(verbose_name="更新日時", default=timezone.now)

    def __str__(self):
        return f"{self.id} | @{self.account.account_id} | {self.type}"

    class Meta:
        ordering = ["-created_at"]


class FollowStudio(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="follows_account")  # フォローする人
    following = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="followers")  # フォローされる人
    created_at = models.DateTimeField(verbose_name="作成日時", default=timezone.now)
    updated_at = models.DateTimeField(verbose_name="更新日時", default=timezone.now)

    def __str__(self):
        return f"{self.id} | @{self.account.account_id} | {self.following.name}"

    class Meta:
        unique_together = ("account", "following")
