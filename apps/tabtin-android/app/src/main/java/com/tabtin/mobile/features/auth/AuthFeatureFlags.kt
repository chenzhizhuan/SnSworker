package com.tabtin.mobile.features.auth

import com.tabtin.mobile.BuildConfig

/**
 * 认证入口编译期开关（集中入口，对齐 web / 桌面端 featureFlags）。
 *
 * 语义与后端 TABTIN_REGISTRATION_ENABLED / TABTIN_VERIFICATION_LOGIN_ENABLED 的
 * 公网部署形态对应，且与全端统一为「部署安全默认关停」：
 * 所有构建形态（dev/debug / release）默认关，仅显式注入
 * `-PTABTIN_VERIFICATION_LOGIN_ENABLED=true` / `-PTABTIN_REGISTRATION_ENABLED=true`
 * 才开启（build.gradle.kts 注入）。
 */
public object AuthFeatureFlags {
    /** 验证码登录入口：false 时登录页隐藏「验证码/密码」切换与发码 UI，仅保留密码登录。 */
    public val verificationLoginEnabled: Boolean = BuildConfig.VERIFICATION_LOGIN_ENABLED

    /** 注册入口总开关：当前移动端无注册界面，预留与后端 / 其他端语义对齐。 */
    public val registrationEnabled: Boolean = BuildConfig.REGISTRATION_ENABLED
}
