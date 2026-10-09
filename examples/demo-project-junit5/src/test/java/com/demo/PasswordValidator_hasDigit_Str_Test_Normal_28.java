package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class PasswordValidator_hasDigit_Str_Test_Normal_28 {


    @Test
    public void testHasDigit() throws Exception {
        PasswordValidator validator = new PasswordValidator();

        Method method = PasswordValidator.class.getDeclaredMethod("hasDigit", String.class);
        method.setAccessible(true);

        // Typical valid input: "test" (a plain alphabetic string)
        boolean resultTest = (Boolean) method.invoke(validator, "test");
        Assertions.assertFalse(resultTest, "Expected hasDigit(\"test\") to be false");

        // Empty string boundary
        boolean resultEmpty = (Boolean) method.invoke(validator, "");
        Assertions.assertFalse(resultEmpty, "Expected hasDigit(\"\") to be false");
    }

}
