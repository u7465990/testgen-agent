package com.demo;

import com.demo.PasswordValidator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class PasswordValidator_strength_Str_Test_Normal_30 {


    @Test
    public void testStrengthWithTypicalInputs() {
        PasswordValidator validator = new PasswordValidator();

        // Typical non-empty input: result must be a defined strength value.
        String resultForTypical = validator.strength("test");
        assertNotNull(resultForTypical, "strength(...) must not return null for a typical input");
        assertTrue("weak".equals(resultForTypical) || "strong".equals(resultForTypical),
                "strength(...) must return either 'weak' or 'strong'");

        // Empty input is an invalid password, so the expected value is "weak".
        String resultForEmpty = validator.strength("");
        assertEquals("weak", resultForEmpty, "An empty password should be classified as 'weak'");
    }

}
