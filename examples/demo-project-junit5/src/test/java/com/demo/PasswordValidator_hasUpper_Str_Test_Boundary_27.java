package com.demo;

import com.demo.PasswordValidator;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class PasswordValidator_hasUpper_Str_Test_Boundary_27 {


    @Test
    public void testHasUpperWithNullString() throws Exception {
        PasswordValidator validator = new PasswordValidator();
        Method method = PasswordValidator.class.getDeclaredMethod("hasUpper", String.class);
        method.setAccessible(true);

        InvocationTargetException thrown = assertThrows(InvocationTargetException.class, () -> {
            method.invoke(validator, (Object) null);
        });

        assertNotNull(thrown.getCause(), "InvocationTargetException should wrap a cause");
        assertTrue(thrown.getCause() instanceof NullPointerException,
                "Expected cause to be NullPointerException but was: " + thrown.getCause());
    }

}
