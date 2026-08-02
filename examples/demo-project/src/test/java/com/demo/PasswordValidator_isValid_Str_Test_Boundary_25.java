package com.demo;

import com.demo.PasswordValidator;
import static org.junit.Assert.assertFalse;
import org.junit.Test;

public class PasswordValidator_isValid_Str_Test_Boundary_25 {


    @Test
    public void testIsValidWithNullPasswordReturnsFalse() {
        PasswordValidator validator = new PasswordValidator();
        assertFalse(validator.isValid(null));
    }

}
