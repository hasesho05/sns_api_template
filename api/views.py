from django.http import HttpResponse, JsonResponse, HttpResponseNotFound
from django.views import View
from rest_framework import viewsets
from rest_framework import permissions
from django.db.models import Q
from .serializers import *
from .models import *
from . import utils
from django.conf import settings

from rest_framework.response import Response
from rest_framework.decorators import action
import hashlib
import random
import time

from .permissions import *
from .permissions import _permit_denied, _permit_only_owner, _permit_require_params, _permit_only_owner_for_list
from .validations import *
from .decorators import get_account, getAccount
from .jwt_token import jwt_encode, jwt_decode

from gmail_api import sendmail


def create_notification(account_id, type, initiator_id, target_post_id=None):
    notification = Notification.objects.create(
        account_id=account_id,
        type=type,
        initiator_id=initiator_id,
    )
    if type == "like":
        post = Post.objects.filter(id=target_post_id).first()
        notification.target_post = post
    elif type == "follow":
        post = Post.objects.filter(id=target_post_id).first()
        notification.target_post = post
    notification.save()

    return notification


class AuthenticateView(utils.DisabledCRUDMixin):
    queryset = Account.objects.all().order_by("-created_at")
    serializer_class = AccountSerializer

    @action(detail=False, methods=["post"])
    def authenticated(self, request, *args, **kwargs):
        getAccount(request)
        if request.is_authenticated:
            serializer = self.get_serializer(request.account)
            return Response({"status": "success", "data": serializer.data})
        else:
            return Response({"status": "failed", "message": "token is not provided."})

    @action(detail=False, methods=["post"])
    def login(self, request, *args, **kwargs):
        login_query = request.data.get("login_query")
        if not login_query:
            login_query = request.data.get("email")
        encrypted_password = hashlib.sha256(request.data["password"].encode()).hexdigest()

        account = Account.objects.filter(Q(email=login_query) | Q(account_id=login_query)).first()
        if account and account.encrypted_password == encrypted_password:
            serializer = self.get_serializer(account)
            token = jwt_encode(serializer.data)
            return Response({"status": "success", "data": {"token": token, "account_id": account.account_id}})
        else:
            return Response({"status": "failed", "data": {}})

    @action(detail=False, methods=["post"])
    def signup(self, request, *args, **kwargs):
        self.validate_signup(request)
        email = request.data.get("email")
        encrypted_password = hashlib.sha256(request.data.get("password").encode()).hexdigest()
        username = request.data.get("username")

        existing_account = Account.objects.filter(account_id=email.split("@")[0].replace("+", "_"))
        if len(existing_account) == 0:
            account_id = email.split("@")[0].replace("+", "_")
        else:
            account_id = email.split("@")[0].replace("+", "_") + "_" + str(len(existing_account))

        account = Account.objects.create(
            account_id=account_id, username=username, email=email, encrypted_password=encrypted_password
        )

        # Create a post
        posts = [""]
        while len(posts) != 0:
            addr1 = str(random.randint(101, 999)).zfill(3)
            addr2 = str(random.randint(1, 2)).zfill(2)
            addr3 = str(random.randint(1, 9999)).zfill(4)
            posts = Post.objects.filter(address=f"post avenue {addr1}-{addr2}-{addr3}")

        post = Post.objects.create(account_id=account.id)
        post.name = f"{username}'s post"
        post.address = f"post avenue {addr1}-{addr2}-{addr3}"
        post.save()

        return self.login(request, *args, **kwargs)

    @action(detail=False, methods=["post"])
    def change_password(self, request, *args, **kwargs):
        getAccount(request)
        success = False
        if request.is_authenticated:
            current_password = request.data["current_password"]
            new_password = request.data["new_password"]
            encrypted_current_password = hashlib.sha256(current_password.encode()).hexdigest()
            encrypted_new_password = hashlib.sha256(new_password.encode()).hexdigest()

            if request.account.encrypted_password == encrypted_current_password:
                request.account.encrypted_password = encrypted_new_password
                request.account.save()
                success = True

        if success:
            return Response({"status": "success"})
        else:
            return Response({"status": "failed"})

    @action(detail=False, methods=["post"])
    def change_email(self, request, *args, **kwargs):
        getAccount(request)
        success = False
        if request.is_authenticated:
            email = request.data["email"]
            request.account.email = email
            request.account.email_verified = False
            request.account.save()
            success = True

        if success:
            return Response({"status": "success"})
        else:
            return Response({"status": "failed"})

    @action(detail=False, methods=["post"])
    def reset_password(self, request, *args, **kwargs):
        t = request.data.get("t")
        new_password = request.data.get("new_password")
        success = False
        verification = Verification.objects.filter(code=t).first()

        if verification and verification.verified and new_password:
            encrypted_new_password = hashlib.sha256(new_password.encode()).hexdigest()
            verification.account.encrypted_password = encrypted_new_password
            verification.account.save()
            success = True

        if success:
            return Response({"status": "success"})
        else:
            return Response({"status": "failed"})

    def validate_signup(self, request):
        email = request.data.get("email")
        # account_id = request.data.get('account_id')
        password = request.data.get("password")
        validate_account_duplication(email)
        # validate_account_id(account_id)
        validate_password(password)


