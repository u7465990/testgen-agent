package com.demo;

import com.demo.PasswordValidator;
import org.junit.Assert;
import org.junit.Test;

public class PasswordValidator_isValid_Str_Test_Boundary_25 {


    @Test
    public void testIsValidWithNullPassword() {
        PasswordValidator validator = new PasswordValidator();
        boolean result = validator.isValid(null);
        Assert.assertFalse("isValid should return false when password is null", result);
    }

}
