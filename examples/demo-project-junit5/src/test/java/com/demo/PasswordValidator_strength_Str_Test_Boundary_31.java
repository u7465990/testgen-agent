package com.demo;

import com.demo.PasswordValidator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class PasswordValidator_strength_Str_Test_Boundary_31 {


    @Test
    public void testStrengthWithNullPasswordReturnsWeak() {
        PasswordValidator validator = new PasswordValidator();

        String actual = validator.strength(null);

        assertEquals("weak", actual, "A null password must be reported as weak");
    }

}
