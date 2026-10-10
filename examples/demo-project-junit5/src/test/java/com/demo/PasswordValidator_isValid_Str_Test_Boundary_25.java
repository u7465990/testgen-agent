package com.demo;

import com.demo.PasswordValidator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertFalse;

public class PasswordValidator_isValid_Str_Test_Boundary_25 {


    @Test
    public void testIsValidWithNullPassword() {
        PasswordValidator validator = new PasswordValidator();
        boolean result = validator.isValid(null);
        assertFalse(result, "isValid should return false when password is null");
    }

}
