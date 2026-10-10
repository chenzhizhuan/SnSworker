"""账号登录 / 唯一性大小写不敏感回归。

与登录匹配（MultiFieldAuthBackend username__iexact / email__iexact）及
唯一性校验（validate_unique_username / validate_unique_email 的 iexact）
配套：任意大小写变体应命中同一账号，且大小写变体不允许注册并存。
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.users.auth.authentication import MultiFieldAuthBackend
from apps.users.auth.validators import validate_unique_email, validate_unique_username

User = get_user_model()


class CaseInsensitiveLoginTests(TestCase):
    def setUp(self):
        self.backend = MultiFieldAuthBackend()
        self.user = User.objects.create_user(
            username='J0325',
            nickname='谢蒙萌',
            email='J0325@huaxiyuan.invalid',
            password='Ai345678',
        )

    def test_username_exact_still_works(self):
        self.assertEqual(
            self.backend.authenticate(None, username='J0325', password='Ai345678'),
            self.user,
        )

    def test_username_lowercase_variant_logs_in(self):
        self.assertEqual(
            self.backend.authenticate(None, username='j0325', password='Ai345678'),
            self.user,
        )

    def test_username_mixed_case_variant_logs_in(self):
        self.assertEqual(
            self.backend.authenticate(None, username='J0325', password='Ai345678'),
            self.user,
        )

    def test_email_lowercase_variant_logs_in(self):
        self.assertEqual(
            self.backend.authenticate(None, username='j0325@huaxiyuan.invalid', password='Ai345678'),
            self.user,
        )

    def test_password_is_still_case_sensitive(self):
        self.assertIsNone(
            self.backend.authenticate(None, username='j0325', password='ai345678'),
        )

    def test_wrong_identifier_does_not_hit(self):
        self.assertIsNone(
            self.backend.authenticate(None, username='j9999', password='Ai345678'),
        )


class LoginInputWhitespaceNormalizationTests(TestCase):
    """登录入参首尾空白归一。

    真实事故（2026-10-10）：Windows 手输密码在输入法切换时带入前导空格，
    视觉不可见但哈希不匹配，反复报「用户名或密码错误」。

    收口语义（MultiFieldAuthBackend 双通道）：
    - 密码「精确优先 + 空白归一重试」：第一通道兼容存量带空白的历史密码
      （validators 禁空白规则之前注册的凭据），第二通道仅当首尾有空白时
      用 strip 后的密码重试；中部空白不归一，仍按不匹配处理。
    - 标识符（邮箱/用户名/手机号）本身不含空白，统一 strip。
    - login_user 端点在限流前 strip username，保证限流键与认证一致。
    """

    def setUp(self):
        self.backend = MultiFieldAuthBackend()
        self.user = User.objects.create_user(
            username='chenzhizhuan',
            email='285625881@qq.com',
            password='Angel192023',
        )

    def test_password_with_leading_space_logs_in(self):
        self.assertEqual(
            self.backend.authenticate(None, username='chenzhizhuan', password=' Angel192023'),
            self.user,
        )

    def test_password_with_trailing_space_logs_in(self):
        self.assertEqual(
            self.backend.authenticate(None, username='chenzhizhuan', password='Angel192023 '),
            self.user,
        )

    def test_password_with_surrounding_spaces_logs_in(self):
        self.assertEqual(
            self.backend.authenticate(None, username='chenzhizhuan', password=' Angel192023 '),
            self.user,
        )

    def test_password_inner_space_still_rejected(self):
        # 中部空格不会被 strip：合法密码不含空格，中部空格必然是输错
        self.assertIsNone(
            self.backend.authenticate(None, username='chenzhizhuan', password='Angel 192023'),
        )

    def test_identifier_with_surrounding_spaces_logs_in(self):
        self.assertEqual(
            self.backend.authenticate(None, username=' chenzhizhuan ', password='Angel192023'),
            self.user,
        )

    def test_email_with_surrounding_spaces_logs_in(self):
        self.assertEqual(
            self.backend.authenticate(None, username=' 285625881@qq.com ', password='Angel192023'),
            self.user,
        )

    def test_blank_identifier_returns_none(self):
        self.assertIsNone(
            self.backend.authenticate(None, username='   ', password='Angel192023'),
        )

    def test_login_user_endpoint_normalizes_credentials(self):
        # 端点级归一：login_user 在限流前 strip username；
        # password 由后端双通道归一（精确失败后空白重试）
        from django.test import RequestFactory

        from apps.users.auth.api.auth_routes import login_user
        from apps.users.auth.schemas import UserLoginSchema

        factory = RequestFactory()
        request = factory.post('/api/auth/login')
        data = UserLoginSchema(username=' chenzhizhuan ', password=' Angel192023 ')

        status, payload = login_user(request, data)

        self.assertEqual(status, 200)
        self.assertTrue(payload.success)


class CaseInsensitiveUniquenessTests(TestCase):
    def setUp(self):
        User.objects.create_user(
            username='SJ2604',
            email='SJ2604@huaxiyuan.invalid',
            password='Ai345678',
        )

    def test_username_case_variant_rejected(self):
        with self.assertRaises(ValidationError):
            validate_unique_username('sj2604')

    def test_email_case_variant_rejected(self):
        with self.assertRaises(ValidationError):
            validate_unique_email('sj2604@huaxiyuan.invalid')

    def test_excluding_self_allows_own_username(self):
        user = User.objects.get(username='SJ2604')
        # 修改自己资料时重校验自己的用户名应通过
        validate_unique_username('sj2604', user_id=user.id)

    def test_distinct_username_still_accepted(self):
        validate_unique_username('sj2605')

    def test_generate_unique_username_skips_case_variants(self):
        from apps.users.auth.api.auth_routes import _generate_unique_username

        generated = _generate_unique_username(email='sj2604@huaxiyuan.invalid')
        # sj2604 已被占用（大小写不敏感），自动生成应绕开而非复用
        self.assertNotEqual(generated.lower(), 'sj2604')
