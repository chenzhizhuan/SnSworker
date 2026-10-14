package com.tabtin.mobile.features.auth

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tabtin.mobile.data.model.AppError
import com.tabtin.mobile.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.UUID
import javax.inject.Inject

/**
 * 「忘记密码」表单校验口径（纯函数，可单测）。
 *
 * 与后端 validators.validate_user_password 对齐的确定性子集：
 * - 长度 8~128；
 * - 不含任何空白字符；
 * - 不含 CJK 文字（防把报错文案粘贴进密码框）；
 * - 大写 / 小写 / 数字 / 特殊字符至少 3 种。
 *
 * Django 内置密码验证器（常见密码字典、与账号相似度）不做客户端镜像，
 * 由后端权威校验后回显 message。
 */
public object PasswordResetFormRules {
    private val emailPattern = Regex("""^[^\s@]+@[^\s@]+\.[^\s@]+$""")
    private val codePattern = Regex("""^\d{6}$""")
    private val cjkPattern = Regex("""[\u3000-\u303F\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]""")

    /** 邮箱输入即时净化：去掉首尾空白与所有内部空白；邮箱本身不含空白。 */
    public fun editingIdentifier(input: String): String =
        input.filterNot { it.isWhitespace() }

    /** 验证码输入复用登录页六位数字口径。 */
    public fun editingCode(input: String): String = LoginVerificationCode.editingValue(input)

    public fun isEmail(identifier: String): Boolean =
        emailPattern.matches(identifier.trim().lowercase())

    public fun isVerificationCode(code: String): Boolean =
        codePattern.matches(code)

    /** 对齐后端「密码必须包含大写/小写/数字/特殊字符中的至少 3 种」等确定性规则。 */
    public fun isStrongPassword(password: String): Boolean {
        if (password.length !in 8..128) return false
        if (password.any { it.isWhitespace() }) return false
        if (cjkPattern.containsMatchIn(password)) return false
        val hasUpper = password.any { it.isUpperCase() }
        val hasLower = password.any { it.isLowerCase() }
        val hasDigit = password.any { it.isDigit() }
        val hasSpecial = password.any { !it.isLetterOrDigit() && !it.isWhitespace() }
        return listOf(hasUpper, hasLower, hasDigit, hasSpecial).count { it } >= 3
    }
}

public data class ForgotPasswordUiState(
    val identifier: String = "",
    val verificationCode: String = "",
    val newPassword: String = "",
    val isSendingCode: Boolean = false,
    val isSubmitting: Boolean = false,
    val codeSent: Boolean = false,
    val cooldownSeconds: Int = 0,
    val error: String? = null,
    val fieldError: String? = null,
    val resetSucceeded: Boolean = false,
)

@HiltViewModel
public class ForgotPasswordViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    @ApplicationContext private val context: Context,
) : ViewModel() {

    private var verificationChallengeKey: String? = null

    private val _uiState = MutableStateFlow(ForgotPasswordUiState())
    public val uiState: StateFlow<ForgotPasswordUiState> = _uiState.asStateFlow()

    public fun updateIdentifier(identifier: String) {
        val next = PasswordResetFormRules.editingIdentifier(identifier)
        if (next != _uiState.value.identifier) verificationChallengeKey = null
        _uiState.value = _uiState.value.copy(identifier = next, error = null, fieldError = null)
    }

    public fun updateCode(code: String) {
        _uiState.value = _uiState.value.copy(
            verificationCode = PasswordResetFormRules.editingCode(code),
            error = null,
            fieldError = null,
        )
    }

    public fun updateNewPassword(password: String) {
        _uiState.value = _uiState.value.copy(newPassword = password, error = null, fieldError = null)
    }

    public fun sendCode() {
        val state = _uiState.value
        val identifier = state.identifier.trim().lowercase()
        if (!PasswordResetFormRules.isEmail(identifier)) {
            // 后端 reset-password 只支持邮箱 / 手机号标识；公网短信已禁用，
            // 工号用户唯一可靠找回通道是注册邮箱，这里引导输入邮箱。
            _uiState.value = state.copy(fieldError = fieldText(ForgotPasswordField.EMAIL))
            return
        }
        viewModelScope.launch {
            val challengeKey = UUID.randomUUID().toString()
            _uiState.value = _uiState.value.copy(isSendingCode = true, error = null, fieldError = null)
            authRepository.sendPasswordResetCode(identifier, challengeKey)
                .onSuccess {
                    verificationChallengeKey = challengeKey
                    _uiState.value = _uiState.value.copy(
                        isSendingCode = false,
                        codeSent = true,
                        cooldownSeconds = 60,
                    )
                    startCooldown()
                }
                .onFailure { e ->
                    _uiState.value = _uiState.value.copy(
                        isSendingCode = false,
                        error = errorMessage(e),
                    )
                }
        }
    }

    public fun submit() {
        val state = _uiState.value
        val identifier = state.identifier.trim().lowercase()
        val challengeKey = verificationChallengeKey
        when {
            !PasswordResetFormRules.isEmail(identifier) -> {
                _uiState.value = state.copy(fieldError = fieldText(ForgotPasswordField.EMAIL))
                return
            }
            !PasswordResetFormRules.isVerificationCode(state.verificationCode) -> {
                _uiState.value = state.copy(fieldError = fieldText(ForgotPasswordField.CODE))
                return
            }
            !PasswordResetFormRules.isStrongPassword(state.newPassword) -> {
                _uiState.value = state.copy(fieldError = fieldText(ForgotPasswordField.PASSWORD))
                return
            }
            challengeKey == null -> {
                // 验证码还没发过（或换邮箱后失效）：引导先获取验证码。
                _uiState.value = state.copy(fieldError = fieldText(ForgotPasswordField.CODE_NOT_SENT))
                return
            }
        }
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSubmitting = true, error = null, fieldError = null)
            authRepository.resetPassword(identifier, state.verificationCode, state.newPassword)
                .onSuccess {
                    _uiState.value = _uiState.value.copy(
                        isSubmitting = false,
                        resetSucceeded = true,
                    )
                }
                .onFailure { e ->
                    _uiState.value = _uiState.value.copy(
                        isSubmitting = false,
                        error = errorMessage(e),
                    )
                }
        }
    }

    private fun fieldText(field: ForgotPasswordField): String =
        context.getString(field.messageRes)

    private fun errorMessage(e: Throwable): String = when (e) {
        is AppError -> e.toUserMessage(context)
        else -> context.getString(com.tabtin.mobile.R.string.error_request_failed)
    }

    private fun startCooldown() {
        viewModelScope.launch {
            while (_uiState.value.cooldownSeconds > 0) {
                kotlinx.coroutines.delay(1000)
                _uiState.value = _uiState.value.copy(
                    cooldownSeconds = _uiState.value.cooldownSeconds - 1,
                )
            }
        }
    }
}

internal enum class ForgotPasswordField(val messageRes: Int) {
    EMAIL(com.tabtin.mobile.R.string.auth_forgot_error_email),
    CODE(com.tabtin.mobile.R.string.auth_error_invalid_code),
    CODE_NOT_SENT(com.tabtin.mobile.R.string.auth_forgot_error_code_not_sent),
    PASSWORD(com.tabtin.mobile.R.string.auth_forgot_error_weak_password),
}
