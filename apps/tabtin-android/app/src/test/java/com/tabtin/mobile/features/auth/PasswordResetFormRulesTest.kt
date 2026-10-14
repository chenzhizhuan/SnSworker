package com.tabtin.mobile.features.auth

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PasswordResetFormRulesTest {
    @Test
    fun `editing identifier strips all whitespace`() {
        assertEquals("user@example.com", PasswordResetFormRules.editingIdentifier(" user@example.com "))
        assertEquals("user@example.com", PasswordResetFormRules.editingIdentifier("u ser@ex ample.com"))
    }

    @Test
    fun `editing code keeps six digits at most`() {
        assertEquals("123456", PasswordResetFormRules.editingCode("12 34a56789"))
    }

    @Test
    fun `email validation accepts normal shapes and rejects malformed ones`() {
        assertTrue(PasswordResetFormRules.isEmail("dingfupeng@cicdi.cn"))
        assertTrue(PasswordResetFormRules.isEmail("DingFupeng@CICDI.CN"))
        assertFalse(PasswordResetFormRules.isEmail("SJ3365"))
        assertFalse(PasswordResetFormRules.isEmail("user@"))
        assertFalse(PasswordResetFormRules.isEmail("user@example"))
        assertFalse(PasswordResetFormRules.isEmail(""))
    }

    @Test
    fun `verification code must be six digits`() {
        assertTrue(PasswordResetFormRules.isVerificationCode("123456"))
        assertFalse(PasswordResetFormRules.isVerificationCode("12345"))
        assertFalse(PasswordResetFormRules.isVerificationCode("1234567"))
        assertFalse(PasswordResetFormRules.isVerificationCode("12 456"))
    }

    @Test
    fun `password requires at least eight characters`() {
        assertFalse(PasswordResetFormRules.isStrongPassword("Ab1!xyz"))
        assertTrue(PasswordResetFormRules.isStrongPassword("Ab1!xyzw"))
    }

    @Test
    fun `password requires at least three character kinds`() {
        // 仅两类：小写 + 数字
        assertFalse(PasswordResetFormRules.isStrongPassword("abcd1234"))
        // 三类：小写 + 数字 + 特殊
        assertTrue(PasswordResetFormRules.isStrongPassword("abcd1234!"))
        // 三类：大写 + 小写 + 数字
        assertTrue(PasswordResetFormRules.isStrongPassword("Abcd1234"))
    }

    @Test
    fun `password rejects whitespace and cjk characters`() {
        // 空白被拒（后端 validators 禁空白规则）
        assertFalse(PasswordResetFormRules.isStrongPassword("Abcd 1234!"))
        assertFalse(PasswordResetFormRules.isStrongPassword("Abcd\t1234!"))
        // CJK 被拒（防把报错文案粘贴进密码框）
        assertFalse(PasswordResetFormRules.isStrongPassword("Abcd1234中文!"))
        assertTrue(PasswordResetFormRules.isStrongPassword("Abcd1234!"))
    }

    @Test
    fun `password rejects overly long input`() {
        val longPassword = "Ab1!" + "x".repeat(125)
        assertFalse(PasswordResetFormRules.isStrongPassword(longPassword))
    }
}
