package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.Method;
import org.junit.Assert;
import org.junit.Test;

public class PasswordValidator_hasUpper_Str_Test_Normal_26 {


    @Test
    public void testHasUpperWithTypicalInput() throws Exception {
        PasswordValidator validator = new PasswordValidator();
        Method method = PasswordValidator.class.getDeclaredMethod("hasUpper", String.class);
        method.setAccessible(true);

        Object result = method.invoke(validator, "test");

        Assert.assertNotNull(result);
        Assert.assertTrue(result instanceof Boolean);
        Assert.assertFalse(((Boolean) result).booleanValue());
    }

}
