package com.tabtin.mobile.features.auth

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.focus.FocusDirection
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.tabtin.mobile.R
import com.tabtin.mobile.features.profile.ProfileViewModel
import com.tabtin.mobile.ui.theme.AppLanguage

/**
 * 「忘记密码」页：注册邮箱 → 重置验证码 → 新密码，一屏完成。
 *
 * 验证码登录 / 注册入口在公网部署形态默认关停，这里复用后端不受关停限制的
 * reset_password 验证码通道，保证密码找回始终闭环——批量导入的工号用户
 * 只有初始密码，找回路径缺失会直接把人挡在门外。
 */
@Composable
public fun ForgotPasswordScreen(
    onBack: () -> Unit,
    viewModel: ForgotPasswordViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    val focusManager = LocalFocusManager.current
    val profileViewModel: ProfileViewModel = hiltViewModel()
    val language = profileViewModel.currentLanguage
    val isEnglish = language.isEnglishForLogin()
    var isPasswordVisible by rememberSaveable { mutableStateOf(false) }

    LoginPaperSystemBars()
    BackHandler(onBack = onBack)

    Scaffold(
        containerColor = LoginPaper,
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp),
        ) {
            ForgotPasswordTopBar(
                isEnglish = isEnglish,
                onBack = {
                    focusManager.clearFocus()
                    onBack()
                },
            )

            Spacer(Modifier.height(16.dp))
            Text(
                text = stringResource(R.string.auth_forgot_title),
                color = LoginInk,
                fontSize = 20.sp,
                fontWeight = FontWeight.ExtraBold,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                text = stringResource(R.string.auth_forgot_description),
                color = LoginMutedInk,
                fontSize = 11.sp,
                lineHeight = 16.sp,
            )
            Spacer(Modifier.height(16.dp))

            Column(modifier = Modifier.widthIn(max = 520.dp)) {
                if (state.resetSucceeded) {
                    ForgotPasswordSuccessPane(onBack = onBack)
                } else {
                    ForgotPasswordForm(
                        state = state,
                        isEnglish = isEnglish,
                        language = language,
                        isPasswordVisible = isPasswordVisible,
                        onPasswordVisibilityToggle = { isPasswordVisible = !isPasswordVisible },
                        onSendCode = viewModel::sendCode,
                        onSubmit = viewModel::submit,
                        onIdentifierChange = viewModel::updateIdentifier,
                        onCodeChange = viewModel::updateCode,
                        onNewPasswordChange = viewModel::updateNewPassword,
                        onBack = onBack,
                    )
                }
                Spacer(Modifier.height(24.dp))
            }
        }
    }
}

