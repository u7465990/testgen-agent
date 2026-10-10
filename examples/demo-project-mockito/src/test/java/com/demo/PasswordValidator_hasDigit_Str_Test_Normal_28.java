package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import org.junit.Assert;
import org.junit.Test;

public class PasswordValidator_hasDigit_Str_Test_Normal_28 {


    @Test
    public void testHasDigitWithRepresentativeInputs() {
        PasswordValidator validator = new PasswordValidator();
        try {
            Method method = PasswordValidator.class.getDeclaredMethod("hasDigit", String.class);
            method.setAccessible(true);

            Boolean resultNoDigit = (Boolean) method.invoke(validator, "test");
            Assert.assertFalse("Expected 'test' to contain no digit", resultNoDigit.booleanValue());

            Boolean resultEmpty = (Boolean) method.invoke(validator, "");
            Assert.assertFalse("Expected empty string to contain no digit", resultEmpty.booleanValue());

            Boolean resultWithDigit = (Boolean) method.invoke(validator, "abc1");
            Assert.assertTrue("Expected 'abc1' to contain a digit", resultWithDigit.booleanValue());
        } catch (NoSuchMethodException e) {
            Assert.fail("Method hasDigit not found: " + e.getMessage());
        } catch (IllegalAccessException e) {
            Assert.fail("Illegal access invoking hasDigit: " + e.getMessage());
        } catch (InvocationTargetException e) {
            Assert.fail("Exception thrown by hasDigit: " + e.getCause());
        }
    }

}
