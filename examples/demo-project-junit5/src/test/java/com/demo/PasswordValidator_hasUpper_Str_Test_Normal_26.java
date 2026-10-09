package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class PasswordValidator_hasUpper_Str_Test_Normal_26 {


    @Test
    public void testHasUpperWithTypicalInputs() throws NoSuchMethodException, IllegalAccessException, InvocationTargetException {
        PasswordValidator validator = new PasswordValidator();
        Method method = PasswordValidator.class.getDeclaredMethod("hasUpper", String.class);
        method.setAccessible(true);

        // Typical lowercase input: no uppercase character present.
        Object result1 = method.invoke(validator, "test");
        Assertions.assertFalse((Boolean) result1, "Expected no uppercase letter in \"test\"");

        // Empty string: loop body never executes, so no uppercase letter.
        Object result2 = method.invoke(validator, "");
        Assertions.assertFalse((Boolean) result2, "Expected no uppercase letter in empty string");
    }

}
