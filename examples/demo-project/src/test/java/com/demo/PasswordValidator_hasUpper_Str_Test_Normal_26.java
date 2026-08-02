package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import org.junit.Assert;
import org.junit.Test;

public class PasswordValidator_hasUpper_Str_Test_Normal_26 {


    @Test
    public void hasUpper_WithTypicalInputs_ReturnsExpectedResult() {
        try {
            PasswordValidator validator = new PasswordValidator();
            Method method = PasswordValidator.class.getDeclaredMethod("hasUpper", String.class);
            method.setAccessible(true);

            Boolean resultForLowerCase = (Boolean) method.invoke(validator, "test");
            Assert.assertFalse("Expected false for 'test'", resultForLowerCase.booleanValue());

            Boolean resultForEmpty = (Boolean) method.invoke(validator, "");
            Assert.assertFalse("Expected false for ''", resultForEmpty.booleanValue());
        } catch (IllegalAccessException e) {
            Assert.fail("Unexpected IllegalAccessException: " + e.getMessage());
        } catch (InvocationTargetException e) {
            Assert.fail("Unexpected InvocationTargetException: " + e.getMessage());
        } catch (NoSuchMethodException e) {
            Assert.fail("Unexpected NoSuchMethodException: " + e.getMessage());
        }
    }

}