@Composable
private fun ForgotPasswordForm(
    state: ForgotPasswordUiState,
    isEnglish: Boolean,
    language: AppLanguage,
    isPasswordVisible: Boolean,
    onPasswordVisibilityToggle: () -> Unit,
    onSendCode: () -> Unit,
    onSubmit: () -> Unit,
    onIdentifierChange: (String) -> Unit,
    onCodeChange: (String) -> Unit,
    onNewPasswordChange: (String) -> Unit,
    onBack: () -> Unit,
) {
    val focusManager = LocalFocusManager.current

    EditorialLoginField(
        label = stringResource(R.string.auth_forgot_email_label),
        value = state.identifier,
        onValueChange = onIdentifierChange,
        placeholder = stringResource(R.string.auth_forgot_email_placeholder),
        keyboardOptions = KeyboardOptions(
            keyboardType = KeyboardType.Email,
            imeAction = ImeAction.Next,
        ),
        keyboardActions = KeyboardActions(
            onNext = { focusManager.moveFocus(FocusDirection.Down) },
        ),
    )
    Spacer(Modifier.height(8.dp))
    EditorialLoginField(
        label = stringResource(R.string.auth_code_label),
        value = state.verificationCode,
        onValueChange = onCodeChange,
        placeholder = stringResource(R.string.auth_code_placeholder),
        actionWidth = 104.dp,
        action = {
            LoginCodeAction(
                isSending = state.isSendingCode,
                countdownSeconds = state.cooldownSeconds,
                onClick = onSendCode,
            )
        },
        keyboardOptions = KeyboardOptions(
            keyboardType = KeyboardType.Number,
            imeAction = ImeAction.Next,
        ),
        keyboardActions = KeyboardActions(
            onNext = { focusManager.moveFocus(FocusDirection.Down) },
        ),
    )
    Spacer(Modifier.height(8.dp))
    EditorialLoginField(
        label = stringResource(R.string.auth_forgot_new_password_label),
        value = state.newPassword,
        onValueChange = onNewPasswordChange,
        placeholder = stringResource(R.string.auth_forgot_new_password_placeholder),
        actionWidth = 52.dp,
        action = {
            LoginPasswordAction(
                language = language,
                isPasswordVisible = isPasswordVisible,
                onClick = onPasswordVisibilityToggle,
            )
        },
        visualTransformation = if (isPasswordVisible) {
            VisualTransformation.None
        } else {
            PasswordVisualTransformation()
        },
        keyboardOptions = KeyboardOptions(
            keyboardType = KeyboardType.Password,
            imeAction = ImeAction.Done,
        ),
        keyboardActions = KeyboardActions(onDone = { focusManager.clearFocus() }),
    )
    Spacer(Modifier.height(4.dp))
    Text(
        text = stringResource(R.string.auth_forgot_password_hint),
        color = LoginMutedInk,
        fontSize = 9.sp,
        lineHeight = 13.sp,
    )
    Spacer(Modifier.height(8.dp))
    LoginSubmitButton(
        loading = state.isSubmitting,
        enabled = state.identifier.isNotBlank() &&
            state.verificationCode.isNotBlank() &&
            state.newPassword.isNotBlank(),
        onClick = onSubmit,
        label = stringResource(R.string.auth_forgot_submit),
    )
    Spacer(Modifier.height(8.dp))

    state.fieldError?.let { message -> LoginErrorHint(message = message) }
    if (state.fieldError == null) {
        state.error?.let { message -> LoginErrorHint(message = message) }
    }
    Spacer(Modifier.height(8.dp))
    Text(
        text = if (isEnglish) "Back to sign in" else stringResource(R.string.auth_forgot_back),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(role = Role.Button, onClick = onBack)
            .padding(vertical = 6.dp),
        color = LoginBlue,
        fontSize = 11.sp,
        fontWeight = FontWeight.SemiBold,
        textAlign = TextAlign.Center,
    )
}

@Composable
private fun ForgotPasswordSuccessPane(onBack: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(8.dp))
        Text(
            text = stringResource(R.string.auth_forgot_success_title),
            color = LoginInk,
            fontSize = 14.sp,
            fontWeight = FontWeight.ExtraBold,
        )
        Spacer(Modifier.height(6.dp))
        Text(
            text = stringResource(R.string.auth_forgot_success_message),
            color = LoginMutedInk,
            fontSize = 11.sp,
            lineHeight = 16.sp,
        )
        Spacer(Modifier.height(16.dp))
        LoginSubmitButton(
            loading = false,
            enabled = true,
            onClick = onBack,
            label = stringResource(R.string.auth_forgot_back),
        )
    }
}

@Composable
private fun ForgotPasswordTopBar(
    isEnglish: Boolean,
    onBack: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(48.dp)
            .drawBehind {
                val strokeWidth = 1.dp.toPx()
                drawLine(
                    color = LoginInk,
                    start = Offset(0f, size.height - strokeWidth / 2f),
                    end = Offset(size.width, size.height - strokeWidth / 2f),
                    strokeWidth = strokeWidth,
                )
            },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = if (isEnglish) "← Back" else "← 返回",
            modifier = Modifier
                .clickable(role = Role.Button, onClick = onBack)
                .padding(vertical = 8.dp),
            color = LoginInk,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}
