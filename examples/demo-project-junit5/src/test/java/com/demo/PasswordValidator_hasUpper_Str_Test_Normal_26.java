package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class PasswordValidator_hasUpper_Str_Test_Normal_26 {


    @Test
    public void testHasUpperWithRepresentativeInputs() throws NoSuchMethodException, IllegalAccessException, InvocationTargetException {
        PasswordValidator validator = new PasswordValidator();

        Method hasUpper = PasswordValidator.class.getDeclaredMethod("hasUpper", String.class);
        hasUpper.setAccessible(true);

        Boolean resultLowercase = (Boolean) hasUpper.invoke(validator, "test");
        Boolean resultEmpty = (Boolean) hasUpper.invoke(validator, "");

        Assertions.assertAll(
                () -> Assertions.assertFalse(resultLowercase, "A lowercase-only string should not contain an uppercase character"),
                () -> Assertions.assertFalse(resultEmpty, "An empty string should not contain an uppercase character")
        );
    }

}
