package com.demo;

import com.demo.PasswordValidator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class PasswordValidator_isValid_Str_Test_Normal_24 {


    @Test
    public void testIsValidWithTypicalInputs() {
        PasswordValidator validator = new PasswordValidator();

        boolean resultForTest = validator.isValid("test");
        Assertions.assertFalse(resultForTest, "Password \"test\" is too short and has no uppercase/digit, so it should be invalid");

        boolean resultForEmpty = validator.isValid("");
        Assertions.assertFalse(resultForEmpty, "Empty password is shorter than 8 characters, so it should be invalid");
    }

}
