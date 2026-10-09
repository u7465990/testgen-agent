package com.demo;

import com.demo.PasswordValidator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class PasswordValidator_strength_Str_Test_Boundary_31 {


    @Test
    public void testStrengthWithNullPassword() {
        PasswordValidator validator = new PasswordValidator();

        String result = validator.strength(null);

        Assertions.assertEquals("weak", result);
    }

}