class AccountViewSet(utils.ModelViewSet):
    queryset = Account.objects.all().order_by("-created_at")
    serializer_class = AccountPublicSerializer
    permission_classes = []
    removed_methods = ["partial_update", "destroy"]

    @permit_denied
    def list(self, request, *args, **kwargs):
        _permit_require_params(request, params=["account_id"])

        queryset = self.get_queryset()
        queryset = self.queryset_filter(queryset, request.GET)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"status": "success", "data": serializer.data})

    @permit_denied
    def create(self, request, *args, **kwargs):
        encrypted_password = hashlib.sha256(request.data["password"].encode()).hexdigest()
        account = Account.objects.create(
            username=request.data["username"], email=request.data["email"], encrypted_password=encrypted_password
        )
        serializer = self.get_serializer(account)
        return Response({"status": "success", "data": serializer.data})

    @get_account
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.is_authenticated and request.account.id == instance.id:
            serializer = AccountSerializer(instance, context={"request": request})
        else:
            serializer = self.get_serializer(instance)
        return Response({"status": "success", "data": serializer.data})

    @get_account
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        if request.is_authenticated and request.account.id == instance.id:
            serializer = AccountSerializer(instance, data=request.data, partial=partial, context={"request": request})
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"status": "success", "data": serializer.data})
        else:
            _permit_denied()
            # serializer = self.get_serializer(instance, data=request.data, partial=partial)


class VerificationViewSet(utils.ModelViewSet):
    queryset = Verification.objects.all().order_by("-created_at")
    serializer_class = VerificationSerializer
    permission_classes = []
    removed_methods = ["retrieve", "update", "partial_update", "destroy"]

    @permit_denied
    def list(self, request, *args, **kwargs):
        pass

    @get_account
    def create(self, request, *args, **kwargs):
        code = str(time.time()) + ":T9etBHY9NuthTD^b"
        code_encoded = hashlib.sha256(code.encode()).hexdigest()
        verification_type = request.data.get("verification_type")

        sender = "no-reply@art-tunes.net"
        to = ""
        subject = ""
        message = ""
        attach_file_path = None

        if verification_type == "email":
            account = request.account
            to = request.account.email
            subject = "Email Verification"
            verification_url = f"{settings.FRONT_URL}/verify/?t={code_encoded}"
            message = "テストメール (メール認証)\n\nこのリンクをクリックしてください。\n" + verification_url

        elif verification_type == "reset-password":
            login_query = request.data.get("login_query")
            account = Account.objects.filter(Q(email=login_query) | Q(account_id=login_query)).first()

            if account:
                to = account.email
                subject = "Password reset request."
                verification_url = f"{settings.FRONT_URL}/password-reset/?t={code_encoded}"
                message = "テストメール (メール認証)\n\nこのリンクをクリックしてください。\n" + verification_url

        if to != "":
            sendmail.main(sender, to, subject, message, attach_file_path)

            verification = Verification.objects.create(
                account=account,
                verification_type=verification_type,
                code=code_encoded,
            )

            serializer = self.get_serializer(verification, many=False)
            return Response({"status": "success", "data": serializer.data})
        else:
            return Response({"status": "failed"})

    @action(detail=False, methods=["post"])
    def verify(self, request, *args, **kwargs):
        getAccount(request)
        success = False
        code = request.data.get("t")

        verification = Verification.objects.filter(code=code).first()
        if verification and not verification.verified:
            if verification.verification_type == "email" and verification.account == request.account:
                verification.account.email_verified = True
                verification.account.save()
                verification.verified = True
                verification.save()
                success = True

            elif verification.verification_type == "reset-password":
                verification.verified = True
                verification.save()
                success = True

        if success:
            return Response({"status": "success"})
        else:
            return Response({"status": "failed"})


