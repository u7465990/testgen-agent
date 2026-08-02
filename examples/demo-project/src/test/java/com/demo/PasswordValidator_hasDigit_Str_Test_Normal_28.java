package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.Method;
import org.junit.Assert;
import org.junit.Test;

public class PasswordValidator_hasDigit_Str_Test_Normal_28 {


    @Test
    public void hasDigitReturnsFalseForTestAndEmpty() throws Exception {
        PasswordValidator validator = new PasswordValidator();
        Method method = PasswordValidator.class.getDeclaredMethod("hasDigit", String.class);
        method.setAccessible(true);

        Assert.assertFalse((Boolean) method.invoke(validator, "test"));
        Assert.assertFalse((Boolean) method.invoke(validator, ""));
    }

}
