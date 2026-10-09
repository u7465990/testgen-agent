package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class PasswordValidator_hasDigit_Str_Test_Boundary_29 {


    @Test
    public void testHasDigitWithNullParameter() {
        PasswordValidator validator = new PasswordValidator();
        try {
            Method method = PasswordValidator.class.getDeclaredMethod("hasDigit", String.class);
            method.setAccessible(true);
            method.invoke(validator, new Object[] { null });
            Assertions.fail("Expected NullPointerException when passing null to hasDigit");
        } catch (InvocationTargetException e) {
            Assertions.assertTrue(e.getCause() instanceof NullPointerException,
                    "Expected cause to be NullPointerException but was: " + e.getCause());
        } catch (IllegalAccessException e) {
            Assertions.fail("Unexpected IllegalAccessException: " + e.getMessage());
        } catch (NoSuchMethodException e) {
            Assertions.fail("Unexpected NoSuchMethodException: " + e.getMessage());
        }
    }

}