class SearchViewSet(View):
    def get(self, request, *args, **kwargs):
        query = ""
        tab = "top"
        if "query" in request.GET.keys():
            query = request.GET["query"]
        if "tab" in request.GET.keys():
            tab = request.GET["tab"]

        posts = Post.objects.filter(
            Q(account__username__icontains=query)
            | Q(account__account_id__icontains=query)
            | Q(name__icontains=query)
            | Q(address__icontains=query)
            | Q(statement__icontains=query)
        )

        token = request.GET.get("token")
        decoded_token = jwt_decode(token)
        if decoded_token["status"] == "success":
            user_accessed = Account.objects.get(id=decoded_token["data"]["id"])
        else:
            user_accessed = None

        posts_temp = []
        for post in posts:
            if post not in posts_temp:
                if user_accessed and Post.objects.filter(account=user_accessed, following=post).first():
                    post.followed = True
                else:
                    post.followed = False
                posts_temp.append(post)
        posts = posts_temp

        return JsonResponse(
            {
                "status": "success",
                "data": {
                    "query": query,
                    "tab": tab,
                    "posts": PostSerializer(posts, many=True).data,
                },
            }
        )


class PostViewSet(utils.ModelViewSet):
    queryset = Post.objects.all().order_by("-created_at")
    serializer_class = PostSerializer
    permission_classes = [PermitIsAuthenticatedOrReadOnly]
    removed_methods = ["partial_update"]

    @permit_only_owner
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        queryset = self.queryset_filter(queryset, request.GET)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"status": "success", "data": serializer.data})

    @permit_only_owner
    def create(self, request, *args, **kwargs):
        post = Post.objects.create(
            account_id=request.data.get("account_id"),
            image1=request.data.get("image1"),
            image2=request.data.get("image2"),
            image3=request.data.get("image3"),
            title=request.data.get("title"),
            content=request.data.get("content"),
            category_id=request.data.get("category_id"),
            tags=request.data.get("tags"),
            status=request.data.get("status"),
        )
        serializer = self.get_serializer(post)
        return Response({"status": "success", "data": serializer.data})

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        _permit_only_owner(request, instance)

        for key, value in request.data.items():

            if key == "category_id" and value == 0:
                category = Category.objects.filter(name=value).first()
                instance.category = category
            else:
                if value == "":
                    value = None
                setattr(instance, key, value)
        instance.save()
        serializer = self.get_serializer(instance)
        return Response({"status": "success", "data": serializer.data})

    @action(detail=False, methods=["put"])
    def multiple_update(self, request, *args, **kwargs):
        Posts = request.data.get("data")
        for item in Posts:
            post = Post.objects.get(id=item["id"])
            _permit_only_owner(request, post)

            for key, value in item.items():
                if key == "account" or key == "category" or key.find("image") != -1:
                    continue
                setattr(post, key, value)
            post.save()

        return Response({"status": "success"})


class NotificationViewSet(utils.ModelViewSet):
    queryset = Notification.objects.all().order_by("-created_at")
    serializer_class = NotificationSerializer
    permission_classes = [PermitIsAuthenticated]
    removed_methods = ["retrieve", "update", "partial_update", "destroy"]

    @permit_only_owner
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        queryset = self.queryset_filter(queryset, request.GET)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"status": "success", "data": serializer.data})

    def create(self, request, *args, **kwargs):
        _permit_only_owner(request)

        notification = Notification.objects.create(
            account_id=request.data["account_id"],
            type=request.data["type"],
            initiator_id=request.data["initiator_id"],
        )
        if notification.type == "like":
            notification.targer_post_id = request.data["targer_post_id"]
        elif notification.type == "follow":
            notification.target_post_id = request.data["target_post_id"]
        serializer = self.get_serializer(notification)
        return Response({"status": "success", "data": serializer.data})

    @action(detail=False, methods=["post"])
    def multiple_read(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        _permit_only_owner_for_list(request, queryset)

        ids = request.data["ids"]
        for id in ids:
            notification = Notification.objects.filter(id=id).first()
            notification.is_read = True
            notification.save()
        return Response({"status": "success"})
