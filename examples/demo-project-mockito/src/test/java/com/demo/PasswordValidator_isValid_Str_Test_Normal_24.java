package com.demo;

import com.demo.PasswordValidator;
import org.junit.Assert;
import org.junit.Test;

public class PasswordValidator_isValid_Str_Test_Normal_24 {


    @Test
    public void testIsValidWithRepresentativeInputs() {
        PasswordValidator validator = new PasswordValidator();

        // "test" is shorter than 8 characters -> should be invalid
        boolean resultShort = validator.isValid("test");
        Assert.assertFalse(resultShort);

        // empty string is shorter than 8 characters -> should be invalid
        boolean resultEmpty = validator.isValid("");
        Assert.assertFalse(resultEmpty);

        // a typical valid password: length 9 with an uppercase letter and a digit
        boolean resultValid = validator.isValid("Password1");
        Assert.assertTrue(resultValid);
    }

}
