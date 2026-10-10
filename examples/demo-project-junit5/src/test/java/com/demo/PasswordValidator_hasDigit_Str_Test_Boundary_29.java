package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class PasswordValidator_hasDigit_Str_Test_Boundary_29 {


    @Test
    public void testHasDigitWithNullBoundary() throws Exception {
        PasswordValidator validator = new PasswordValidator();

        Method hasDigit = PasswordValidator.class.getDeclaredMethod("hasDigit", String.class);
        hasDigit.setAccessible(true);

        // Boundary: null input for the String parameter.
        // The method dereferences the argument (e.g. via length()/charAt()),
        // so the underlying invocation is expected to fail with a NullPointerException,
        // which reflection wraps in an InvocationTargetException.
        InvocationTargetException thrown = assertThrows(
                InvocationTargetException.class,
                () -> hasDigit.invoke(validator, (String) null)
        );

        assertInstanceOf(NullPointerException.class, thrown.getCause());
    }

}
