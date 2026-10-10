package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import org.junit.Assert;
import org.junit.Test;

public class PasswordValidator_hasUpper_Str_Test_Boundary_27 {


    @Test
    public void testHasUpperWithNullString() throws Exception {
        PasswordValidator validator = new PasswordValidator();
        Method method = PasswordValidator.class.getDeclaredMethod("hasUpper", String.class);
        method.setAccessible(true);

        String s = null;
        try {
            method.invoke(validator, s);
            Assert.fail("Expected NullPointerException was not thrown");
        } catch (InvocationTargetException e) {
            Assert.assertTrue(e.getCause() instanceof NullPointerException);
        }
    }

}
