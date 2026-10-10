package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class PasswordValidator_hasDigit_Str_Test_Normal_28 {


    @Test
    public void testHasDigitWithTypicalInputs() {
        PasswordValidator validator = new PasswordValidator();
        try {
            Method hasDigitMethod = PasswordValidator.class.getDeclaredMethod("hasDigit", String.class);
            hasDigitMethod.setAccessible(true);

            boolean resultForTest = (boolean) hasDigitMethod.invoke(validator, "test");
            assertFalse(resultForTest, "hasDigit(\"test\") should be false");

            boolean resultForEmpty = (boolean) hasDigitMethod.invoke(validator, "");
            assertFalse(resultForEmpty, "hasDigit(\"\") should be false");
        } catch (NoSuchMethodException | IllegalAccessException | InvocationTargetException e) {
            fail("Reflection failed: " + e.getMessage());
        }
    }

}
