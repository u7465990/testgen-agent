package com.demo;

/** Validator with private helper methods that require reflection-based testing. */
public class PasswordValidator {

    public boolean isValid(String password) {
        if (password == null) {
            return false;
        }
        if (password.length() < 8) {
            return false;
        }
        if (password.length() > 64) {
            return false;
        }
        return hasUpper(password) && hasDigit(password);
    }

    private boolean hasUpper(String s) {
        for (int i = 0; i < s.length(); i++) {
            if (Character.isUpperCase(s.charAt(i))) {
                return true;
            }
        }
        return false;
    }

    private boolean hasDigit(String s) {
        for (int i = 0; i < s.length(); i++) {
            if (Character.isDigit(s.charAt(i))) {
                return true;
            }
        }
        return false;
    }

    public String strength(String password) {
        if (!isValid(password)) {
            return "weak";
        }
        return "strong";
    }
}
