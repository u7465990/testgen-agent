package com.demo;

import com.demo.PasswordValidator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class PasswordValidator_isValid_Str_Test_Normal_24 {


    @Test
    public void testIsValidWithRepresentativeInputs() {
        PasswordValidator validator = new PasswordValidator();

        // Empty string: length (0) is less than 8, so not valid
        boolean resultEmpty = validator.isValid("");
        assertFalse(resultEmpty, "Empty password should be invalid");

        // "test": length (4) is less than 8, so not valid
        boolean resultShort = validator.isValid("test");
        assertFalse(resultShort, "\"test\" is too short and should be invalid");

        // A representative valid password: length 9, contains uppercase and digit
        boolean resultValid = validator.isValid("Password1");
        assertTrue(resultValid, "\"Password1\" should be a valid password");
    }

}
