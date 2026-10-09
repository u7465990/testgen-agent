package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class PasswordValidator_hasUpper_Str_Test_Boundary_27 {


    @Test
    public void testHasUpperWithNullString() throws Exception {
        PasswordValidator validator = new PasswordValidator();

        Method method = PasswordValidator.class.getDeclaredMethod("hasUpper", String.class);
        method.setAccessible(true);

        try {
            method.invoke(validator, new Object[] { null });
            Assertions.fail("Expected NullPointerException when the input string is null");
        } catch (InvocationTargetException e) {
            Throwable cause = e.getCause();
            Assertions.assertNotNull(cause);
            Assertions.assertTrue(cause instanceof NullPointerException,
                    "Expected cause to be NullPointerException but was " + cause.getClass().getName());
        }
    }

}
