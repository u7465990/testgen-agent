package com.demo;

import com.demo.PasswordValidator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class PasswordValidator_strength_Str_Test_Normal_30 {


    @Test
    public void testStrengthWithRepresentativeValidInput() {
        PasswordValidator validator = new PasswordValidator();

        String result = validator.strength("test");

        Assertions.assertNotNull(result);
        Assertions.assertEquals("strong", result);
    }

    @Test
    public void testStrengthWithEmptyInput() {
        PasswordValidator validator = new PasswordValidator();

        String result = validator.strength("");

        Assertions.assertNotNull(result);
        Assertions.assertEquals("weak", result);
    }

}
