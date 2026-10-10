export interface UserInfo {
  id: string
  username?: string
  email?: string
  phone?: string
  nickname?: string
  avatar?: string
  bio?: string
  is_verified_email: boolean
  is_verified_phone: boolean
  date_joined: string
  last_login?: string
  login_count: number
  invite_code_required?: boolean
  invite_code_redeemed?: boolean
  /**
   * 全局管理员身份（后端 _build_user_info 始终下发）。
   * - is_superuser：超级管理员（role='admin'）
   * - is_staff：后台管理员（role='operator'）
   * 用于与「组织角色」无关的全局功能门禁（如场景市场 / 经营看板）。
   */
  is_superuser?: boolean
  is_staff?: boolean
  role?: 'admin' | 'operator' | 'user'
}

export interface LoginRequest {
  username: string
  password: string
  remember_me?: boolean
}

export interface VerificationCodeLoginRequest {
  username: string
  verification_code: string
  invite_code?: string
  remember_me?: boolean
  challenge_key?: string
}

export interface RegisterRequest {
  email?: string
  phone?: string
  password: string
  nickname?: string
  username?: string
  verification_code: string
  invite_code?: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: UserInfo
  is_new_user?: boolean
}

export interface RefreshTokenResponse {
  access_token: string
  refresh_token: string
  token_type?: string
  expires_in?: number
  user?: UserInfo
}

export interface SendVerificationCodeRequest {
  username: string
  code_type: VerificationCodeType
  invite_code?: string
  challenge_key?: string
}

export interface ForgotPasswordRequest {
  username: string
}

export interface ResetPasswordRequest {
  username: string
  verification_code: string
  new_password: string
}

/** @deprecated register now returns LoginResponse (auto-login after registration) */
export interface RegisterResponse {
  user_id: string
  message?: string
}

export interface PasswordStrength {
  score: number
  level: string
  suggestions: string[]
}

export interface ApiResponse<T = unknown> {
  success: boolean
  message: string
  data?: T
  code?: string | number
}

export type VerificationCodeType = 'login' | 'register' | 'reset_password' | 'phone_reservation'
export type LoginMethod = 'password' | 'verification_code'
