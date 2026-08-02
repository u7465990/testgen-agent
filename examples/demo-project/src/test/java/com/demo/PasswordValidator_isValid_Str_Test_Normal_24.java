package com.demo;

import com.demo.PasswordValidator;
import org.junit.Test;
import static org.junit.Assert.*;

public class PasswordValidator_isValid_Str_Test_Normal_24 {


    @Test
    public void isValid_withTypicalInputs_returnsExpectedResult() {
        PasswordValidator validator = new PasswordValidator();

        assertFalse(validator.isValid(""));
        assertFalse(validator.isValid("test"));
        assertTrue(validator.isValid("Password1"));
    }

}
