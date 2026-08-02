package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import org.junit.Test;
import static org.junit.Assert.*;

public class PasswordValidator_hasUpper_Str_Test_Boundary_27 {


    @Test
    public void testHasUpperNullInputThrowsNullPointerException() throws Exception {
        PasswordValidator validator = new PasswordValidator();
        Method method = PasswordValidator.class.getDeclaredMethod("hasUpper", String.class);
        method.setAccessible(true);

        try {
            method.invoke(validator, new Object[] { null });
            fail("Expected NullPointerException for null input");
        } catch (InvocationTargetException e) {
            assertTrue("Expected cause to be NullPointerException", e.getCause() instanceof NullPointerException);
        }
    }

}
