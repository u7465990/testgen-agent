package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.Method;
import java.lang.reflect.InvocationTargetException;
import org.junit.Test;
import org.junit.Assert;

public class PasswordValidator_hasDigit_Str_Test_Boundary_29 {


    @Test
    public void testHasDigit_withNullParameter() throws Exception {
        PasswordValidator validator = new PasswordValidator();

        Method method = PasswordValidator.class.getDeclaredMethod("hasDigit", String.class);
        method.setAccessible(true);

        try {
            method.invoke(validator, new Object[]{null});
            Assert.fail("Expected an exception when the input String is null");
        } catch (InvocationTargetException e) {
            Throwable cause = e.getCause();
            Assert.assertNotNull("Expected a cause exception for null input", cause);
            Assert.assertTrue(
                    "Expected NullPointerException for null input but got: " + cause.getClass().getName(),
                    cause instanceof NullPointerException);
        }
    }

}
